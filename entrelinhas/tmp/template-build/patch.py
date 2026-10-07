import sys,zipfile,re
from pathlib import Path
from lxml import etree as E
path=Path(sys.argv[1]);tmp=path.with_suffix('.patched')
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
with zipfile.ZipFile(path) as source,zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as out:
    for item in source.infolist():
        data=source.read(item.filename)
        if re.fullmatch(r'ppt/slides/slide\d+\.xml',item.filename):
            root=E.fromstring(data)
            for index,shape in enumerate(root.findall('.//p:sp',ns)):
                nv=shape.find('p:nvSpPr/p:nvPr',ns)
                if nv is not None:
                    ph=E.SubElement(nv,'{'+ns['p']+'}ph');ph.set('type','title' if index==0 else 'body');ph.set('idx',str(index))
            for prop in root.xpath('//a:rPr | //a:defRPr | //a:endParaRPr',namespaces=ns):prop.set('lang','pt-BR')
            for para in root.findall('.//a:p',ns):
                prop=para.find('a:pPr',ns)
                if prop is None:prop=E.Element('{'+ns['a']+'}pPr');para.insert(0,prop)
                for old in list(prop):
                    if E.QName(old).localname.startswith('bu'):prop.remove(old)
                E.SubElement(prop,'{'+ns['a']+'}buNone')
            data=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
        out.writestr(item,data)
tmp.replace(path)
