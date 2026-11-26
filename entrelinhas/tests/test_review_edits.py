from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from PIL import Image
import pdfplumber
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

import analyzer
import image_ai
import review_store
import server
import workspace_store


CONTEXT={'discipline':'Matemática','activity':'Atividade de sala',
    'needs':'Leitura ampliada e descrição de imagens','technology':'Ampliação e leitor de tela','min_font':18}
DESCRIPTION='Um quadrado azul sobre fundo branco.'


def approved_description():
    return {'score':990,'verdict':'adequada','matches_image':True,'sufficient':True,
        'image_type':'photo','image_summary':DESCRIPTION,
        'essential_details':[{'fact':'Quadrado azul','evidence':'quadrado azul'}],'data_points':[],
        'explanation':'A descrição está boa.','differences':[],'suggested_description':'','visible_text':''}


def word_activity():
    doc=Document()
    doc.styles['Normal'].font.size=Pt(18)
    run=doc.add_paragraph().add_run('Texto pequeno para ajustar.')
    run.font.size=Pt(8);run.font.color.rgb=RGBColor(0,0,0)
    image=BytesIO();Image.new('RGB',(40,40),'blue').save(image,format='PNG');image.seek(0)
    doc.add_picture(image,width=Inches(1))
    output=BytesIO();doc.save(output)
    return output.getvalue()


class RevisionFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name);self.data=self.folder/'jobs';self.data.mkdir()
        for context in (patch.object(server,'DATA',self.data),patch.dict('os.environ',{'OPENROUTER_API_KEY':''}),
            patch('analyzer.ocr',return_value=([],''))):
            context.start();self.addCleanup(context.stop)
        self.job=server.create_job(word_activity(),'atividade.docx',dict(CONTEXT))

    def image_issue(self,job):
        return next(i for i in job['analysis']['issues'] if i.get('quick_image'))

    def save_description(self,job=None):
        job=job or self.job
        return server.adjust_image_job(job,self.image_issue(job),{'alt':DESCRIPTION,'scale':1})

    def test_word_font_change_is_in_the_file_and_removes_the_finding(self):
        issue=next(i for i in self.job['analysis']['issues'] if i['rule']=='font_size')
        updated=server.edit_job(self.job,[{'issue_id':issue['id'],'value':18}])
        self.assertFalse(any(i['rule']=='font_size' for i in updated['analysis']['issues']))
        self.assertEqual(Document(server.file_path(updated)).paragraphs[0].runs[0].font.size.pt,18)
        self.assertEqual(Document(server.file_path(self.job)).paragraphs[0].runs[0].font.size.pt,8)

    def test_verified_image_stays_resolved_despite_an_old_empty_progress_snapshot(self):
        issue=self.image_issue(self.job)
        block=next(b for p in self.job['analysis']['pages'] for b in p['blocks'] if b['id']==issue['block_id'])
        review_store.remember_ai(self.folder,image_ai.approval_key(block['image'],DESCRIPTION),approved_description())
        updated=self.save_description()
        quality=self.image_issue(updated)
        self.assertIn(quality['id'],updated['resolved_issues'])
        workspace_store.save_progress(self.folder,updated,{'page':0,'resolved':[]})
        loaded=server.load_job(updated['id'])
        self.assertIn(quality['id'],loaded['resolved_issues'])
        findings=review_store.details(self.folder,loaded['id'])['findings']
        self.assertTrue(next(i for i in findings if i['id']==quality['id'])['resolved'])
        font=next(i for i in loaded['analysis']['issues'] if i['rule']=='font_size')
        with patch.dict('os.environ',{'OPENROUTER_API_KEY':'test-key'}),\
            patch('review_store.ai_status',return_value={'accepted_count':0,'result':None}),\
            patch('image_ai.verify',side_effect=AssertionError('Uma mudança na prévia não deve reabrir a imagem aprovada.')):
            final=server.edit_job(loaded,[{'issue_id':font['id'],'value':18}])
        self.assertIn(quality['id'],final['resolved_issues'])
        self.assertEqual(final['review']['status'],'completed')

    def test_unavailable_ai_allows_manual_confirmation_after_saving(self):
        with patch.dict('os.environ',{'OPENROUTER_API_KEY':'test-key'}),patch('image_ai.verify',side_effect=image_ai.ImageAIError('Sem saldo')):
            updated=self.save_description()
        quality=self.image_issue(updated)
        self.assertEqual(quality['rule'],'alt_quality')
        self.assertTrue(workspace_store.can_resolve(quality))
        workspace_store.save_progress(self.folder,updated,{'page':0,'resolved':[quality['id']]})
        loaded=server.load_job(updated['id'])
        findings=review_store.details(self.folder,loaded['id'])['findings']
        self.assertTrue(next(i for i in findings if i['id']==quality['id'])['resolved'])
        font=next(i for i in loaded['analysis']['issues'] if i['rule']=='font_size')
        with patch('image_ai.verify',side_effect=AssertionError('Não deve conferir novamente uma imagem já confirmada.')):
            final=server.edit_job(loaded,[{'issue_id':font['id'],'value':18}])
        self.assertIn(quality['id'],final['resolved_issues'])
        self.assertEqual(final['review']['status'],'completed')

    def test_image_without_a_description_cannot_be_manually_bypassed(self):
        issue=self.image_issue(self.job)
        self.assertFalse(workspace_store.can_resolve(issue))
        with self.assertRaises(analyzer.MaterialError):
            workspace_store.save_progress(self.folder,self.job,{'page':0,'resolved':[issue['id']]})

    def test_saving_the_same_image_again_does_not_create_another_version(self):
        updated=self.save_description()
        before=len(list(self.data.iterdir()))
        repeated=self.save_description(updated)
        self.assertTrue(repeated['unchanged'])
        self.assertEqual(repeated['id'],updated['id'])
        self.assertEqual(repeated['version'],updated['version'])
        self.assertEqual(len(list(self.data.iterdir())),before)
        self.assertEqual(Document(server.file_path(updated)).inline_shapes[0]._inline.docPr.get('descr'),DESCRIPTION)

    def test_multiple_pdf_font_edits_remain_valid_after_text_reflows(self):
        output=BytesIO();pdf=canvas.Canvas(output,pagesize=(600,800));pdf.scale(.75,.75)
        pdf.setFont('Helvetica',8/.75);x=60/.75
        for word in 'Os valores representam a água usada para beber em cada dia.'.split():
            pdf.drawString(x,650/.75,word+' ');x+=stringWidth(word+' ','Helvetica',8/.75)
        pdf.setFont('Helvetica',12/.75);pdf.drawString(60/.75,560/.75,'Outro trecho para ajustar.')
        pdf.save()
        original=server.create_job(output.getvalue(),'atividade.pdf',{**CONTEXT,'min_font':20})
        requests=[{'issue_id':i['id'],'value':20} for i in original['analysis']['issues'] if i['rule']=='font_size']
        self.assertEqual(len(requests),2)
        updated=server.edit_job(original,requests)
        self.assertFalse(any(i['rule']=='font_size' for i in updated['analysis']['issues']))


class PDFFontTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)

    def analyze(self,path):return analyzer.analyze(path,{**CONTEXT,'min_font':20})

    def test_font_size_uses_page_points_despite_a_scaled_text_matrix(self):
        source=self.folder/'scaled.pdf';target=self.folder/'updated.pdf'
        pdf=canvas.Canvas(str(source),pagesize=(600,800))
        pdf.scale(.75,.75);pdf.setFont('Helvetica',24);pdf.drawString(60/.75,700/.75,'Texto para ajustar')
        pdf.save()
        initial=self.analyze(source);issue=next(i for i in initial['issues'] if i['rule']=='font_size')
        analyzer.apply_edit(source,target,issue,20)
        self.assertFalse(any(i['rule']=='font_size' for i in self.analyze(target)['issues']))
        with pdfplumber.open(target) as result:
            self.assertTrue(all(abs(c['size']-20)<.05 for c in result.pages[0].chars))

    def test_enlarging_a_long_line_wraps_without_splitting_the_lines_below(self):
        source=self.folder/'small.pdf';target=self.folder/'readable.pdf'
        text='Os valores representam a água usada para beber em cada dia.'
        pdf=canvas.Canvas(str(source),pagesize=(600,800));pdf.scale(.75,.75)
        pdf.setFont('Helvetica',8/.75);x=60/.75
        for word in text.split():
            pdf.drawString(x,650/.75,word+' ');x+=stringWidth(word+' ','Helvetica',8/.75)
        pdf.setFont('Helvetica',20/.75)
        pdf.drawString(60/.75,580/.75,'Marcador')
        pdf.drawString(480/.75,580/.75,'Final')
        pdf.save()
        issue=next(i for i in self.analyze(source)['issues'] if i['rule']=='font_size')
        analyzer.apply_edit(source,target,issue,20)
        self.assertFalse(any(i['rule']=='font_size' for i in self.analyze(target)['issues']))
        with pdfplumber.open(target) as doc:
            words=doc.pages[0].extract_words();markers=[w for w in words if w['text'] in ('Marcador','Final')]
            self.assertEqual(len(markers),2)
            self.assertLess(abs(markers[0]['top']-markers[1]['top']),.1)
            self.assertTrue(all(w['x1']<doc.pages[0].width and w['bottom']<doc.pages[0].height for w in words))
            self.assertIn('cada dia.',doc.pages[0].extract_text())

    def test_rounding_error_does_not_report_a_20_point_font_as_too_small(self):
        source=self.folder/'rounding.pdf';pdf=canvas.Canvas(str(source))
        pdf.scale(.75,.75);pdf.setFont('Helvetica',26.66665);pdf.drawString(80,800,'Fonte ajustada')
        pdf.save()
        self.assertFalse(any(i['rule']=='font_size' for i in self.analyze(source)['issues']))


if __name__=='__main__':unittest.main()
