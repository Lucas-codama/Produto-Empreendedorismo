"""Recolor identified top-level PDF text objects without painting over the page."""
import re
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
    import math
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
                for obj in objects:
                    if not pdfium.raw.FPDFTextObj_SetFontSize(obj,size):raise MaterialError('Não foi possível alterar a fonte deste objeto.')
                page.gen_content();document.save(str(destination))
            finally:page.close()
        finally:document.close()


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
