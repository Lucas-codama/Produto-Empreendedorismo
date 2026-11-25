"""Edit one identified PDF image occurrence and its caption on the original page."""
from io import BytesIO
import uuid
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (ArrayObject, BooleanObject, ContentStream, DictionaryObject,
    FloatObject, NameObject, NullObject, NumberObject, TextStringObject)


def multiply(a,b):
    return (a[0]*b[0]+a[1]*b[2],a[0]*b[1]+a[1]*b[3],
            a[2]*b[0]+a[3]*b[2],a[2]*b[1]+a[3]*b[3],
            a[4]*b[0]+a[5]*b[2]+b[4],a[4]*b[1]+a[5]*b[3]+b[5])


def image_target(page,stream,block):
    matrix=(1,0,0,1,0,0);stack=[];matches=[]
    resources=page['/Resources'].get_object().get('/XObject',{}).get_object()
    expected=(block['x'],float(page.mediabox.height)-block['y']-block['h'],block['w'],block['h'])
    for index,(args,op) in enumerate(stream.operations):
        if op==b'q':stack.append(matrix)
        elif op==b'Q':matrix=stack.pop() if stack else (1,0,0,1,0,0)
        elif op==b'cm':matrix=multiply(tuple(float(v) for v in args),matrix)
        elif op==b'Do':
            obj=resources.get(args[0]);obj=obj.get_object() if obj is not None else {}
            if obj.get('/Subtype')!='/Image':continue
            a,b,c,d,x,y=matrix
            if abs(b)>.001 or abs(c)>.001 or a<=0 or d<=0:continue
            if all(abs(v-w)<2 for v,w in zip((x,y,a,d),expected)):matches.append((index,matrix))
    return matches[0] if len(matches)==1 else None


def structure_node(writer,path):
    node=writer.root_object['/StructTreeRoot'].get_object()
    for part in path:node=node[part if isinstance(part,int) else '/'+part].get_object()
    return node


def number_entries(node,result=None):
    result={} if result is None else result
    node=node.get_object()
    values=node.get('/Nums',[])
    for index in range(0,len(values),2):result[int(values[index])]=values[index+1]
    for child in node.get('/Kids',[]):number_entries(child,result)
    return result


def add_figure(writer,page,stream,alt):
    root=writer.root_object
    if '/StructTreeRoot' not in root:
        tree=DictionaryObject({NameObject('/Type'):NameObject('/StructTreeRoot'),NameObject('/K'):ArrayObject()})
        root[NameObject('/StructTreeRoot')]=writer._add_object(tree)
    tree=root['/StructTreeRoot'].get_object()
    entries=number_entries(tree['/ParentTree']) if tree.get('/ParentTree') else {}
    key=int(page['/StructParents']) if '/StructParents' in page else max(entries,default=-1)+1
    parents=entries.get(key,ArrayObject());parents=parents.get_object()
    if not isinstance(parents,ArrayObject):raise ValueError('Invalid page parent tree')
    used=[int(args[1]['/MCID']) for args,op in stream.operations if op==b'BDC' and len(args)>1 and isinstance(args[1],dict) and '/MCID' in args[1]]
    mcid=max(used+[len(parents)-1],default=-1)+1
    figure=DictionaryObject({NameObject('/Type'):NameObject('/StructElem'),NameObject('/S'):NameObject('/Figure'),
        NameObject('/P'):tree.indirect_reference,NameObject('/Pg'):page.indirect_reference,
        NameObject('/K'):NumberObject(mcid),NameObject('/Alt'):TextStringObject(alt)})
    reference=writer._add_object(figure)
    kids=tree.get('/K',ArrayObject());kids=kids.get_object()
    if not isinstance(kids,ArrayObject):kids=ArrayObject([kids])
    kids.append(reference);tree[NameObject('/K')]=kids
    while len(parents)<=mcid:parents.append(NullObject())
    parents[mcid]=reference;entries[key]=parents
    nums=ArrayObject()
    for entry,value in sorted(entries.items()):nums.extend([NumberObject(entry),value])
    tree[NameObject('/ParentTree')]=writer._add_object(DictionaryObject({NameObject('/Nums'):nums}))
    tree[NameObject('/ParentTreeNextKey')]=NumberObject(max(entries)+1)
    page[NameObject('/StructParents')]=NumberObject(key)
    mark=root.get('/MarkInfo',DictionaryObject()).get_object();mark[NameObject('/Marked')]=BooleanObject(True);root[NameObject('/MarkInfo')]=mark
    return figure,mcid


def edit(source,destination,block,alt,caption,scale):
    from analyzer import MaterialError
    import pdfplumber
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase.pdfmetrics import stringWidth
    ref=block.get('source') or {};index=ref.get('pdf_page')
    if index is None:raise MaterialError('Não foi possível localizar esta imagem na página. Analise o documento novamente.')
    writer=PdfWriter(clone_from=str(source));page=writer.pages[index]
    if page.rotation or any(abs(float(v))>.01 for v in page.mediabox.lower_left) or list(page.cropbox)!=list(page.mediabox):
        raise MaterialError('Esta página tem rotação ou recorte. Ajuste a imagem no editor original para preservar o layout.')
    stream=ContentStream(page.get_contents(),writer);target=image_target(page,stream,block)
    if not target:raise MaterialError('Não foi possível isolar esta imagem. Ajuste no editor original para preservar o restante da página.')
    figure=structure_node(writer,ref['pdf_path']) if ref.get('pdf_path') else None
    caption_key=str(figure.get('/EntrelinhasCaptionKey','')) if figure is not None else ''
    old_box=[float(v) for v in figure.get('/EntrelinhasCaptionBox',[])] if figure is not None else []
    # Remove only the caption created for this image in an earlier edit.
    if caption_key:
        cleaned=[];skip=0
        for args,op in stream.operations:
            if op==b'BDC' and len(args)>1 and isinstance(args[1],dict) and str(args[1].get('/EntrelinhasCaption',''))==caption_key:skip=1;continue
            if skip:
                if op in (b'BDC',b'BMC'):skip+=1
                elif op==b'EMC':skip-=1
                continue
            cleaned.append((args,op))
        stream.operations=cleaned;target=image_target(page,stream,block)
        if not target:raise MaterialError('A imagem não pôde ser localizada depois da edição da legenda.')
    width,height=float(page.mediabox.width),float(page.mediabox.height)
    x,y,w,h=block['x'],block['y'],block['w']*scale,block['h']*scale
    def overlaps(a,b):return a[0]<b[0]+b[2]-.5 and a[0]+a[2]>b[0]+.5 and a[1]<b[1]+b[3]-.5 and a[1]+a[3]>b[1]+.5
    obstacles=[]
    with pdfplumber.open(source) as document:
        p=document.pages[index]
        for item in p.chars+p.images+p.rects+p.curves:
            box=(float(item['x0']),float(item['top']),float(item['x1']-item['x0']),float(item['bottom']-item['top']))
            own=item.get('object_type')=='image' and all(abs(a-b)<2 for a,b in zip(box,(block['x'],block['y'],block['w'],block['h'])))
            old_caption=len(old_box)==4 and box[0]>=old_box[0]-.5 and box[1]>=old_box[1]-.5 and box[0]+box[2]<=old_box[0]+old_box[2]+.5 and box[1]+box[3]<=old_box[1]+old_box[3]+.5
            background=box[0]<=x and box[1]<=y and box[0]+box[2]>=x+w and box[1]+box[3]>=y+h and item.get('object_type') in ('rect','curve')
            if not own and not old_caption and not background:obstacles.append(box)
    def free(box):return box[0]>=0 and box[1]>=0 and box[0]+box[2]<=width and box[1]+box[3]<=height and not any(overlaps(box,o) for o in obstacles)
    if scale>1 and not free((x,y,w,h)):raise MaterialError('A imagem ampliada cobriria outro conteúdo ou sairia da página. Escolha uma ampliação menor.')
    caption_box=None;lines=[]
    if caption.strip():
        def wrap(available):
            result=[]
            for paragraph in caption.strip().splitlines():
                current=''
                for word in paragraph.split():
                    if stringWidth(word,'Helvetica',20)>available:return None
                    test=(current+' '+word).strip()
                    if current and stringWidth(test,'Helvetica',20)>available:result.append(current);current=word
                    else:current=test
                result.append(current)
            return result
        for left,top,cw,above in [(x,y+h+6,w,False),(x+w+8,y,width-x-w-20,False),(12,y,x-20,False),(x,y-6,w,True)]:
            if cw<80:continue
            wrapped=wrap(cw-8)
            if wrapped is None:continue
            ch=len(wrapped)*25+8;top=top-ch if above else top
            if free((left,top,cw,ch)) and not overlaps((left,top,cw,ch),(x,y,w,h)):
                caption_box=(left,top,cw,ch);lines=wrapped;break
        if caption_box is None:raise MaterialError('Não há espaço fora da imagem para a legenda. Desmarque “Mostrar a descrição como legenda” para salvar só a descrição para o leitor de tela. Para incluir a legenda visível, ajuste o espaço no editor original.')
    mcid=None
    if figure is None and alt is not None:
        try:figure,mcid=add_figure(writer,page,stream,alt.strip())
        except (KeyError,ValueError,TypeError):raise MaterialError('Não foi possível associar a descrição à imagem deste PDF.')
    if figure is not None and alt is not None:figure[NameObject('/Alt')]=TextStringObject(alt.strip())
    pos,matrix=target;args,op=stream.operations[pos]
    replacement=[([],b'q'),([FloatObject(scale),NumberObject(0),NumberObject(0),FloatObject(scale),NumberObject(0),FloatObject(1-scale)],b'cm')]
    if mcid is not None:replacement.append(([NameObject('/Figure'),DictionaryObject({NameObject('/MCID'):NumberObject(mcid)})],b'BDC'))
    replacement.append((args,op))
    if mcid is not None:replacement.append(([],b'EMC'))
    replacement.append(([],b'Q'));stream.operations[pos:pos+1]=replacement
    page.replace_contents(stream)
    if figure is not None:
        for key in ('/EntrelinhasCaption','/EntrelinhasCaptionBox','/EntrelinhasCaptionKey'):figure.pop(key,None)
    if caption_box:
        left,top,cw,ch=caption_box;buffer=BytesIO();overlay=canvas.Canvas(buffer,pagesize=(width,height))
        caption_key=caption_key or uuid.uuid4().hex
        overlay._code.append('/Artifact <</EntrelinhasCaption ('+caption_key+')>> BDC')
        overlay.setFillColorRGB(1,1,1);overlay.rect(left,height-top-ch,cw,ch,fill=1,stroke=0)
        overlay.setFillColorRGB(0,0,0);overlay.setFont('Helvetica',20)
        for n,line in enumerate(lines):overlay.drawString(left+4,height-top-23-n*25,line)
        overlay._code.append('EMC');overlay.save();page.merge_page(PdfReader(BytesIO(buffer.getvalue())).pages[0])
        if figure is not None:
            figure[NameObject('/EntrelinhasCaption')]=TextStringObject(caption.strip())
            figure[NameObject('/EntrelinhasCaptionKey')]=TextStringObject(caption_key)
            figure[NameObject('/EntrelinhasCaptionBox')]=ArrayObject([FloatObject(v) for v in caption_box])
    writer.write(destination)
