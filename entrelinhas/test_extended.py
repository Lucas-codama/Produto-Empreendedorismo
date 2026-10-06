from pathlib import Path
from io import BytesIO
import hashlib
import json
import zipfile
import unittest
from unittest.mock import patch
from docx import Document
from docx.shared import Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image,ImageDraw,ImageFont
from pypdf import PdfReader,PdfWriter
from pypdf.generic import DictionaryObject,NameObject,ArrayObject,NumberObject,TextStringObject
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import analyzer,reading,vision_checks
import test_analyzer
CONTEXT=test_analyzer.CONTEXT


class ExtendedTests(unittest.TestCase):
    setUp=test_analyzer.AnalyzerTests.setUp
    tearDown=test_analyzer.AnalyzerTests.tearDown
    result=test_analyzer.AnalyzerTests.result
    # Reuse fixture lifecycle, not the parent test methods.
    def test_header_image_description_edit_is_preserved(self):
        path=self.folder/'header-image.docx';doc=Document();doc.add_paragraph('Corpo preservado.')
        buffer=BytesIO();Image.new('RGB',(100,80),'blue').save(buffer,format='PNG');buffer.seek(0)
        doc.sections[0].header.paragraphs[0].add_run().add_picture(buffer);doc.save(path)
        issue=next(i for i in self.result(path)['issues'] if i['rule']=='alt_missing')
        self.assertIn('header',issue['source']['part'])
        dest=self.folder/'header-image-fixed.docx';analyzer.apply_edit(path,dest,issue,'Imagem azul usada como exemplo.')
        self.assertFalse(any(i['rule']=='alt_missing' for i in self.result(dest)['issues']))
        self.assertEqual(Document(dest).paragraphs[0].text,'Corpo preservado.')

    def test_footnotes_are_analyzed_and_edited(self):
        base=self.folder/'base.docx';doc=Document();doc.add_paragraph('Corpo preservado.');doc.save(base)
        source=self.folder/'notes.docx'
        notes=b'<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:footnote w:id="1"><w:p><w:r><w:rPr><w:color w:val="FFFFFF"/><w:sz w:val="16"/></w:rPr><w:t>Nota importante</w:t></w:r></w:p></w:footnote></w:footnotes>'
        with zipfile.ZipFile(base) as z,zipfile.ZipFile(source,'w') as out:
            for info in z.infolist():out.writestr(info,z.read(info.filename))
            out.writestr('word/footnotes.xml',notes)
        issue=next(i for i in self.result(source)['issues'] if i['rule']=='contrast' and i['source']['part']=='word/footnotes.xml')
        dest=self.folder/'notes-fixed.docx';analyzer.apply_edit(source,dest,issue)
        self.assertFalse(any(i['rule']=='contrast' and i['source'].get('part')=='word/footnotes.xml' for i in self.result(dest)['issues']))
        with zipfile.ZipFile(source) as z:self.assertEqual(z.read('word/footnotes.xml'),notes)

    def test_textbox_text_and_hyperlink_can_be_edited(self):
        path=self.folder/'boxes.docx';doc=Document();p=doc.add_paragraph('Corpo preservado.')
        outer=p.add_run();pict=OxmlElement('w:pict')
        from lxml import etree
        shape=etree.SubElement(pict,'{urn:schemas-microsoft-com:vml}shape');box=etree.SubElement(shape,'{urn:schemas-microsoft-com:vml}textbox')
        content=OxmlElement('w:txbxContent');inner=OxmlElement('w:p');link=OxmlElement('w:hyperlink');run=OxmlElement('w:r');prop=OxmlElement('w:rPr');color=OxmlElement('w:color');color.set(qn('w:val'),'FFFFFF');prop.append(color);run.append(prop);text=OxmlElement('w:t');text.text='Texto importante na caixa';run.append(text);link.append(run);inner.append(link);content.append(inner);box.append(content);outer._r.append(pict);doc.save(path)
        result=self.result(path);issue=next(i for i in result['issues'] if i['rule']=='contrast' and 'caixa' in i['text'])
        dest=self.folder/'box-fixed.docx';analyzer.apply_edit(path,dest,issue)
        self.assertFalse(any(i['rule']=='contrast' for i in self.result(dest)['issues']))
        self.assertEqual(Document(dest).paragraphs[0].text,'Corpo preservado.')

    def test_cmyk_low_contrast_and_original_preserved(self):
        p=self.folder/'cmyk.pdf';c=canvas.Canvas(str(p));c.setFillColorCMYK(0,0,0,.2);c.drawString(40,740,'Texto CMYK');c.save()
        digest=hashlib.sha256(p.read_bytes()).hexdigest();result=self.result(p)
        self.assertTrue(any(i['rule']=='contrast' and 'renderizada' in i['evidence'] for i in result['issues']))
        self.assertEqual(digest,hashlib.sha256(p.read_bytes()).hexdigest())

    def test_cmyk_black_text_is_not_falsely_flagged(self):
        p=self.folder/'black-cmyk.pdf';c=canvas.Canvas(str(p));c.setFillColorCMYK(0,0,0,1);c.drawString(40,740,'Texto preto CMYK');c.save()
        result=self.result(p)
        self.assertGreater(result['measured']['contrast'],0)
        self.assertFalse(any(i['rule']=='contrast' for i in result['issues']))

    def test_empty_tags_are_reported_as_objective_problem(self):
        p=self.folder/'tags.pdf';c=canvas.Canvas(str(p));c.drawString(40,740,'Conteudo');c.save()
        writer=PdfWriter();writer.clone_document_from_reader(PdfReader(p));writer.root_object[NameObject('/StructTreeRoot')]=DictionaryObject({NameObject('/Type'):NameObject('/StructTreeRoot')});writer.write(p)
        issue=next(i for i in self.result(p)['issues'] if i['rule']=='pdf_tags_empty')
        self.assertEqual(issue['severity'],'attention')

    def test_pdf_table_and_heading_structure_are_inspected(self):
        p=self.folder/'tag-tree.pdf';c=canvas.Canvas(str(p));c.drawString(40,740,'Conteudo');c.save()
        writer=PdfWriter();writer.clone_document_from_reader(PdfReader(p))
        children=ArrayObject([DictionaryObject({NameObject('/S'):NameObject('/H3')}),DictionaryObject({NameObject('/S'):NameObject('/Table'),NameObject('/K'):ArrayObject([DictionaryObject({NameObject('/S'):NameObject('/TD')})])}),DictionaryObject({NameObject('/S'):NameObject('/Figure')})])
        writer.root_object[NameObject('/StructTreeRoot')]=DictionaryObject({NameObject('/Type'):NameObject('/StructTreeRoot'),NameObject('/K'):children});writer.write(p)
        rules={i['rule'] for i in self.result(p)['issues']}
        self.assertTrue({'pdf_heading_skip','pdf_table_headers','pdf_figure_alt','pdf_text_untagged'}<=rules)

    def test_pdf_untagged_text_keeps_its_page_and_specific_guidance(self):
        p=self.folder/'page-scope.pdf';c=canvas.Canvas(str(p))
        for text in ['Primeira página','Segunda página']:
            c.drawString(40,740,text);c.showPage()
        c.save();writer=PdfWriter();writer.clone_document_from_reader(PdfReader(p))
        writer.root_object[NameObject('/StructTreeRoot')]=DictionaryObject({NameObject('/Type'):NameObject('/StructTreeRoot'),NameObject('/K'):ArrayObject([DictionaryObject({NameObject('/S'):NameObject('/H3')}),DictionaryObject({NameObject('/S'):NameObject('/Table')})])});writer.write(p)
        result=self.result(p)
        text_issues=[i for i in result['issues'] if i['rule']=='pdf_text_untagged']
        self.assertEqual([i['page'] for i in text_issues],[0,1])
        self.assertEqual([i['location'] for i in text_issues],['Página 1','Página 2'])
        heading=next(i for i in result['issues'] if i['rule']=='pdf_heading_skip')
        table=next(i for i in result['issues'] if i['rule']=='pdf_table_headers')
        self.assertIn('nível',heading['explanation']);self.assertIn('cabeçalho',table['explanation'])
        self.assertNotEqual(heading['suggestion'],table['suggestion'])

    def test_raster_pixel_measurement_white_on_yellow(self):
        image=Image.new('RGB',(400,120),'yellow');draw=ImageDraw.Draw(image);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',44);box=draw.textbbox((15,25),'Texto',font=font);draw.text((15,25),'Texto',font=font,fill='white')
        colors=vision_checks.raster_colors(image,(box[0],box[1],box[2]-box[0],box[3]-box[1]))
        self.assertIsNotNone(colors);self.assertLess(analyzer.contrast(*colors),1.2)

    def test_pdf_underlines_and_borders_are_not_text_background(self):
        p=self.folder/'underlined.pdf';c=canvas.Canvas(str(p));c.setFont('Helvetica',12);c.setFillColorRGB(.02,.39,.76)
        c.drawString(40,740,'Texto de um link');c.setStrokeColorRGB(.02,.39,.76);c.line(40,737,135,737)
        c.setFillAlpha(.999);c.setFillColorRGB(0,0,0);c.drawString(40,700,'Texto em tabela');c.setStrokeColorRGB(0,0,0);c.rect(35,697,160,20,stroke=1,fill=0);c.save()
        result=self.result(p)
        self.assertFalse(any(i['rule']=='contrast' for i in result['issues']))
        self.assertGreater(result['measured']['contrast'],0)

    def test_ocr_failure_does_not_claim_checked_text(self):
        p=self.folder/'text.png';Image.new('RGB',(300,100),'white').save(p)
        with patch.object(vision_checks,'executable',return_value=None):result=self.result(p)
        self.assertTrue(any(i['rule']=='ocr_unavailable' for i in result['issues']))
        self.assertEqual(result['measured']['contrast'],0)

    def test_local_ocr_real_text_and_contrast_when_installed(self):
        if not vision_checks.executable():self.skipTest('Instalação do OCR local aguardando autorização.')
        p=self.folder/'ocr.png';image=Image.new('RGB',(1000,240),'yellow');draw=ImageDraw.Draw(image);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',64);draw.text((40,70),'Atividade de Geografia',font=font,fill='white');image.save(p)
        result=self.result(p);text=' '.join(b.get('text','') for pg in result['pages'] for b in pg['blocks'])
        self.assertIn('Geografia',text);self.assertGreater(result['measured']['contrast'],0)
        self.assertTrue(any(i['rule']=='contrast' for i in result['issues']))

    def test_reading_document_escapes_text_and_preserves_order(self):
        job={'filename':'Atividade','analysis':{'pages':[{'label':'Página 1','blocks':[{'id':'b1','type':'text','text':'Primeiro'},{'id':'b2','type':'text','text':'Segundo'}]}]}}
        value=reading.initial(job);value['items'].reverse();value['items'][0]['text']='<script>alert(1)</script>'
        for item in value['items']:item['confirmed']=True
        job['reading']=reading.validate(job,value);html=reading.render(job).decode()
        self.assertTrue(job['reading']['reviewed']);self.assertNotIn('<script>',html);self.assertLess(html.index('&lt;script&gt;'),html.index('Primeiro'))
        value['items'][1]['id']=value['items'][0]['id']
        with self.assertRaises(analyzer.MaterialError):reading.validate(job,value)


class ReadingServerTests(unittest.TestCase):
    setUpClass=classmethod(test_analyzer.ServerTests.setUpClass.__func__)
    tearDownClass=classmethod(test_analyzer.ServerTests.tearDownClass.__func__)
    request=test_analyzer.ServerTests.request
    def test_reading_endpoint_round_trip_preserves_source(self):
        data,_=self.request('/api/demo',{});job=json.loads(data)
        import server
        before=server.file_path(job).read_bytes();value=reading.initial(job)
        for item in value['items']:
            if item['role']=='figure':item['text']='Gráfico com valores das regiões A, B e C.'
            item['confirmed']=True
        updated=json.loads(self.request('/api/reading',{'id':job['id'],'reading':value})[0])
        self.assertTrue(updated['reading']['reviewed']);self.assertEqual(before,server.file_path(updated).read_bytes())
        html,_=self.request('/api/job/'+job['id']+'/reading')
        self.assertIn(b'lang="pt-BR"',html);self.assertIn(b'<figure>',html)


if __name__=='__main__':unittest.main(verbosity=2)
