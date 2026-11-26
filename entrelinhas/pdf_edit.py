"""Recolor identified top-level PDF text objects without painting over the page."""
import re
import ctypes
import math
import pypdfium2 as pdfium
from vision_checks import PDF_LOCK


def targets(page, box):
    if page.get_rotation()!=0:
        return []
    x0,top,x1,bottom=box
    height=page.get_height()
    result=[]
    # Nested form coordinates need separate transforms and are not edited here.
    for obj in page.get_objects(filter=[pdfium.raw.FPDF_PAGEOBJ_TEXT],max_depth=0):
        left,down,right,up=obj.get_bounds()
        y0,y1=height-up,height-down
        area=max(0,right-left)*max(0,y1-y0)
        overlap=max(0,min(right,x1+2)-max(left,x0-2))*max(0,min(y1,bottom+2)-max(y0,top-2))
        if area>0 and overlap/area>=.95:
            result.append(obj)
    return result


def can_edit(page, block):
    return not block.get('ocr') and bool(targets(page,[block['x'],block['y'],block['x']+block['w'],block['y']+block['h']]))


def recolor(source,destination,issue,color):
    from analyzer import MaterialError
    if not isinstance(color,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',color):
        raise MaterialError('Escolha uma cor válida para o texto.')
    if not issue.get('pdf_box'):
        raise MaterialError('Não foi possível localizar o texto editável deste PDF.')
    rgb=[int(color[i:i+2],16) for i in (1,3,5)]
    with PDF_LOCK:
        document=pdfium.PdfDocument(str(source))
        try:
            page=document[issue['page']]
            try:
                objects=targets(page,issue['pdf_box'])
                if not objects:raise MaterialError('O trecho não pode ser editado com segurança nesta versão do PDF. Nenhum arquivo foi alterado.')
                for obj in objects:
                    if not pdfium.raw.FPDFPageObj_SetFillColor(obj,*rgb,255):
                        raise MaterialError('Não foi possível alterar a cor deste texto. O original foi preservado.')
                    if not pdfium.raw.FPDFPageObj_SetStrokeColor(obj,*rgb,255):
                        raise MaterialError('Não foi possível alterar o contorno deste texto. O original foi preservado.')
                page.gen_content()
                document.save(str(destination))
            finally:page.close()
        finally:document.close()


def resize(source,destination,issue,size):
    from analyzer import MaterialError
    try:size=float(size)
    except (TypeError,ValueError):raise MaterialError('Informe uma fonte entre 6 e 96 pt.')
    if not math.isfinite(size) or not 6<=size<=96:raise MaterialError('Informe uma fonte entre 6 e 96 pt.')
    with PDF_LOCK:
        document=pdfium.PdfDocument(str(source))
        try:
            page=document[issue['page']]
            try:
                objects=targets(page,issue['pdf_box'])
                if not objects:raise MaterialError('Não foi possível isolar o trecho. Faça este ajuste no editor original.')
                resize_line(page,objects,issue,size)
                page.gen_content();document.save(str(destination))
            finally:page.close()
        finally:document.close()


def resize_line(page,objects,issue,size):
    """Resize in page points and reflow existing text objects without losing their tags."""
    from analyzer import MaterialError
    height=page.get_height();left,top,right,bottom=issue['pdf_box']
    selected={ctypes.cast(o.raw,ctypes.c_void_p).value for o in objects}
    others=[(o,o.get_bounds()) for o in page.get_objects(max_depth=0)
        if ctypes.cast(o.raw,ctypes.c_void_p).value not in selected]
    limit=page.get_width()-min(max(left,18),36)
    records=[]
    textpage=page.get_textpage()
    try:
        for obj,(x0,y0,x1,y1) in others:
            if x0>=right-1 and height-y1<bottom and height-y0>top:
                if obj.type==pdfium.raw.FPDF_PAGEOBJ_TEXT:
                    length=pdfium.raw.FPDFTextObj_GetText(obj,textpage,None,0)
                    if length<2:continue
                    buffer=ctypes.create_string_buffer(length)
                    pdfium.raw.FPDFTextObj_GetText(obj,textpage,ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ushort)),length)
                    if not buffer.raw.decode('utf-16-le').rstrip('\0').strip():continue
                limit=min(limit,x0-8)
        for obj in objects:
            matrix=obj.get_matrix();scale=math.hypot(matrix.c,matrix.d)
            if scale<.001 or abs(matrix.b)>.001 or abs(matrix.c)>.001 or matrix.a<=0 or matrix.d<=0:
                raise MaterialError('Este texto tem uma transformação que exige ajuste no editor original.')
            current=ctypes.c_float()
            if not pdfium.raw.FPDFTextObj_GetFontSize(obj,ctypes.byref(current)):
                raise MaterialError('Não foi possível medir a fonte deste trecho.')
            length=pdfium.raw.FPDFTextObj_GetText(obj,textpage,None,0)
            if length<2:raise MaterialError('Não foi possível recuperar o texto deste trecho.')
            buffer=ctypes.create_string_buffer(length)
            pdfium.raw.FPDFTextObj_GetText(obj,textpage,ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ushort)),length)
            text=buffer.raw.decode('utf-16-le').rstrip('\0')
            records.append({'object':obj,'matrix':matrix,'text':text,'buffer':buffer,'size':current.value*scale})
    finally:textpage.close()
    records.sort(key=lambda r:r['matrix'].e)
    original=''.join(issue.get('text','').split())
    if not original or ''.join(''.join(r['text'].split()) for r in records)!=original:
        raise MaterialError('Não foi possível reorganizar este trecho com segurança. Ajuste-o no editor original.')
    boundaries=set();length=0
    for word in issue['text'].split():length+=len(word);boundaries.add(length)
    groups=[];group=[];length=0
    for record in records:
        obj=record['object'];matrix=record['matrix']
        if not pdfium.raw.FPDFTextObj_SetFontSize(obj,size/math.hypot(matrix.c,matrix.d)):
            raise MaterialError('Não foi possível alterar a fonte deste objeto.')
        # PDFium caches bounds; resetting the unchanged text recalculates glyph positions.
        if not pdfium.raw.FPDFText_SetText(obj,ctypes.cast(record['buffer'],ctypes.POINTER(ctypes.c_ushort))):
            raise MaterialError('Não foi possível atualizar a posição do texto.')
        record['advance']=max(.05,obj.get_bounds()[2]-matrix.e)
        group.append(record);length+=len(''.join(record['text'].split()))
        if length in boundaries:groups.append(group);group=[]
    if group:groups.append(group)
    cursor=left;line=0;placements=[];spacing=size*.28;fragment_gap=size*.035
    for group in groups:
        width=sum(r['advance'] for r in group)+fragment_gap*max(0,len(group)-1)
        if width>limit-left+.05:
            raise MaterialError('A fonte escolhida não cabe neste trecho sem reorganizar o conteúdo. Faça esse ajuste no editor original.')
        if cursor>left and cursor+width>limit:
            line+=1;cursor=left
        for record in group:
            placements.append((record,cursor,line));cursor+=record['advance']+fragment_gap
        cursor+=spacing-fragment_gap
    new_height=size+line*size*1.25
    shift=max(0,new_height-(bottom-top))
    downstream=[o for o,b in others if height-b[3]>=bottom-.2 and b[2]>left and b[0]<limit]
    if top+new_height>height-18 or any(height-o.get_bounds()[1]+shift>height-18 for o in downstream):
        raise MaterialError('A fonte escolhida ultrapassaria o fim da página. Reorganize o material no editor original.')
    first=records[0]
    ascent=max(.5,min(1.5,(height-top-first['matrix'].f)/first['size']))
    baseline=height-top-size*ascent
    for record,x,row in placements:
        matrix=record['matrix']
        updated=pdfium.raw.FS_MATRIX(matrix.a,matrix.b,matrix.c,matrix.d,x,baseline-row*size*1.25)
        if not pdfium.raw.FPDFPageObj_SetMatrix(record['object'],ctypes.byref(updated)):
            raise MaterialError('Não foi possível posicionar o texto ajustado.')
    for obj in downstream:obj.transform(pdfium.PdfMatrix(e=0,f=-shift))


def structure_edit(source,destination,issue,value):
    from analyzer import MaterialError
    from pypdf import PdfWriter
    from pypdf.generic import NameObject,TextStringObject,DictionaryObject
    writer=PdfWriter(clone_from=str(source))
    if issue['action']=='language':
        if not isinstance(value,str) or not re.fullmatch(r'[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8})*',value) or len(value)>35:
            raise MaterialError('Informe um idioma como pt-BR, en-US ou es-ES.')
        writer.root_object[NameObject('/Lang')]=TextStringObject(value)
    else:
        node=writer.root_object.get('/StructTreeRoot')
        if node is None:raise MaterialError('A estrutura do PDF não foi localizada. Faça este ajuste no editor original.')
        node=node.get_object()
        for part in issue.get('source',{}).get('pdf_path',[]):
            try:node=node[part if isinstance(part,int) else '/'+part].get_object()
            except (KeyError,IndexError,TypeError,AttributeError):raise MaterialError('O elemento de estrutura não foi localizado.')
        if issue['action']=='alt':node[NameObject('/Alt')]=TextStringObject(value)
        elif issue['action']=='heading':
            if value not in ('H1','H2','H3','H4','H5','H6'):raise MaterialError('Escolha um nível de título válido.')
            node[NameObject('/S')]=NameObject('/'+value)
        elif issue['action']=='table_headers':
            visited=set()
            def first_row(item):
                item=item.get_object() if hasattr(item,'get_object') else item
                if isinstance(item,list):
                    for entry in item:
                        found=first_row(entry)
                        if found is not None:return found
                elif isinstance(item,dict) and id(item) not in visited:
                    visited.add(id(item))
                    if item.get('/S')=='/TR':return item
                    return first_row(item.get('/K'))
                return None
            row=first_row(node)
            if row is None:raise MaterialError('Não foi encontrada uma linha de tabela. Organize a tabela no editor original.')
            count=0;visited.clear()
            def headers(item):
                nonlocal count
                item=item.get_object() if hasattr(item,'get_object') else item
                if isinstance(item,list):
                    for entry in item:headers(entry)
                elif isinstance(item,dict) and id(item) not in visited:
                    visited.add(id(item))
                    if item.get('/S')=='/TD':
                        item[NameObject('/S')]=NameObject('/TH')
                        item[NameObject('/A')]=DictionaryObject({NameObject('/O'):NameObject('/Table'),NameObject('/Scope'):NameObject('/Column')})
                        count+=1
                    headers(item.get('/K'))
            headers(row)
            if not count:raise MaterialError('Não foram encontradas células para marcar como cabeçalho.')
        else:raise MaterialError('Operação de estrutura inválida.')
    writer.write(destination)
