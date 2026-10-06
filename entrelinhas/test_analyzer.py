import base64
from io import BytesIO
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from docx import Document
from docx.shared import Pt, RGBColor
from PIL import Image
from pptx import Presentation
from reportlab.pdfgen import canvas

import analyzer
import server

CONTEXT = {'discipline':'Geografia','activity':'Prova','needs':'Fonte ampliada e descrição de imagens',
           'technology':'Leitor de tela e ampliação','min_font':20}
TEST_ROOT=Path(__file__).resolve().parent/'.runtime'/'test-temp'

def temporary_workspace():
    TEST_ROOT.mkdir(parents=True,exist_ok=True)
    return tempfile.TemporaryDirectory(dir=TEST_ROOT)

def cleanup_workspace(tmp):
    assert Path(tmp.name).resolve().is_relative_to(TEST_ROOT.resolve())
    tmp.cleanup()


class AnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=temporary_workspace()
        self.folder=Path(self.tmp.name)
    def tearDown(self):
        cleanup_workspace(self.tmp)
    def result(self,path,context=None):
        return analyzer.decorate_actions(analyzer.analyze(path,dict(context or CONTEXT)))
    def test_contrast_math_and_unrounded_threshold(self):
        self.assertEqual(analyzer.contrast('#000000','#FFFFFF'),21)
        self.assertAlmostEqual(analyzer.contrast('#CCCCCC','#FFFFFF'),1.60592856)
        self.assertEqual(analyzer.threshold(18,False),3)
        self.assertEqual(analyzer.threshold(14,True),3)
        self.assertEqual(analyzer.threshold(14,False),4.5)
    def test_context_is_required_not_inferred(self):
        with self.assertRaises(analyzer.MaterialError): analyzer.validate_context({'discipline':'Geografia'})
        with self.assertRaises(analyzer.MaterialError): analyzer.validate_context(dict(CONTEXT,min_font=0))
    def test_demo_checks_actual_document_and_patch_font(self):
        source=self.folder/'test.pptx'; analyzer.demo_pptx(source)
        result=self.result(source)
        for code in ['font_size','contrast','alt_missing']:
            self.assertTrue(any(i['rule']==code for i in result['issues']),code)
        issue=next(i for i in result['issues'] if i['rule']=='font_size')
        dest=self.folder/'edited.pptx'; analyzer.apply_edit(source,dest,issue,20)
        after=self.result(dest)
        self.assertFalse(any(i['rule']=='font_size' for i in after['issues']))
        self.assertTrue(any(i['rule']=='font_size' for i in self.result(source)['issues']))
        prs=Presentation(dest)
        self.assertEqual(prs.slides[0].shapes[issue['source']['shape']].text_frame.paragraphs[0].runs[0].font.size.pt,20)
    def test_contrast_fix_uses_identified_dark_background(self):
        source=self.folder/'dark.pptx';analyzer.demo_pptx(source)
        prs=Presentation(source)
        from pptx.dml.color import RGBColor as PptColor
        prs.slides[0].background.fill.fore_color.rgb=PptColor(0,0,0)
        for shape in prs.slides[0].shapes:
            if shape.has_text_frame:
                for p in shape.text_frame.paragraphs:
                    for r in p.runs:r.font.color.rgb=PptColor(30,30,30)
        prs.save(source)
        issue=next(i for i in self.result(source)['issues'] if i['rule']=='contrast')
        self.assertEqual(issue['background'],'#000000')
        dest=self.folder/'fixed.pptx';analyzer.apply_edit(source,dest,issue)
        p=Presentation(dest).slides[0].shapes[issue['source']['shape']].text_frame.paragraphs[0]
        self.assertEqual(str(p.runs[0].font.color.rgb),'FFFFFF')
    def test_image_description_is_real_metadata_not_auto_validation(self):
        source=self.folder/'source.pptx'; analyzer.demo_pptx(source)
        issue=next(i for i in self.result(source)['issues'] if i['rule']=='alt_missing')
        dest=self.folder/'described.pptx';analyzer.apply_edit(source,dest,issue,'Três barras identificadas pelas regiões A, B e C.')
        result=self.result(dest)
        self.assertFalse(any(i['rule']=='alt_missing' for i in result['issues']))
        self.assertTrue(any(i['rule']=='alt_quality' and i['severity']=='review' for i in result['issues']))
    def test_docx_runs_tables_images_and_preservation(self):
        source=self.folder/'text.docx'; doc=Document()
        r=doc.add_paragraph('Atividade com fonte pequena.').runs[0];r.font.size=Pt(10);r.font.color.rgb=RGBColor(180,180,180)
        doc.add_table(rows=1,cols=1).cell(0,0).text='Cabeçalho'
        img=BytesIO();Image.new('RGB',(100,100),'green').save(img,format='PNG');img.seek(0);doc.add_picture(img)
        doc.save(source)
        result=self.result(source)
        rules={i['rule'] for i in result['issues']}
        self.assertTrue({'font_size','contrast','alt_missing','table_review'}<=rules)
        font=next(i for i in result['issues'] if i['rule']=='font_size' and i['source']['paragraph']==0)
        dest=self.folder/'corrected.docx';analyzer.apply_edit(source,dest,font,20)
        self.assertEqual(Document(dest).paragraphs[0].runs[0].font.size.pt,20)
        self.assertEqual(len(Document(dest).inline_shapes),1)
        alt=next(i for i in self.result(dest)['issues'] if i['rule']=='alt_missing')
        dest2=self.folder/'desc.docx';analyzer.apply_edit(dest,dest2,alt,'Imagem de exemplo para teste.')
        self.assertFalse(any(i['rule']=='alt_missing' for i in self.result(dest2)['issues']))
    def test_no_universal_font_minimum(self):
        source=self.folder/'test.pptx';analyzer.demo_pptx(source)
        result=self.result(source,dict(CONTEXT,min_font=None))
        self.assertFalse(any(i['rule']=='font_size' for i in result['issues']))
        self.assertEqual(result['checks'][1]['state'],'partial')
    def test_docx_background_is_not_assumed_white(self):
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        source=self.folder/'dark.docx';doc=Document()
        background=OxmlElement('w:background');background.set(qn('w:color'),'000000');doc.element.insert(0,background)
        run=doc.add_paragraph('Texto em fundo escuro.').runs[0];run.font.size=Pt(20);run.font.color.rgb=RGBColor(30,30,30)
        doc.save(source)
        issue=next(i for i in self.result(source)['issues'] if i['rule']=='contrast')
        self.assertEqual(issue['background'],'#000000')
        dest=self.folder/'light-text.docx';analyzer.apply_edit(source,dest,issue)
        self.assertEqual(str(Document(dest).paragraphs[0].runs[0].font.color.rgb),'FFFFFF')
    def test_character_style_is_resolved_before_paragraph_default(self):
        from docx.enum.style import WD_STYLE_TYPE
        source=self.folder/'character-style.docx';doc=Document()
        doc.styles['Normal'].font.size=Pt(10)
        style=doc.styles.add_style('TextoAmpliado',WD_STYLE_TYPE.CHARACTER);style.font.size=Pt(24)
        run=doc.add_paragraph('Texto ampliado pelo estilo de caractere.').runs[0];run.style=style
        doc.save(source)
        self.assertFalse(any(i['rule']=='font_size' for i in self.result(source)['issues']))
    def test_pdf_extracts_real_positions_without_claiming_full_access(self):
        path=self.folder/'source.pdf';c=canvas.Canvas(str(path));c.setFont('Helvetica',10);c.setFillColorRGB(.7,.7,.7);c.drawString(40,740,'Texto de contraste baixo');c.save()
        result=self.result(path);rules={i['rule'] for i in result['issues']}
        self.assertTrue({'contrast','font_size','pdf_structure'}<=rules)
        self.assertTrue(all(i['action'] is None for i in result['issues']))
        self.assertGreater(result['pages'][0]['blocks'][0]['x'],0)
    def test_scans_are_not_falsely_marked_as_checked(self):
        path=self.folder/'scan.png';Image.new('RGB',(100,100),'white').save(path)
        result=self.result(path)
        self.assertEqual(result['measured']['contrast'],0)
        self.assertEqual(result['checks'][0]['state'],'partial')
        self.assertTrue(any(i['rule']=='image_review' for i in result['issues']))
    def test_corrupt_file_returns_explanation(self):
        path=self.folder/'fake.pdf';path.write_bytes(b'not a pdf')
        with self.assertRaises(analyzer.MaterialError):self.result(path)

    def test_white_text_on_yellow_pdf_is_detected(self):
        path=self.folder/'yellow.pdf';c=canvas.Canvas(str(path))
        c.setFillColorRGB(1,1,0);c.rect(0,0,600,900,fill=1,stroke=0)
        c.setFillColorRGB(1,1,1);c.setFont('Helvetica',11);c.drawString(40,740,'Texto branco sobre amarelo');c.save()
        r=self.result(path,dict(CONTEXT,min_font=None))
        issue=next(i for i in r['issues'] if i['rule']=='contrast')
        self.assertIn('#FFFFFF sobre #FFFF00: 1.07:1',issue['evidence'])
        self.assertEqual(r['measured']['unknown_contrast'],0)
        self.assertIsNone(issue['action'])

    def test_black_text_on_yellow_pdf_is_not_falsely_flagged(self):
        path=self.folder/'yellow-good.pdf';c=canvas.Canvas(str(path))
        c.setFillColorRGB(1,1,0);c.rect(0,0,600,900,fill=1,stroke=0)
        c.setFillColorRGB(0,0,0);c.drawString(40,740,'Texto preto');c.save()
        self.assertFalse(any(i['rule']=='contrast' for i in self.result(path)['issues']))

    def test_pdf_background_changes_split_text(self):
        path=self.folder/'split.pdf';c=canvas.Canvas(str(path))
        c.setFillColorRGB(1,1,0);c.rect(40,730,100,40,fill=1,stroke=0)
        c.setFillColorRGB(1,1,1);c.drawString(50,740,'Ruim')
        c.setFillColorRGB(0,0,0);c.drawString(160,740,'Bom');c.save()
        r=self.result(path);bad=next(i for i in r['issues'] if i['rule']=='contrast')
        self.assertEqual(bad['text'],'Ruim')
        self.assertEqual(bad['background'],'#FFFF00')

    def test_pdf_transparency_is_measured_as_composited_color(self):
        path=self.folder/'alpha.pdf';c=canvas.Canvas(str(path));c.setFillAlpha(.5)
        c.drawString(40,740,'Transparencia exige conferencia');c.save()
        r=self.result(path)
        issue=next(i for i in r['issues'] if i['rule']=='contrast')
        self.assertIn('renderizada',issue['evidence'])
        ratio=r['pages'][0]['blocks'][0]['runs'][0]['measured_contrast']
        self.assertGreater(ratio,3.5);self.assertLess(ratio,4.5)

    def test_docx_highlight_and_mixed_background_correction(self):
        from docx.enum.text import WD_COLOR_INDEX
        source=self.folder/'highlight.docx';doc=Document();p=doc.add_paragraph()
        first=p.add_run('Branco no amarelo');first.font.color.rgb=RGBColor(255,255,255);first.font.highlight_color=WD_COLOR_INDEX.YELLOW
        second=p.add_run(' Branco no preto');second.font.color.rgb=RGBColor(255,255,255);second.font.highlight_color=WD_COLOR_INDEX.BLACK
        doc.save(source);r=self.result(source)
        issue=next(i for i in r['issues'] if i['rule']=='contrast')
        self.assertEqual(issue['background'],'#FFFF00')
        dest=self.folder/'highlight-fixed.docx';analyzer.apply_edit(source,dest,issue)
        runs=Document(dest).paragraphs[0].runs
        self.assertEqual(str(runs[0].font.color.rgb),'000000')
        self.assertEqual(str(runs[1].font.color.rgb),'FFFFFF')
        self.assertFalse(any(i['rule']=='contrast' for i in self.result(dest)['issues']))

    def test_docx_cell_shading_is_checked(self):
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        source=self.folder/'cell.docx';doc=Document();cell=doc.add_table(rows=1,cols=1).cell(0,0)
        shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'FFFF00');cell._tc.get_or_add_tcPr().append(shade)
        run=cell.paragraphs[0].add_run('Texto');run.font.color.rgb=RGBColor(255,255,255);doc.save(source)
        self.assertTrue(any(i['rule']=='contrast' and i['background']=='#FFFF00' for i in self.result(source)['issues']))

    def test_docx_theme_color_is_resolved(self):
        from docx.enum.dml import MSO_THEME_COLOR_INDEX
        source=self.folder/'theme.docx';doc=Document();run=doc.add_paragraph('Tema claro').runs[0]
        run.font.color.theme_color=MSO_THEME_COLOR_INDEX.ACCENT_1;doc.save(source)
        r=self.result(source);run=r['pages'][0]['blocks'][0]['runs'][0]
        self.assertRegex(run['color'],r'^#[0-9A-F]{6}$')
        self.assertEqual(r['measured']['unknown_contrast'],0)

    def test_pptx_solid_shape_behind_text_is_resolved(self):
        from pptx.util import Inches,Pt as PptPt
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.dml.color import RGBColor as C
        source=self.folder/'rectangle.pptx';prs=Presentation();slide=prs.slides.add_slide(prs.slide_layouts[6])
        rect=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,0,0,Inches(10),Inches(7));rect.fill.solid();rect.fill.fore_color.rgb=C(255,255,0)
        box=slide.shapes.add_textbox(Inches(1),Inches(1),Inches(5),Inches(1));box.text='Branco sobre amarelo'
        run=box.text_frame.paragraphs[0].runs[0];run.font.color.rgb=C(255,255,255);run.font.size=PptPt(12);prs.save(source)
        r=self.result(source);issue=next(i for i in r['issues'] if i['rule']=='contrast')
        self.assertEqual(issue['background'],'#FFFF00')
        self.assertFalse(any(i['rule']=='contrast_unknown' for i in r['issues']))

    def test_pptx_grouped_text_can_be_checked_and_edited(self):
        from pptx.util import Inches,Pt as PptPt
        from pptx.dml.color import RGBColor as C
        source=self.folder/'group.pptx';prs=Presentation();slide=prs.slides.add_slide(prs.slide_layouts[6])
        group=slide.shapes.add_group_shape();box=group.shapes.add_textbox(Inches(1),Inches(1),Inches(5),Inches(1));box.text='Texto agrupado'
        run=box.text_frame.paragraphs[0].runs[0];run.font.color.rgb=C(255,255,255);run.font.size=PptPt(10)
        slide.background.fill.solid();slide.background.fill.fore_color.rgb=C(255,255,0);prs.save(source)
        r=self.result(source);issue=next(i for i in r['issues'] if i['rule']=='contrast')
        self.assertEqual(issue['source']['shape_path'],[0,0])
        dest=self.folder/'group-fixed.pptx';analyzer.apply_edit(source,dest,issue)
        self.assertFalse(any(i['rule']=='contrast' for i in self.result(dest)['issues']))

    def test_pptx_table_text_contrast_is_checked(self):
        from pptx.util import Inches
        from pptx.dml.color import RGBColor as C
        source=self.folder/'table.pptx';prs=Presentation();slide=prs.slides.add_slide(prs.slide_layouts[6])
        cell=slide.shapes.add_table(1,1,Inches(1),Inches(1),Inches(4),Inches(1)).table.cell(0,0)
        cell.fill.solid();cell.fill.fore_color.rgb=C(255,255,0);cell.text='Texto da célula';cell.text_frame.paragraphs[0].runs[0].font.color.rgb=C(255,255,255)
        prs.save(source);issue=next(i for i in self.result(source)['issues'] if i['rule']=='contrast')
        self.assertEqual(issue['source']['row'],0)
        dest=self.folder/'table-fixed.pptx';analyzer.apply_edit(source,dest,issue)
        self.assertFalse(any(i['rule']=='contrast' for i in self.result(dest)['issues']))



    def test_pdf_gradient_is_not_falsely_assumed_white(self):
        from reportlab.lib.colors import Color
        path=self.folder/'gradient.pdf';c=canvas.Canvas(str(path))
        c.linearGradient(0,0,600,0,[Color(0,0,0),Color(.15,.15,.15)],extend=True)
        c.setFillColorRGB(0,0,0);c.setFont('Helvetica',20);c.drawString(40,740,'Texto sobre degrade');c.save()
        result=self.result(path)
        self.assertGreater(result['measured']['contrast'],0)
        self.assertTrue(any(i['rule']=='contrast' and 'renderizada' in i['evidence'] for i in result['issues']))
        self.assertLess(result['pages'][0]['blocks'][0]['runs'][0]['measured_contrast'],1.2)

    def test_pdf_gradient_in_form_is_measured(self):
        from reportlab.lib.colors import Color
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import DecodedStreamObject, NameObject, DictionaryObject, ArrayObject, FloatObject
        path=self.folder/'form-gradient.pdf';c=canvas.Canvas(str(path))
        c.linearGradient(0,0,600,0,[Color(0,0,0),Color(.15,.15,.15)],extend=True)
        c.setFillColorRGB(0,0,0);c.drawString(40,740,'Texto sobre formulario');c.save()
        writer=PdfWriter();writer.clone_document_from_reader(PdfReader(path));page=writer.pages[0]
        form=DecodedStreamObject();form.set_data(page.get_contents().get_data())
        form.update({NameObject('/Type'):NameObject('/XObject'),NameObject('/Subtype'):NameObject('/Form'),
                     NameObject('/BBox'):ArrayObject([FloatObject(v) for v in page.mediabox]),NameObject('/Resources'):page['/Resources']})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/XObject'):DictionaryObject({NameObject('/Fundo'):writer._add_object(form)})})
        content=DecodedStreamObject();content.set_data(b'/Fundo Do');page[NameObject('/Contents')]=writer._add_object(content);writer.write(path)
        result=self.result(path)
        self.assertGreater(result['measured']['contrast'],0)
        self.assertTrue(any(i['rule']=='contrast' for i in result['issues']))

    def test_docx_header_and_footer_are_analyzed(self):
        path=self.folder/'outside-body.docx';doc=Document()
        doc.add_paragraph('Texto principal.').runs[0].font.size=Pt(20)
        doc.sections[0].header.paragraphs[0].text='Cabeçalho com informação.'
        doc.sections[0].footer.paragraphs[0].text='Rodapé com informação.'
        for p in [doc.sections[0].header.paragraphs[0],doc.sections[0].footer.paragraphs[0]]:
            p.runs[0].font.color.rgb=RGBColor(255,255,255);p.runs[0].font.size=Pt(8)
        doc.save(path)
        result=self.result(path)
        issues=[i for i in result['issues'] if i['rule']=='contrast']
        self.assertTrue(any('Cabeçalho' in i['location'] for i in issues))
        self.assertTrue(any('Rodapé' in i['location'] for i in issues))
        issue=issues[0];destination=self.folder/'header-fixed.docx';analyzer.apply_edit(path,destination,issue)
        self.assertFalse(any(i['rule']=='contrast' and i['id']==issue['id'] for i in self.result(destination)['issues']))

    def test_docx_hyperlink_text_is_not_silently_approved(self):
        from docx.oxml import OxmlElement
        path=self.folder/'link.docx';doc=Document();p=doc.add_paragraph('Texto principal.')
        link=OxmlElement('w:hyperlink');run=OxmlElement('w:r');text=OxmlElement('w:t');text.text='Texto do link';run.append(text);link.append(run);p._p.append(link);doc.save(path)
        result=self.result(path)
        self.assertTrue(any('Texto do link' in b.get('text','') for p in result['pages'] for b in p['blocks']))
        self.assertFalse(any(i['rule']=='content_unchecked' for i in result['issues']))

    def test_docx_solid_shading_does_not_use_background_fill(self):
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        path=self.folder/'solid-pattern.docx';doc=Document();p=doc.add_paragraph('Texto sobre padrão sólido.')
        p.runs[0].font.color.rgb=RGBColor(0,0,0)
        shade=OxmlElement('w:shd');shade.set(qn('w:val'),'solid');shade.set(qn('w:color'),'000000');shade.set(qn('w:fill'),'FFFFFF');p._p.get_or_add_pPr().append(shade);doc.save(path)
        result=self.result(path)
        issue=next(i for i in result['issues'] if i['rule']=='contrast')
        self.assertEqual(issue['background'],'#000000')


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=temporary_workspace();cls.old_data=server.DATA
        server.DATA=Path(cls.tmp.name)/'jobs';server.DATA.mkdir()
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
        cls.url='http://127.0.0.1:'+str(cls.http.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.thread.join();server.DATA=cls.old_data;cleanup_workspace(cls.tmp)
    def request(self,path,body=None):
        req=Request(self.url+path,data=json.dumps(body).encode() if body is not None else None,
                    headers={'Content-Type':'application/json'})
        with urlopen(req) as response:return response.read(),response.headers
    def test_full_revision_flow_download_and_report(self):
        data,_=self.request('/api/demo',{});job=json.loads(data)
        self.assertEqual(job['version'],1)
        fixes=[i['id'] for i in job['analysis']['issues'] if i['action'] in {'font','contrast'}]
        nextdata,_=self.request('/api/assist',{'id':job['id'],'issues':fixes});revised=json.loads(nextdata)
        self.assertEqual(revised['version'],2)
        self.assertEqual(revised['root_id'],job['id'])
        self.assertGreater(revised['comparison']['not_found'],0)
        rules={i['rule'] for i in revised['analysis']['issues']}
        self.assertNotIn('contrast',rules);self.assertNotIn('font_size',rules)
        binary,_=self.request('/api/job/'+revised['id']+'/file')
        prs=Presentation(BytesIO(binary));self.assertIn('Geografia',prs.slides[0].shapes.title.text)
        html,headers=self.request('/api/job/'+revised['id']+'/report');self.assertIn('Versão 2',html.decode());self.assertIn('attachment',headers['Content-Disposition'])
        raw,_=self.request('/api/analyze',{'filename':'Nova_versao.pptx','file':base64.b64encode(binary).decode(),'context':CONTEXT,'parent_id':revised['id']})
        self.assertEqual(json.loads(raw)['version'],3)
    def test_validation_and_origin_guard(self):
        with self.assertRaises(HTTPError) as err:self.request('/api/analyze',{'filename':'file.pdf','file':'!invalid!','context':CONTEXT})
        self.assertEqual(err.exception.code,400)
        req=Request(self.url+'/api/demo',data=b'{}',headers={'Content-Type':'application/json','Origin':'https://external.example'})
        with self.assertRaises(HTTPError) as err:urlopen(req)
        self.assertEqual(err.exception.code,403)
    def test_pdf_preview_endpoint_returns_rendered_image(self):
        stream=BytesIO();c=canvas.Canvas(stream);c.drawString(40,740,'PDF para teste de renderizacao');c.save()
        response,_=self.request('/api/analyze',{'filename':'preview.pdf','file':base64.b64encode(stream.getvalue()).decode(),'context':CONTEXT})
        job=json.loads(response)
        data,headers=self.request('/api/job/'+job['id']+'/page/0')
        self.assertEqual(headers['Content-Type'],'image/png')
        with Image.open(BytesIO(data)) as image:self.assertGreater(image.width,500)
        req=Request(self.url+'/api/jobs',headers={'Host':'external.example'})
        with self.assertRaises(HTTPError) as err:urlopen(req)
        self.assertEqual(err.exception.code,403)
    def test_report_escapes_user_content(self):
        data,_=self.request('/api/demo',{});job=json.loads(data)
        job['filename']='<script>alert(1)</script>.pptx'
        text=server.report(job).decode()
        self.assertNotIn('<script>',text);self.assertIn('&lt;script&gt;',text)

    def test_stored_analysis_is_upgraded_without_changing_material(self):
        data,_=self.request('/api/demo',{});job=json.loads(data)
        material=server.file_path(job).read_bytes();target=server.job_path(job['id'])/'analysis.json'
        job['analysis'].pop('engine_version');job['analysis']['issues']=[]
        target.write_text(json.dumps(job),encoding='utf-8')
        current=json.loads(self.request('/api/job/'+job['id'])[0])
        self.assertEqual(current['analysis']['engine_version'],analyzer.ENGINE_VERSION)
        self.assertTrue(current['analysis']['issues']);self.assertEqual(current['version'],1)
        self.assertEqual(server.file_path(current).read_bytes(),material)



if __name__=='__main__':unittest.main(verbosity=2)
