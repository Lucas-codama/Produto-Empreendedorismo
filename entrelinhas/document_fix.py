"""Small native Office structure corrections exposed beside findings."""
import zipfile
from lxml import etree


def table_headers(source,destination):
    ns='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    with zipfile.ZipFile(source) as package,zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as output:
        for item in package.infolist():
            content=package.read(item.filename)
            if item.filename.startswith('word/') and item.filename.endswith('.xml'):
                root=etree.fromstring(content,parser=etree.XMLParser(resolve_entities=False,no_network=True))
                changed=False
                for table in root.iter('{'+ns+'}tbl'):
                    row=table.find('{'+ns+'}tr')
                    if row is None:continue
                    props=row.find('{'+ns+'}trPr')
                    if props is None:props=etree.Element('{'+ns+'}trPr');row.insert(0,props)
                    header=props.find('{'+ns+'}tblHeader')
                    if header is None:header=etree.SubElement(props,'{'+ns+'}tblHeader')
                    header.set('{'+ns+'}val','1');changed=True
                if changed:content=etree.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
            output.writestr(item,content)


def slide_title(source,destination,page,title):
    from analyzer import MaterialError
    from pptx import Presentation
    from pptx.util import Inches,Pt
    from pptx.dml.color import RGBColor
    from pptx.oxml.xmlchemy import OxmlElement
    if not isinstance(title,str) or not title.strip() or len(title)>200:raise MaterialError('Escreva um título com até 200 caracteres.')
    presentation=Presentation(source);slide=presentation.slides[page]
    shape=slide.shapes.title
    if shape is None:
        shape=slide.shapes.add_textbox(Inches(.4),Inches(.15),presentation.slide_width-Inches(.8),Inches(.6))
        nv=shape._element.find('{http://schemas.openxmlformats.org/presentationml/2006/main}nvSpPr')
        props=nv.find('{http://schemas.openxmlformats.org/presentationml/2006/main}nvPr')
        ph=OxmlElement('p:ph');ph.set('type','title');ph.set('idx','0');props.append(ph)
    shape.text=title.strip()
    for paragraph in shape.text_frame.paragraphs:
        for run in paragraph.runs:run.font.size=Pt(26);run.font.color.rgb=RGBColor(0,0,0)
    presentation.save(destination)
