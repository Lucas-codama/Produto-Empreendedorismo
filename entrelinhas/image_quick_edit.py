"""Quick image adjustments in the original document location."""
import math
import re
import zipfile
from lxml import etree as ET
from analyzer import MaterialError

def apply(source,destination,block,value):
    if not isinstance(value,dict) or set(value)-{'alt','caption','scale'}:raise MaterialError('Confira os ajustes da imagem.')
    alt=value.get('alt');caption=value.get('caption','')
    if not isinstance(caption,str):raise MaterialError('Escreva uma legenda válida.')
    for text in (alt,caption):
        if text is not None and (not isinstance(text,str) or len(text)>3000 or re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]',text)):raise MaterialError('Escreva uma descrição com até 3.000 caracteres.')
    if alt is not None and not alt.strip():raise MaterialError('Escreva uma descrição antes de salvar.')
    try:scale=float(value.get('scale',1))
    except (ValueError,TypeError):raise MaterialError('Escolha uma ampliação válida.')
    if not math.isfinite(scale) or not 1<=scale<=2:raise MaterialError('A ampliação deve ficar entre 100% e 200%.')
    if source.suffix=='.docx':word(source,destination,block,alt,caption,scale)
    elif source.suffix=='.pptx':slides(source,destination,block,alt,caption,scale)
    elif source.suffix=='.pdf':pdf(source,destination,block,alt,caption,scale)
    else:raise MaterialError('Para alterar esta imagem avulsa, use o editor original.')

def word(source,destination,block,alt,caption,scale):
    from docx.oxml.ns import qn
    ref=block['source'];part=ref['part']
    with zipfile.ZipFile(source) as package:
        root=ET.fromstring(package.read(part),parser=ET.XMLParser(resolve_entities=False,no_network=True))
        drawing=list(root.iter(qn('w:drawing')))[ref['image']]
        if alt is not None:
            props=drawing.find('.//'+qn('wp:docPr'));props.set('descr',alt.strip())
        if scale!=1:
            if drawing.find('.//'+qn('wp:anchor')) is not None:raise MaterialError('Esta imagem está flutuando sobre o texto. Amplie no editor original para evitar sobreposições.')
            for extent in drawing.iter():
                if extent.tag in {qn('wp:extent'),qn('a:ext')} and extent.get('cx') and extent.get('cy'):
                    extent.set('cx',str(round(int(extent.get('cx'))*scale)));extent.set('cy',str(round(int(extent.get('cy'))*scale)))
            extent=drawing.find('.//'+qn('wp:extent'))
            section=root.find('.//'+qn('w:sectPr'))
            if extent is not None and section is not None:
                size=section.find(qn('w:pgSz'));margin=section.find(qn('w:pgMar'))
                if size is not None and margin is not None:
                    available=(int(size.get(qn('w:w')))-int(margin.get(qn('w:left'),'0'))-int(margin.get(qn('w:right'),'0')))*635
                    if int(extent.get('cx'))>available:raise MaterialError('A imagem ampliada ultrapassa a largura da página. Escolha uma ampliação menor.')
        paragraph=next(drawing.iterancestors(qn('w:p')),None)
        caption_name='EntrelinhasCaption'+drawing.find('.//'+qn('wp:docPr')).get('id','0')
        sibling=paragraph.getnext()
        if sibling is not None and any(n.get(qn('w:name'))==caption_name for n in sibling.iter(qn('w:bookmarkStart'))):paragraph.getparent().remove(sibling)
        if caption.strip():
            note=ET.Element(qn('w:p'));run=ET.SubElement(note,qn('w:r'));props=ET.SubElement(run,qn('w:rPr'))
            bookmark_id=str(max([int(n.get(qn('w:id'),'0')) for n in root.iter(qn('w:bookmarkStart'))]+[0])+1)
            mark=ET.Element(qn('w:bookmarkStart'));mark.set(qn('w:name'),caption_name);mark.set(qn('w:id'),bookmark_id);note.insert(0,mark)
            end=ET.SubElement(note,qn('w:bookmarkEnd'));end.set(qn('w:id'),bookmark_id)
            ET.SubElement(props,qn('w:sz')).set(qn('w:val'),'40');ET.SubElement(props,qn('w:color')).set(qn('w:val'),'000000');shade=ET.SubElement(props,qn('w:shd'));shade.set(qn('w:val'),'clear');shade.set(qn('w:fill'),'FFFFFF')
            ET.SubElement(run,qn('w:t')).text=caption.strip();paragraph.addnext(note)
        content=ET.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
        with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as output:
            for item in package.infolist():output.writestr(item,content if item.filename==part else package.read(item.filename))

def slides(source,destination,block,alt,caption,scale):
    from pptx import Presentation
    from pptx.util import Pt,Inches
    from pptx.dml.color import RGBColor
    ref=block['source'];prs=Presentation(source);slide=prs.slides[ref['slide']];shape=slide.shapes[ref['shape']]
    if len(ref.get('shape_path',[]))>1:raise MaterialError('Esta imagem está dentro de um grupo. Ajuste o grupo no PowerPoint para preservar o layout.')
    width,height=round(shape.width*scale),round(shape.height*scale)
    caption_name='EntrelinhasCaption'+str(shape.shape_id)
    old_captions=[other for other in slide.shapes if other.name==caption_name]
    x,y=shape.left,shape.top
    def free(rect):
        left,top,w,h=rect
        if left<0 or top<0 or left+w>prs.slide_width or top+h>prs.slide_height:return False
        for other in slide.shapes:
            if other.shape_id==shape.shape_id or other.name==caption_name:continue
            overlaps=left<other.left+other.width and left+w>other.left and top<other.top+other.height and top+h>other.top
            # Background rectangles can cover the slide without occupying reading space.
            background=other.left<=left and other.top<=top and other.left+other.width>=left+w and other.top+other.height>=top+h and other.shape_type==1 and not getattr(other,'text','').strip()
            if overlaps and not background:return False
        return True
    if x+width>prs.slide_width or y+height>prs.slide_height:raise MaterialError('A imagem ampliada não cabe neste slide. Escolha uma ampliação menor.')
    if scale>1 and not free((x,y,width,height)):raise MaterialError('A ampliação cobriria outro elemento do slide. Escolha uma ampliação menor.')
    caption_rect=None
    if caption.strip():
        # Measure wrapping with a conservative 20 pt font estimate, including margins.
        from reportlab.pdfbase.pdfmetrics import stringWidth
        gap=Inches(.04)
        def caption_size(w):
            available=max(1,(w-Inches(.2))/12700)
            lines=0
            for line in caption.strip().splitlines():
                used=0;lines+=1
                for word in line.split():
                    size=stringWidth(word+' ','Helvetica',20)*1.05
                    if size>available:return None
                    if used and used+size>available:lines+=1;used=0
                    used+=size
            return Pt(lines*25+6)
        candidates=[(x,y+height+gap,width), (x+width+gap,y,prs.slide_width-x-width-2*gap), (gap,y,x-2*gap)]
        for left,top,w in candidates:
            h=caption_size(w) if w>=Inches(1.5) else None
            if h and free((left,top,w,h)):caption_rect=(left,top,w,h);break
        if caption_rect is None:
            h=caption_size(width)
            if h and free((x,y-gap-h,width,h)):caption_rect=(x,y-gap-h,width,h)
        if caption_rect is None:raise MaterialError('Não há espaço livre para a legenda neste slide. Desmarque a legenda para salvar só a descrição ou ajuste o layout no PowerPoint.')
    shape.width,shape.height=width,height
    if alt is not None:
        props=next(n for n in shape._element.iter() if n.tag.endswith('}cNvPr'));props.set('descr',alt.strip())
    for old in old_captions:old._element.getparent().remove(old._element)
    if caption.strip():
        box=slide.shapes.add_textbox(*caption_rect);box.name=caption_name;box.text=caption.strip();box.text_frame.word_wrap=True
        for paragraph in box.text_frame.paragraphs:
            for run in paragraph.runs:run.font.name='Arial';run.font.size=Pt(20);run.font.color.rgb=RGBColor(0,0,0)
        box.fill.solid();box.fill.fore_color.rgb=RGBColor(255,255,255)
    prs.save(destination)

def pdf(source,destination,block,alt,caption,scale):
    from pdf_image_edit import edit
    edit(source,destination,block,alt,caption,scale)
