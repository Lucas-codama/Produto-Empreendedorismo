"""Read and patch Word stories without dropping headers, notes or hyperlinks."""
import posixpath
import re
import zipfile
from io import BytesIO
from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from lxml import etree

PATTERN = r'word/(?:document|header\d+|footer\d+|footnotes|endnotes)\.xml'


def stories(path):
    doc=Document(path)
    with zipfile.ZipFile(path) as z:
        for name in sorted((n for n in z.namelist() if re.fullmatch(PATTERN,n)),key=lambda n:(n!='word/document.xml',n)):
            root=parse_xml(z.read(name))
            label='Corpo' if name=='word/document.xml' else 'Cabeçalho' if '/header' in name else 'Rodapé' if '/footer' in name else 'Nota de rodapé' if '/footnotes' in name else 'Nota de fim'
            relname=posixpath.join(posixpath.dirname(name),'_rels',posixpath.basename(name)+'.rels')
            rels={}
            if relname in z.namelist():
                for r in etree.fromstring(z.read(relname)):
                    if r.get('TargetMode')!='External':
                        target=r.get('Target','')
                        rels[r.get('Id')]=target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(name),target))
            yield doc,name,label,root,rels,z


def paragraphs(root):
    return list(root.iter(qn('w:p')))


def runs(paragraph):
    result=[]
    for node in paragraph._p.iter(qn('w:r')):
        owner=node.getparent()
        while owner is not None and owner.tag!=qn('w:p'):owner=owner.getparent()
        if owner is paragraph._p:result.append(Run(node,paragraph))
    return result


def patch(source,destination,ref,action,value,targets,default_background,contrast):
    part=ref.get('part','word/document.xml')
    with zipfile.ZipFile(source) as z:
        root=parse_xml(z.read(part))
        if action=='alt':
            drawings=list(root.iter(qn('w:drawing')))
            props=drawings[ref['image']].xpath('.//wp:docPr')
            props[0].set('descr',value)
        else:
            doc=Document(source);p=Paragraph(paragraphs(root)[ref['paragraph']],doc)
            for index,run in enumerate(runs(p)):
                if action=='font':
                    from docx.shared import Pt
                    run.font.size=Pt(value)
                elif action=='contrast':
                    from docx.shared import RGBColor
                    target=next((t for t in targets if t['source'].get('run')==index),None)
                    if targets and target is None:continue
                    bg=(target or {}).get('background') or default_background
                    if not bg:raise ValueError('Fundo não determinado para correção.')
                    color=max(['#000000','#FFFFFF'],key=lambda c:contrast(c,bg))
                    run.font.color.rgb=RGBColor.from_string(color[1:])
        content=etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
        with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as out:
            for item in z.infolist():out.writestr(item,content if item.filename==part else z.read(item.filename))
