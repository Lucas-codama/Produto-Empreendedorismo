"""Local, explicit checks. Findings are evidence, never a compliance certificate."""
from __future__ import annotations

import base64
import colorsys
from io import BytesIO
import re
import zipfile
import xml.etree.ElementTree as ET

from PIL import Image
from docx import Document
from docx.text.paragraph import Paragraph
from pptx import Presentation
from pptx.enum.dml import MSO_FILL_TYPE
from pptx.util import Pt
import pdfplumber
from pypdf import PdfReader
import document_parts
from vision_checks import PdfPixels, PDF_LOCK, ocr_blocks, ocr
from pdf_structure import inspect as inspect_pdf_structure

SUPPORTED = {'.pdf', '.docx', '.pptx', '.png', '.jpg', '.jpeg'}
MAX_BYTES = 20 * 1024 * 1024
ENGINE_VERSION = 9
NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}


class MaterialError(ValueError):
    pass


def luminance(color):
    values = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
    return .2126 * linear[0] + .7152 * linear[1] + .0722 * linear[2]


def contrast(first, second):
    a, b = sorted([luminance(first), luminance(second)])
    return (b + .05) / (a + .05)


def threshold(size, bold):
    return 3 if size is not None and (size >= 18 or (bold and size >= 14)) else 4.5


def validate_context(context):
    for key, label in [('discipline', 'disciplina'), ('activity', 'tipo de atividade'),
                       ('needs', 'necessidades do estudante'), ('technology', 'tecnologias assistivas')]:
        if not isinstance(context.get(key), str) or not context[key].strip():
            raise MaterialError('Informe ' + label + ' antes de analisar o material.')
        if len(context[key]) > 3000:
            raise MaterialError('Uma das informações de contexto está muito longa (limite: 3.000 caracteres).')
    minimum = context.get('min_font')
    if minimum not in (None, ''):
        try:
            minimum = float(minimum)
        except (ValueError, TypeError):
            raise MaterialError('O tamanho preferido deve ser um número em pontos.')
        if not 6 <= minimum <= 96:
            raise MaterialError('Informe um tamanho de fonte entre 6 e 96 pontos.')
    context['min_font'] = minimum if minimum not in (None, '') else None
    return context


def validate_file(path):
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED:
        raise MaterialError('Use PDF, DOCX, PPTX, PNG ou JPG. Arquivos DOC e PPT antigos precisam ser convertidos.')
    if path.stat().st_size > MAX_BYTES or not path.stat().st_size:
        raise MaterialError('Envie um arquivo não vazio com até 20 MB.')
    if suffix in {'.docx', '.pptx'}:
        try:
            with zipfile.ZipFile(path) as archive:
                info = archive.infolist()
                if len(info) > 10000 or sum(i.file_size for i in info) > 100 * 1024 * 1024:
                    raise MaterialError('O conteúdo expandido do documento excede o limite desta versão.')
                if any(i.flag_bits & 1 for i in info):
                    raise MaterialError('Documentos compactados com senha não são apoiados nesta versão.')
        except zipfile.BadZipFile:
            raise MaterialError('Esse arquivo não é um documento Office válido.')


def data_image(blob):
    image = Image.open(BytesIO(blob))
    image.thumbnail((1400, 1400))
    if image.mode not in ('RGB', 'RGBA'):
        image = image.convert('RGB')
    stream = BytesIO()
    image.save(stream, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(stream.getvalue()).decode('ascii')


def theme_colors(path):
    result = {}
    try:
        with zipfile.ZipFile(path) as archive:
            candidates = [n for n in archive.namelist() if n.endswith('theme/theme1.xml')]
            if not candidates:
                return result
            root = ET.fromstring(archive.read(candidates[0]))
            scheme = root.find('.//a:clrScheme', NS)
            for entry in scheme if scheme is not None else []:
                for child in entry:
                    rgb = child.get('val') if child.tag.endswith('srgbClr') else child.get('lastClr')
                    if rgb and re.fullmatch('[0-9a-fA-F]{6}', rgb):
                        result[entry.tag.split('}')[-1]] = '#' + rgb.upper()
            result.update({'tx1': result.get('dk1'), 'bg1': result.get('lt1'),
                           'tx2': result.get('dk2'), 'bg2': result.get('lt2')})
    except (ET.ParseError, KeyError):
        pass
    return result


def xml_color(node, palette):
    if node is None:
        return None
    for child in node.iter():
        name = child.tag.split('}')[-1]
        if name not in {'srgbClr', 'schemeClr', 'sysClr'}:
            continue
        rgb = child.get('val', '') if name == 'srgbClr' else child.get('lastClr', '') if name == 'sysClr' else (palette.get(child.get('val')) or '').lstrip('#')
        if not re.fullmatch('[0-9a-fA-F]{6}', rgb):
            return None
        channels = [int(rgb[i:i+2], 16)/255 for i in (0,2,4)]
        for transform in child:
            kind=transform.tag.split('}')[-1]
            try: amount=int(transform.get('val','0'))/100000
            except ValueError: return None
            if kind=='alpha' and amount==1: continue
            if kind=='tint': channels=[v+(1-v)*amount for v in channels]
            elif kind=='shade': channels=[v*amount for v in channels]
            elif kind in {'lumMod','lumOff'}:
                h,l,s=colorsys.rgb_to_hls(*channels)
                l=l*amount if kind=='lumMod' else l+amount
                channels=list(colorsys.hls_to_rgb(h,max(0,min(1,l)),s))
            else: return None
        return '#' + ''.join(f'{round(max(0,min(1,v))*255):02X}' for v in channels)
    return None


def ppt_font(run, paragraph, shape, palette):
    size = run.font.size or paragraph.font.size
    bold = run.font.bold if run.font.bold is not None else paragraph.font.bold
    color = xml_color(run._r, palette)
    explicit_color = any(n.tag.split('}')[-1] in {'solidFill','gradFill','noFill'} for n in run._r.iter())
    if color is None and not explicit_color and paragraph._p.pPr is not None:
        color = xml_color(paragraph._p.pPr, palette)
    if shape.is_placeholder:
        for owner in [shape.part.slide.slide_layout, shape.part.slide.slide_layout.slide_master]:
            for inherited in owner.placeholders:
                if inherited.placeholder_format.idx == shape.placeholder_format.idx and inherited.has_text_frame:
                    p = inherited.text_frame.paragraphs[0]
                    if size is None:
                        size = p.font.size
                    if bold is None:
                        bold = p.font.bold
                    if color is None and not explicit_color:
                        color = xml_color(p._p.pPr, palette)
    nodes = shape._element.xpath(f'./p:txBody/a:lstStyle/a:lvl{paragraph.level+1}pPr/a:defRPr')
    owner=shape.part.slide.slide_layout.slide_master
    category='titleStyle' if shape.is_placeholder and shape.placeholder_format.type in {1,3} else 'bodyStyle' if shape.is_placeholder else 'otherStyle'
    nodes += owner._element.xpath(f'./p:txStyles/p:{category}/a:lvl{paragraph.level+1}pPr/a:defRPr')
    for node in nodes:
        if size is None and node.get('sz'): size=Pt(int(node.get('sz'))/100)
        if bold is None and node.get('b') is not None: bold=node.get('b') in {'1','true'}
        if color is None and not explicit_color: color=xml_color(node,palette)
    return float(size.pt) if size else None, bool(bold), color


def fill_color(fill, palette):
    try:
        if fill.type != MSO_FILL_TYPE.SOLID:
            return None
        return xml_color(fill._xPr, palette)
    except (AttributeError, TypeError, ValueError):
        return None


def picture_info(node):
    props = [el for el in node.iter() if el.tag.split('}')[-1] in {'docPr', 'cNvPr'}]
    alt = (props[0].get('descr') or props[0].get('title') or '') if props else ''
    decorative = any(el.tag.split('}')[-1] == 'decorative' and el.get('val') in {'1', 'true'} for el in node.iter())
    return alt.strip(), decorative



def ppt_shapes(shapes, transform=(1,1,0,0), path=()):
    sx,sy,ox,oy=transform
    for index,shape in enumerate(shapes):
        shape_path=path+(index,)
        bounds={'x':(ox+shape.left*sx)/12700,'y':(oy+shape.top*sy)/12700,
                'w':shape.width*sx/12700,'h':shape.height*sy/12700}
        if shape.shape_type==6:
            offs=shape._element.xpath('./p:grpSpPr/a:xfrm/a:chOff')
            exts=shape._element.xpath('./p:grpSpPr/a:xfrm/a:chExt')
            cx=int(offs[0].get('x',0)) if offs else 0;cy=int(offs[0].get('y',0)) if offs else 0
            cw=int(exts[0].get('cx',shape.width)) if exts else shape.width
            ch=int(exts[0].get('cy',shape.height)) if exts else shape.height
            nx=sx*shape.width/(cw or 1);ny=sy*shape.height/(ch or 1)
            yield from ppt_shapes(shape.shapes,(nx,ny,ox+shape.left*sx-cx*nx,oy+shape.top*sy-cy*ny),shape_path)
        else:
            yield shape,shape_path,bounds

def parse_pptx(path):
    prs=Presentation(path)
    if not 1<=len(prs.slides)<=60:raise MaterialError('Esta versão aceita apresentações com até 60 slides.')
    theme=theme_colors(path);pages=[]
    for pi,slide in enumerate(prs.slides):
        palette=dict(theme)
        maps=slide._element.xpath('./p:clrMapOvr/a:overrideClrMapping') or slide.slide_layout.slide_master._element.xpath('./p:clrMap')
        if maps:
            for key,value in maps[0].attrib.items():palette[key]=theme.get(value)
        default_bg=None;complex_bg=False
        for owner in [slide,slide.slide_layout,slide.slide_layout.slide_master]:
            bg_nodes=owner._element.xpath('./p:cSld/p:bg')
            if not bg_nodes:continue
            default_bg=fill_color(owner.background.fill,palette)
            complex_bg=default_bg is None
            break
        page={'label':f'Slide {pi+1}','width':prs.slide_width/12700,'height':prs.slide_height/12700,
              'background':default_bg or palette.get('bg1') or '#FFFFFF','kind':'slide','blocks':[],
              'title':bool(slide.shapes.title and slide.shapes.title.text.strip())}
        entries=list(ppt_shapes(slide.shapes))
        def ref(shape_path,**extra):return {'slide':pi,'shape':shape_path[0],'shape_path':list(shape_path),**extra}
        for shape_index,(shape,shape_path,bounds) in enumerate(entries):
            identity=f's{pi}-e'+('-'.join(map(str,shape_path)))
            own_bg=fill_color(shape.fill,palette) if hasattr(shape,'fill') else None
            own_complex=hasattr(shape,'fill') and shape.fill.type not in (None,MSO_FILL_TYPE.BACKGROUND) and own_bg is None
            bg=own_bg or (None if complex_bg or own_complex else page['background'])
            for oi,(other,_,ob) in enumerate(entries):
                if oi==shape_index:continue
                overlaps=bounds['x']<ob['x']+ob['w'] and bounds['x']+bounds['w']>ob['x'] and bounds['y']<ob['y']+ob['h'] and bounds['y']+bounds['h']>ob['y']
                painted=other.shape_type==13 or (hasattr(other,'fill') and other.fill.type not in (None,MSO_FILL_TYPE.BACKGROUND))
                if not overlaps or not painted:continue
                if oi>shape_index:bg=None;continue
                if own_bg or own_complex:continue
                covers=ob['x']<=bounds['x'] and ob['y']<=bounds['y'] and ob['x']+ob['w']>=bounds['x']+bounds['w'] and ob['y']+ob['h']>=bounds['y']+bounds['h']
                geometries=other._element.xpath('./p:spPr/a:prstGeom')
                rectangular=bool(geometries and geometries[0].get('prst')=='rect')
                solid=fill_color(other.fill,palette) if hasattr(other,'fill') else None
                bg=solid if covers and rectangular and solid else None
            def text_block(text_frame,block_id,box,source,background,location=None):
                runs=[]
                for p_index,paragraph in enumerate(text_frame.paragraphs):
                    for r_index,run in enumerate(paragraph.runs):
                        size,bold,color=ppt_font(run,paragraph,shape,palette)
                        runs.append({'text':run.text,'size':size,'bold':bold,'color':color,'source':dict(source,paragraph=p_index,run=r_index)})
                    if p_index<len(text_frame.paragraphs)-1:runs.append({'text':'\n','size':None,'bold':False,'color':None})
                page['blocks'].append(dict(id=block_id,type='text',text=text_frame.text,runs=runs,background=background,source=source,location=location,**box))
            if shape.shape_type==13:
                alt,decorative=picture_info(shape._element)
                recognized,ocr_error=ocr(Image.open(BytesIO(shape.image.blob)))
                page['blocks'].append(dict(id=identity,type='image',image=data_image(shape.image.blob),alt=alt,decorative=decorative,
                                          ocr_text=' '.join(w['text'] for w in recognized),ocr_error=ocr_error,source=ref(shape_path),**bounds))
            elif shape.has_text_frame:
                text_block(shape.text_frame,identity,bounds,ref(shape_path),bg)
            elif getattr(shape,'has_table',False):
                table=shape.table;row_y=bounds['y']
                for ri,row in enumerate(table.rows):
                    col_x=bounds['x'];row_h=row.height/12700*(bounds['h']/(shape.height/12700))
                    for ci,cell in enumerate(row.cells):
                        col_w=table.columns[ci].width/12700*(bounds['w']/(shape.width/12700))
                        if not cell.is_spanned and cell.text.strip():
                            cb=fill_color(cell.fill,palette)
                            text_block(cell.text_frame,f'{identity}-r{ri}c{ci}',{'x':col_x,'y':row_y,'w':col_w,'h':row_h},
                                       ref(shape_path,row=ri,column=ci),cb,f'Slide {pi+1} · linha {ri+1}, coluna {ci+1}')
                        col_x+=col_w
                    row_y+=row_h
                page['blocks'].append(dict(id=identity,type='table',text='Tabela: conferir cabeçalhos e relações.',**bounds))
            else:
                geometries=shape._element.xpath('./p:spPr/a:prstGeom')
                kind='shape_background' if own_bg and geometries and geometries[0].get('prst')=='rect' else 'unsupported'
                page['blocks'].append(dict(id=identity,type=kind,background=own_bg,text='' if kind=='shape_background' else 'Elemento visual: revisar no PowerPoint',**bounds))
        pages.append(page)
    return pages,{'preview':'Prévia reconstruída. Fontes, temas e efeitos complexos podem diferir do PowerPoint.','format':'PPTX','editable':True}

def doc_font(run, paragraph, doc, palette=None, default_bg='#FFFFFF'):
    candidates = [run.font]
    character_style = run.style
    seen_characters = set()
    while character_style is not None and character_style.style_id not in seen_characters:
        candidates.append(character_style.font)
        seen_characters.add(character_style.style_id)
        character_style = character_style.base_style
    style = paragraph.style
    seen = set()
    while style is not None and style.style_id not in seen:
        candidates.append(style.font); seen.add(style.style_id); style = style.base_style
    candidates.append(doc.styles['Normal'].font)
    size = next((f.size.pt for f in candidates if f.size is not None), None)
    bold = next((f.bold for f in candidates if f.bold is not None), False)
    color = None
    color_nodes = [node for f in candidates for node in f._element.xpath('./w:rPr/w:color')]
    color_nodes += doc.styles.element.xpath('./w:docDefaults/w:rPrDefault/w:rPr/w:color')
    for node in color_nodes:
        if node is None: continue
        theme=node.get('{'+NS['w']+'}themeColor')
        value=node.get('{'+NS['w']+'}val','auto')
        if theme:
            key={'dark1':'dk1','light1':'lt1','dark2':'dk2','light2':'lt2'}.get(theme,theme)
            color=(palette or {}).get(key)
            if color:
                channels=[int(color[i:i+2],16) for i in (1,3,5)]
                for attr in ['themeShade','themeTint']:
                    amount=node.get('{'+NS['w']+'}'+attr)
                    if amount:
                        v=int(amount,16)/255
                        channels=[round(c*v) if attr=='themeShade' else round(c+(255-c)*v) for c in channels]
                color='#'+''.join(f'{c:02X}' for c in channels)
        elif re.fullmatch('[0-9a-fA-F]{6}',value): color='#'+value.upper()
        elif value=='auto' and default_bg=='#FFFFFF': color='#000000'
        break
    else:
        if default_bg=='#FFFFFF': color='#000000'
    if size is None:
        nodes = doc.styles.element.xpath('./w:docDefaults/w:rPrDefault/w:rPr/w:sz')
        if nodes:
            size = float(nodes[0].get('{'+NS['w']+'}val')) / 2
    return size, bool(bold), color


def doc_background(paragraph, default='#FFFFFF', palette=None):
    shades = paragraph._p.xpath('./w:pPr/w:shd')
    style=paragraph.style;seen=set()
    while not shades and style is not None and style.style_id not in seen:
        shades=style.element.xpath('./w:pPr/w:shd');seen.add(style.style_id);style=style.base_style
    if not shades:
        parent = paragraph._p.getparent()
        if parent.tag.endswith('}tc'):
            shades = parent.xpath('./w:tcPr/w:shd')
    if shades:
        pattern=shades[0].get('{'+NS['w']+'}val','clear')
        if pattern=='nil':return default
        if pattern not in {'clear','solid'}:return None
        attr='color' if pattern=='solid' else 'fill'
        theme=shades[0].get('{'+NS['w']+'}'+('themeColor' if pattern=='solid' else 'themeFill'))
        if theme:return (palette or {}).get({'dark1':'dk1','light1':'lt1','dark2':'dk2','light2':'lt2'}.get(theme,theme))
        fill = shades[0].get('{'+NS['w']+'}'+attr, '')
        if re.fullmatch('[0-9a-fA-F]{6}', fill):
            return '#' + fill
        return None
    return default


HIGHLIGHTS={'yellow':'FFFF00','green':'00FF00','cyan':'00FFFF','magenta':'FF00FF','blue':'0000FF','red':'FF0000','darkBlue':'000080','darkCyan':'008080','darkGreen':'008000','darkMagenta':'800080','darkRed':'800000','darkYellow':'808000','darkGray':'808080','lightGray':'C0C0C0','black':'000000','white':'FFFFFF'}

def doc_run_background(run, paragraph, default, palette=None):
    nodes=[run._r];style=run.style;seen=set()
    while style is not None and style.style_id not in seen:
        nodes.append(style.element);seen.add(style.style_id);style=style.base_style
    for node in nodes:
        highlights=node.xpath('./w:rPr/w:highlight')
        if highlights:
            value=highlights[0].get('{'+NS['w']+'}val')
            return '#'+HIGHLIGHTS[value] if value in HIGHLIGHTS else default if value=='none' else None
        shades=node.xpath('./w:rPr/w:shd')
        if shades:
            if shades[0].get('{'+NS['w']+'}val','clear') not in {'clear','nil'} or shades[0].get('{'+NS['w']+'}themeFill'): return None
            value=shades[0].get('{'+NS['w']+'}fill','')
            return '#'+value.upper() if re.fullmatch('[0-9a-fA-F]{6}',value) else None
    return doc_background(paragraph,default,palette)


def parse_docx(path):
    doc = Document(path)
    palette=theme_colors(path)
    pages = []
    blocks = []
    image_index = 0
    backgrounds = doc.element.xpath('./w:background')
    default_bg = '#FFFFFF'
    if backgrounds:
        color = backgrounds[0].get('{'+NS['w']+'}color', '')
        default_bg = '#'+color if re.fullmatch('[0-9a-fA-F]{6}',color) else None
    if doc.element.body.xpath('.//wp:anchor'):
        default_bg = None
    total=0;has_tables=False
    for _,part,label,root,rels,package in document_parts.stories(path):
      elements=document_parts.paragraphs(root);total+=len(elements)
      if total>2000:raise MaterialError('Esta versão aceita até 2.000 parágrafos por documento.')
      has_tables |= any(True for _ in root.iter('{'+NS['w']+'}tbl'))
      drawings=list(root.iter('{'+NS['w']+'}drawing'))
      for p_index, element in enumerate(elements):
        p=Paragraph(element,doc)
        actual_runs=document_parts.runs(p);text=''.join(r.text for r in actual_runs)
        source={'part':part,'paragraph':p_index}
        prefix='' if part=='word/document.xml' else part.rsplit('/',1)[-1]+':'
        if text.strip():
            runs = []
            for r_index, run in enumerate(actual_runs):
                bg=doc_run_background(run,p,default_bg,palette)
                size, bold, color = doc_font(run, p, doc,palette,default_bg)
                runs.append({'text': run.text, 'size': size, 'bold': bold, 'color': color,
                             'background':bg,
                             'source': dict(source,run=r_index)})
            blocks.append({'id': f'{prefix}p{p_index}', 'type': 'text', 'text': text, 'runs': runs,
                           'background': doc_background(p, default_bg,palette), 'location': label+' · parágrafo '+str(p_index+1),
                           'source': source, 'heading': p.style.name.startswith('Heading')})
        for drawing in p._p.xpath('.//w:drawing'):
            owner=drawing.getparent()
            while owner is not None and owner.tag!='{'+NS['w']+'}p':owner=owner.getparent()
            if owner is not element:continue
            drawing_index = drawings.index(drawing)
            image_index += 1
            alt, decorative = picture_info(drawing)
            blips = drawing.xpath('.//a:blip')
            if not blips:
                continue
            relationship = blips[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            target=rels.get(relationship)
            if target not in package.namelist():
                continue
            blob=package.read(target)
            recognized,ocr_error=ocr(Image.open(BytesIO(blob)))
            blocks.append({'id': f'{prefix}img{drawing_index}', 'type': 'image', 'image': data_image(blob),
                           'alt': alt, 'decorative': decorative, 'location': 'Imagem '+str(drawing_index+1),
                           'ocr_text':' '.join(w['text'] for w in recognized),'ocr_error':ocr_error,
                           'source': {'part':part,'image': drawing_index}})
        if len(blocks) >= 9:
            pages.append({'label': 'Trechos '+str(len(pages)+1), 'kind': 'flow', 'blocks': blocks,
                          'width': 595, 'height': 842, 'background': default_bg})
            blocks = []
    if blocks or not pages:
        pages.append({'label': 'Trechos '+str(len(pages)+1), 'kind': 'flow', 'blocks': blocks,
                      'width': 595, 'height': 842, 'background': default_bg})
    return pages, {'format': 'DOCX', 'editable': True, 'has_tables': has_tables,
                   'preview': 'Prévia dos trechos extraídos. Os números de parágrafo identificam o conteúdo; não representam páginas do Word.'}


def pdf_color(value):
    if isinstance(value, (int, float)):
        values = [value] * 3
    elif isinstance(value, (list, tuple)) and len(value) == 3:
        values = value
    elif isinstance(value, (list, tuple)) and len(value) == 1:
        values = list(value) * 3
    else:
        return None  # CMYK / spot colors need proper color management.
    if not all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in values):
        return None
    return '#' + ''.join(f'{round(v*255):02X}' for v in values)


def pdf_background(page, box):
    # An unpainted PDF canvas is white. Anything under/over the text makes this
    # uncertain; never guess that a photographic or gradient background is white.
    x0, top, x1, bottom = box
    overlapping = []
    for collection in [page.rects, page.curves, page.images]:
        for obj in collection:
            if obj['x0'] < x1 and obj['x1'] > x0 and obj['top'] < bottom and obj['bottom'] > top:
                if obj.get('fill') or obj.get('object_type') == 'image':
                    overlapping.append(obj)
    if not overlapping: return '#FFFFFF'
    # Resolve uniform, opaque rectangles, including the full-page rectangle used
    # by Google Docs. A bounding box of a curve/image isn't proof of a flat fill.
    colors=[];covered=False
    for obj in overlapping:
        if obj.get('object_type')!='rect': return None
        color=pdf_color(obj.get('non_stroking_color'))
        if not color: return None
        colors.append(color)
        covered |= obj['x0']<=x0 and obj['x1']>=x1 and obj['top']<=top and obj['bottom']>=bottom
    return colors[0] if covered and len(set(colors))==1 else None


def parse_pdf(path):
    reader = PdfReader(path)
    if reader.is_encrypted:
        raise MaterialError('Remova a senha do PDF antes de enviar.')
    if not 1 <= len(reader.pages) <= 60:
        raise MaterialError('Esta versão aceita PDFs com até 60 páginas.')
    pages = []
    structure=inspect_pdf_structure(reader)
    with pdfplumber.open(path) as pdf:
        for index, page in enumerate(pdf.pages):
            if structure['tagged']:
                mcids={c.get('mcid') for c in page.chars if c.get('mcid') is not None}
                missing=[r['mcid'] for r in structure['reading_order'] if r['page']==index and r['mcid'] not in mcids and (index,r['mcid']) not in structure['figures']]
                if missing:structure['findings'].append({'rule':'pdf_mcid_missing','title':'Tag aponta para conteúdo não identificado','page':index,'evidence':f'Página {index+1}: MCIDs '+', '.join(str(v) for v in missing[:20])+'.'})
                if any(c.get('mcid') is None and c.get('tag')!='Artifact' and c.get('text','').strip() for c in page.chars):
                    structure['findings'].append({'rule':'pdf_text_untagged','title':'Texto fora da estrutura de tags','page':index,'evidence':f'Página {index+1}: caracteres sem MCID de estrutura identificado.'})
            resources=reader.pages[index].get('/Resources',{})
            resources=resources.get_object() if hasattr(resources,'get_object') else resources
            # PDF shadings paint gradients without a rect/curve that pdfplumber
            # can resolve. Resources inside forms can carry their own shading or
            # transparency. Without a complete compositor, leave those unknown.
            def complex_resources(res, seen=None):
                seen = set() if seen is None else seen
                res = res.get_object() if hasattr(res,'get_object') else res
                if id(res) in seen: return False
                seen.add(id(res))
                if res.get('/Shading'): return True
                ext = res.get('/ExtGState', {})
                ext = ext.get_object() if hasattr(ext,'get_object') else ext
                for value in ext.values():
                    value = value.get_object() if hasattr(value,'get_object') else value
                    blend = value.get('/BM','/Normal')
                    if float(value.get('/ca',1))!=1 or value.get('/SMask','/None')!='/None' or not isinstance(blend,str) or blend not in {'/Normal','/Compatible'}: return True
                objects = res.get('/XObject', {})
                objects = objects.get_object() if hasattr(objects,'get_object') else objects
                for obj in objects.values():
                    obj = obj.get_object() if hasattr(obj,'get_object') else obj
                    if obj.get('/Subtype')=='/Form':
                        if obj.get('/Group') or complex_resources(obj.get('/Resources', {}), seen): return True
                return False
            uncertain_blend=complex_resources(resources)
            words = page.extract_words(extra_attrs=['fontname', 'size', 'non_stroking_color'])
            pixels=None
            for word in words:
                word['background']=None if uncertain_blend else pdf_background(page,[word['x0'],word['top'],word['x1'],word['bottom']])
                if word['background'] is None or pdf_color(word.get('non_stroking_color')) is None:
                    if pixels is None:
                        with PDF_LOCK:pixels=PdfPixels(path,index)
                    measurement=pixels.measure([word['x0'],word['top'],word['x1'],word['bottom']],pdf_color(word.get('non_stroking_color')),contrast)
                    if measurement:
                        word['rendered']=measurement;word['background']=measurement[2]
            if len(words) > 3000:
                raise MaterialError('Uma página excede 3.000 palavras. Divida esse material para testar nesta versão.')
            blocks = []
            group = []
            def flush():
                if not group:
                    return
                text = ' '.join(w['text'] for w in group)
                box = [min(w['x0'] for w in group), min(w['top'] for w in group),
                       max(w['x1'] for w in group), max(w['bottom'] for w in group)]
                first = min(group,key=lambda w:w.get('rendered',(999,))[0])
                blocks.append({'id': f'pdf{index}-t{len(blocks)}', 'type': 'text', 'text': text,
                               'x': box[0], 'y': box[1], 'w': box[2]-box[0], 'h': box[3]-box[1],
                               'background': first['background'],
                               'runs': [{'text': text, 'size': float(first['size']),
                                         'bold': 'bold' in first['fontname'].lower(),
                                         'color': first['rendered'][1] if first.get('rendered') else pdf_color(first.get('non_stroking_color')),
                                         'measured_contrast': first.get('rendered',(None,))[0],
                                         'estimated': bool(first.get('rendered'))}]})
                group.clear()
            for word in words:
                if group and (abs(word['top']-group[-1]['top']) > 2 or
                              word['size'] != group[-1]['size'] or word['fontname'] != group[-1]['fontname'] or
                              word.get('non_stroking_color') != group[-1].get('non_stroking_color') or
                              word['background'] != group[-1]['background'] or
                              word['x0']-group[-1]['x1'] > 24):
                    flush()
                group.append(word)
            flush()
            ocr_error=''
            if not words:
                if pixels is None:
                    with PDF_LOCK:pixels=PdfPixels(path,index)
                recognized,ocr_error=ocr_blocks(pixels.original,f'pdf{index}',page.width,page.height)
                blocks.extend(recognized)
            for img_index, image in enumerate(page.images):
                figure=structure['figures'].get((index,image.get('mcid')))
                if pixels is None:
                    with PDF_LOCK:pixels=PdfPixels(path,index)
                crop=pixels.original.crop((image['x0']*pixels.scale,image['top']*pixels.scale,image['x1']*pixels.scale,image['bottom']*pixels.scale))
                recognized,img_error=ocr(crop)
                buffer=BytesIO();crop.save(buffer,format='PNG')
                blocks.append({'id': f'pdf{index}-i{img_index}', 'type': 'image' if figure else 'pdf_image', 'alt': figure['alt'] if figure else None,
                               'image':data_image(buffer.getvalue()),'ocr_text':' '.join(w['text'] for w in recognized),'ocr_error':img_error,
                               'x': image['x0'], 'y': image['top'], 'w': image['width'], 'h': image['height']})
            pages.append({'label': 'Página '+str(index+1), 'kind': 'pdf', 'blocks': blocks,
                          'width': page.width, 'height': page.height, 'background': '#FFFFFF',
                          'has_text': bool(words), 'ocr_error':ocr_error,'ocr_text':' '.join(b['text'] for b in blocks if b.get('ocr')), 'page_index': index})
            if pixels is not None:
                with PDF_LOCK:pixels.close()
    return pages, {'format': 'PDF', 'editable': False, 'tagged': structure['tagged'],
                   'structure_findings':structure['findings'],'structure_elements':structure['elements'],'reading_order':structure['reading_order'],
                   'preview': 'Imagem do PDF original. Marcações indicam posições extraídas; conferir a estrutura e a ordem de leitura exige revisão.'}


def parse_image(path):
    with Image.open(path) as image:
        image.verify()
    preview = data_image(path.read_bytes())
    with Image.open(path) as image:
        width, height = image.size
        recognized,error=ocr_blocks(image,'image')
    return [{'label': 'Imagem enviada', 'kind': 'raster', 'width': width, 'height': height,
             'ocr_error':error,'ocr_text':' '.join(b['text'] for b in recognized),
             'background': '#FFFFFF', 'blocks': [{'id': 'image0', 'type': 'scan', 'image': preview,
                                                  'alt': '', 'location': 'Imagem enviada'}]+recognized}], {
        'format': path.suffix[1:].upper(), 'editable': False,
        'preview': 'Imagem original com texto reconhecido localmente quando o OCR está disponível. Contraste por pixels é estimado; a fonte original não é determinada pela altura da imagem.'}


def analyze(path, context):
    validate_context(context); validate_file(path)
    try:
        parser = {'.pdf': parse_pdf, '.docx': parse_docx, '.pptx': parse_pptx}.get(path.suffix.lower(), parse_image)
        pages, info = parser(path)
    except MaterialError:
        raise
    except Exception as exc:
        raise MaterialError('Não foi possível interpretar esse arquivo. Verifique se ele abre no programa original e tente exportá-lo novamente.') from exc
    issues = []
    measured = {'text': 0, 'contrast': 0, 'font': 0, 'images': 0, 'unknown_contrast': 0, 'unknown_font': 0, 'estimated_contrast':0}

    def add(rule, title, explanation, suggestion, page, block=None, severity='attention', evidence='', action=None):
        block_id = block['id'] if block else 'document'
        loc = (block or {}).get('location') or (pages[page]['label'] if page is not None else 'Documento')
        issues.append({'id': f'{rule}:{page}:{block_id}', 'rule': rule, 'title': title,
                       'explanation': explanation, 'suggestion': suggestion, 'severity': severity,
                       'evidence': evidence, 'page': page, 'block_id': block_id, 'location': loc,
                       'action': action, 'source': (block or {}).get('source'),
                       'text': (block or {}).get('text', '')[:240]})

    minimum = context.get('min_font')
    for pi, page in enumerate(pages):
        if info['format'] == 'PPTX' and not page['title']:
            add('slide_title', 'Slide sem título identificado', 'Não foi encontrado um título no campo de título deste slide. Um texto visualmente destacado pode não estar definido como título.',
                'No PowerPoint, use o espaço reservado de título e preencha um título que identifique o conteúdo.', pi,
                severity='review')
        if page['kind'] == 'pdf' and not page['has_text']:
            add('image_only', 'Página sem texto extraível', 'Não foi possível extrair texto desta página. Se houver palavras visíveis, elas podem estar em uma imagem ou convertidas em desenho.',
                'Se houver texto, transcreva ou use OCR e confira a transcrição. Depois organize a ordem de leitura.', pi)
        if page.get('ocr_error'):
            add('ocr_unavailable','Reconhecimento de texto não concluído',page['ocr_error'],
                'Confira o texto da imagem. O reconhecimento local precisa estar instalado e a imagem deve ter resolução suficiente.',pi,severity='review',evidence=page['ocr_error'])
        if page.get('ocr_text'):
            add('ocr_review','Confira o texto reconhecido','O reconhecimento pode trocar letras, números e símbolos. A transcrição não foi aprovada automaticamente.',
                'Abra Texto para leitura, confira a transcrição e corrija os trechos necessários antes de compartilhar.',pi,severity='review',evidence=page['ocr_text'][:500])
        unknown_color = False
        unknown_size = False
        for block in page['blocks']:
            if block['type'] == 'text' and block['text'].strip():
                measured['text'] += 1
                runs = [r for r in block.get('runs', []) if r['text'].strip()]
                sizes = [r['size'] for r in runs if r['size'] is not None]
                if minimum:
                    if len(sizes) != len(runs):
                        measured['unknown_font'] += 1; unknown_size = True
                    if sizes:
                        measured['font'] += 1
                        if min(sizes) < minimum:
                            add('font_size', 'Fonte abaixo do tamanho informado',
                                f'O trecho tem fonte de {min(sizes):g} pt; você informou {minimum:g} pt para este estudante.',
                                f'Aumente para pelo menos {minimum:g} pt e confira se o texto cabe sem cortes ou sobreposições.', pi, block,
                                evidence=f'Menor fonte identificada: {min(sizes):g} pt. Preferência: {minimum:g} pt.',
                                action='font' if info['editable'] else None)
                bad = []
                contrast_runs=[]
                for run in runs:
                    background=run.get('background') if 'background' in run else block.get('background')
                    if run.get('color') and background:
                        measured['contrast'] += 1
                        if run.get('estimated'):measured['estimated_contrast']+=1
                        ratio = run.get('measured_contrast') if run.get('measured_contrast') is not None else contrast(run['color'], background)
                        required = threshold(run.get('size'), run.get('bold'))
                        if ratio < required:
                            bad.append((ratio, required, run['color'], background))
                            if run.get('source'): contrast_runs.append({'source':run['source'],'background':background})
                    else:
                        measured['unknown_contrast'] += 1; unknown_color = True
                if bad:
                    ratio, required, fg, bg = min(bad)
                    add('contrast', 'Contraste de texto abaixo da referência',
                        f'O contraste medido neste trecho é {ratio:.2f}:1, abaixo da referência de {required:g}:1 para o tamanho e o peso identificados.',
                        'Mude a cor do texto ou do fundo para aumentar o contraste. Confira a combinação no arquivo original.', pi, block,
                        evidence=f'{fg} sobre {bg}: {ratio:.2f}:1. Referência: {required:g}:1.',
                        action='contrast' if info['editable'] else None)
                    issues[-1]['background']=bg
                    issues[-1]['contrast_runs']=contrast_runs
                    if any(r.get('estimated') for r in runs):
                        issues[-1]['explanation']=f'O contraste estimado pela imagem da página é {ratio:.2f}:1, abaixo da referência de {required:g}:1. Confira as cores no original.'
                        issues[-1]['evidence']+=' Medição da imagem renderizada; contraste estimado, confira o resultado.'
            elif block['type'] == 'image':
                measured['images'] += 1
                if not block.get('decorative'):
                    if not block.get('alt'):
                        add('alt_missing', 'Imagem sem descrição alternativa',
                            'Esta imagem não tem descrição alternativa associada. O leitor de tela pode não comunicar a informação que ela apresenta.',
                            'Descreva a informação necessária para a atividade. Se a imagem apenas enfeita a página, marque-a como decorativa no arquivo de origem.',
                            pi, block, action='alt' if info['editable'] else None, evidence='Descrição alternativa ausente nos metadados.')
                    elif re.fullmatch(r'(?:image|picture|imagem|foto)[\s_\d-]*(?:\.(?:png|jpe?g|gif|bmp))?', block['alt'], re.I):
                        add('alt_placeholder', 'Descrição de imagem genérica',
                            'A descrição encontrada é um nome genérico, como um nome de arquivo. Ela não informa o que a imagem mostra.',
                            'Substitua esse nome pela informação da imagem que o estudante precisa para realizar a atividade.',
                            pi, block, action='alt' if info['editable'] else None, evidence=block['alt'])
                    else:
                        add('alt_quality', 'Conferir o sentido da descrição',
                            'A imagem tem descrição. O site não verificou se esse texto corresponde ao que ela mostra.',
                            'Compare a descrição encontrada com a imagem: ela identifica o conteúdo e inclui a informação pedida no enunciado? Corrija o que estiver errado ou faltando.',
                            pi, block, severity='review', evidence=block['alt'], action='alt' if info['editable'] else None)
                    issues[-1]['image']=block.get('image')
                    issues[-1]['image_text']=block.get('ocr_text','')
                    if block.get('ocr_text'):
                        words={w.lower() for w in re.findall(r'\w+',block['ocr_text']) if len(w)>3}
                        missing=sorted(words-{w.lower() for w in re.findall(r'\w+',block.get('alt',''))})
                        if missing:issues[-1]['evidence']+=' Texto na imagem que não aparece na descrição: '+', '.join(missing[:15])+'. Confira se precisa ser incluído.'
            elif block['type'] in {'pdf_image', 'scan'}:
                measured['images'] += 1
                add('image_review', 'Conferir o acesso ao conteúdo da imagem',
                    'Foi encontrada uma imagem, mas não foi possível confirmar uma descrição associada a ela na estrutura do arquivo.',
                    'No arquivo de origem, confira se a imagem tem descrição alternativa. Se houver palavras na imagem, inclua uma transcrição acessível.',
                    pi, block, severity='review')
            elif block['type'] in {'table', 'unsupported'}:
                add('visual_review', 'Elemento que precisa de revisão',
                    'Este elemento não foi interpretado como texto comum; sua informação e organização precisam de conferência.',
                    'Se for tabela, confira os cabeçalhos e a relação entre células. Se for gráfico ou outro objeto, forneça os dados e a informação necessária em texto.',
                    pi, block, severity='review')
        if unknown_color:
            add('contrast_unknown', 'Contraste parcialmente não determinado',
                'Não foi possível medir com confiança o contraste de alguns trechos desta página.',
                'Confira no programa original as cores efetivas do texto e do fundo, principalmente sobre imagens e transparências.', pi, severity='review')
        if unknown_size:
            add('font_unknown', 'Alguns tamanhos de fonte não determinados',
                'Não foi possível identificar o tamanho efetivo da fonte de alguns trechos desta página.',
                'Confira o tamanho efetivo dos trechos no programa original.', pi, severity='review')
    if info['format'] == 'PDF':
        structure_guidance={
            'pdf_tags_empty':('O PDF declara uma estrutura de leitura, mas ela está vazia ou não contém elementos utilizáveis.','No arquivo de origem, defina títulos, parágrafos e demais elementos. Exporte novamente com tags de acessibilidade.'),
            'pdf_heading_skip':('A sequência de títulos pula um nível na estrutura de leitura do PDF.','No arquivo de origem, use os níveis em sequência: título 1, título 2 e título 3. Exporte o PDF novamente com essa estrutura.'),
            'pdf_table_headers':('A tabela não tem células identificadas como cabeçalho na estrutura do PDF.','Defina as células de cabeçalho no arquivo de origem ou em um editor de tags de PDF. Confira se o leitor de tela associa cada dado ao cabeçalho correto.'),
            'pdf_figure_alt':('Uma figura está identificada na estrutura do PDF, mas não possui descrição alternativa.','Adicione a descrição à figura no arquivo de origem ou em um editor de tags de PDF. Depois exporte e confira novamente.'),
            'pdf_language_missing':('O idioma principal não está informado no PDF. Isso pode afetar a pronúncia do leitor de tela.','Defina o idioma principal do documento no arquivo de origem ou nas propriedades do PDF.'),
            'pdf_text_untagged':('Há texto nesta página que não está associado à estrutura de leitura do PDF.','Associe esse texto a parágrafos, títulos ou células no arquivo de origem ou em um editor de tags. Exporte e confira a sequência com um leitor de tela.'),
            'pdf_mcid_missing':('A estrutura desta página referencia conteúdo que a inspeção não conseguiu localizar.','Confira essas referências em um editor de tags de PDF. Refaça a exportação se a estrutura estiver quebrada; o aviso sozinho não prova que o conteúdo foi perdido.'),
            'pdf_tag_orphan':('Um elemento da estrutura aponta para conteúdo sem identificar a página correspondente.','Em um editor de tags de PDF, confira a associação desse elemento ao conteúdo e à página.'),
            'pdf_structure_cycle':('Uma referência se repete na árvore de leitura; a inspeção não conseguiu percorrê-la por completo.','Confira a árvore de tags em um editor de PDF e corrija as referências repetidas ou refaça a exportação.'),
            'pdf_structure_limit':('A estrutura excedeu o limite de inspeção. Parte dela ficou sem verificação.','Divida o documento para análise ou confira a estrutura completa em um editor de tags de PDF.'),
        }
        for finding in info.get('structure_findings',[]):
            explanation,suggestion=structure_guidance.get(finding['rule'],('A inspeção identificou a ocorrência descrita abaixo na estrutura do PDF.','Confira o elemento indicado em um editor de tags de PDF.'))
            add(finding['rule'],finding['title'],explanation,suggestion,finding.get('page'),evidence=finding['evidence'])
        if not info.get('tagged'):
            add('pdf_structure', 'PDF sem estrutura de tags identificada',
                'O PDF não tem uma árvore de tags identificada para organizar títulos, parágrafos, tabelas e imagens.',
                'Defina esses elementos no arquivo de origem e exporte com tags de acessibilidade. Confira a ordem de leitura com um leitor de tela.', None)
        else:
            add('pdf_structure_review', 'Conferir estrutura e ordem de leitura',
                'O PDF tem tags de estrutura. A inspeção não confirmou se a sequência delas acompanha o sentido do conteúdo.',
                'Percorra o documento com um leitor de tela: títulos, parágrafos e etapas devem aparecer na ordem correta, sem saltos ou repetições.', None, severity='review')
    if info.get('has_tables'):
        add('table_review', 'Conferir a estrutura das tabelas', 'O documento contém tabelas. A inspeção não confirmou a associação entre cada célula e seus cabeçalhos.',
            'No arquivo de origem, defina a linha de cabeçalho. Com um leitor de tela, confira se cada célula é anunciada com o cabeçalho correspondente.', None, severity='review')
    issues.sort(key=lambda i: (i['severity'] == 'review', i['page'] if i['page'] is not None else -1, i['id']))
    for index, issue in enumerate(issues):
        issue['number'] = index + 1
    for issue in issues:
        if issue['rule']=='contrast_unknown':
            issue['explanation']='Não foi possível medir com confiança o contraste de alguns trechos desta página. Eles continuam sem resultado de contraste.'
    checks = [
        {'name': 'Contraste de texto', 'detail': f"{measured['contrast']} trechos medidos, sendo {measured['estimated_contrast']} por imagem renderizada; {measured['unknown_contrast']} sem cálculo confiável.", 'state': 'partial' if measured['estimated_contrast'] or measured['unknown_contrast'] or not measured['contrast'] else 'checked'},
        {'name': 'Tamanho da fonte', 'detail': f"Preferência: {minimum:g} pt. {measured['font']} blocos medidos." if minimum else 'Informe uma preferência do estudante para comparar os tamanhos.', 'state': 'partial' if not minimum or measured['unknown_font'] or not measured['font'] else 'checked'},
        {'name': 'Descrições de imagens', 'detail': f"{measured['images']} elementos de imagem identificados. O significado exige revisão humana.", 'state': 'partial'},
        {'name': 'Estrutura e significado', 'detail': 'A ordem de leitura, o sentido dos gráficos e a preservação da atividade precisam ser conferidos.', 'state': 'review'},
    ]
    return {'engine_version':ENGINE_VERSION,'pages': pages, 'info': info, 'issues': issues, 'checks': checks, 'context': context,
            'counts': {'attention': sum(i['severity'] == 'attention' for i in issues),
                       'review': sum(i['severity'] == 'review' for i in issues), 'pages': len(pages)},
            'measured': measured}


def apply_edit(source, destination, issue, value=None):
    action = issue.get('action')
    ref = issue.get('source') or {}
    if action not in {'font', 'contrast', 'alt'}:
        raise MaterialError('Esse item precisa ser corrigido no programa original e reenviado.')
    if action == 'font':
        value = float(value)
        if not 6 <= value <= 96:
            raise MaterialError('O tamanho precisa estar entre 6 e 96 pontos.')
    elif action == 'alt':
        value = str(value or '').strip()
        if not value or len(value) > 3000:
            raise MaterialError('Escreva uma descrição com até 3.000 caracteres.')
    if source.suffix.lower() == '.pptx':
        from pptx.dml.color import RGBColor
        prs = Presentation(source)
        shape = prs.slides[ref['slide']].shapes[ref['shape']]
        for index in ref.get('shape_path',[ref['shape']])[1:]: shape=shape.shapes[index]
        if action == 'alt':
            props = [n for n in shape._element.iter() if n.tag.split('}')[-1] == 'cNvPr']
            props[0].set('descr', value)
        else:
            text_frame=shape.table.cell(ref['row'],ref['column']).text_frame if 'row' in ref else shape.text_frame
            for p_index,paragraph in enumerate(text_frame.paragraphs):
                for r_index,run in enumerate(paragraph.runs):
                    if action == 'font':
                        run.font.size = Pt(value)
                    else:
                        targets=issue.get('contrast_runs',[])
                        target=next((t for t in targets if t['source'].get('paragraph')==p_index and t['source'].get('run')==r_index),None) if targets else None
                        if targets and target is None: continue
                        background = (target or {}).get('background') or issue.get('background') or '#FFFFFF'
                        color = max(['#000000', '#FFFFFF'], key=lambda c: contrast(c, background))
                        run.font.color.rgb = RGBColor.from_string(color[1:])
        prs.save(destination)
    elif source.suffix.lower() == '.docx':
        document_parts.patch(source,destination,ref,action,value,issue.get('contrast_runs',[]),issue.get('background'),contrast)
    else:
        raise MaterialError('A edição de PDF e imagens será feita no programa original nesta versão.')


def decorate_actions(result):
    for issue in result['issues']:
        if issue['action'] == 'contrast' and issue['page'] is not None:
            block = next(b for b in result['pages'][issue['page']]['blocks'] if b['id'] == issue['block_id'])
            if not issue.get('background'): issue['background'] = block.get('background')
    return result


def demo_pptx(destination):
    from PIL import ImageDraw
    from pptx.util import Inches
    from pptx.dml.color import RGBColor
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(10), Inches(5.625)
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.background.fill.solid(); slide.background.fill.fore_color.rgb = RGBColor(255, 255, 255)
    title = slide.shapes.title
    title.left, title.top, title.width, title.height = Inches(.65), Inches(.4), Inches(8.8), Inches(.65)
    title.text = 'Geografia: população e território'
    title.text_frame.paragraphs[0].runs[0].font.size = Pt(30)
    title.text_frame.paragraphs[0].runs[0].font.color.rgb = RGBColor.from_string('24264F')
    box = slide.shapes.add_textbox(Inches(.7), Inches(1.3), Inches(8.6), Inches(.8))
    box.text = 'Observe o gráfico e compare os valores das três regiões.'
    run = box.text_frame.paragraphs[0].runs[0]
    run.font.size = Pt(14); run.font.color.rgb = RGBColor.from_string('AAAAAA')
    image = Image.new('RGB', (740, 260), 'white'); draw = ImageDraw.Draw(image)
    draw.line((55,220,700,220), fill='#303849', width=2)
    for x,h,label in [(100,85,'Região A'),(300,140,'Região B'),(500,185,'Região C')]:
        draw.rectangle((x,220-h,x+105,220), fill='#126665'); draw.text((x,235),label,fill='black')
        draw.text((x+40,200-h), str(h), fill='black')
    draw.text((55,8),'População (em milhares)',fill='black')
    buffer = BytesIO(); image.save(buffer, format='PNG'); buffer.seek(0)
    picture = slide.shapes.add_picture(buffer, Inches(.9), Inches(2.2), width=Inches(8.2))
    for node in picture._element.iter():
        if node.tag.split('}')[-1] == 'cNvPr':
            node.attrib.pop('descr', None)
    prs.save(destination)
