from io import BytesIO
from contextlib import contextmanager
import base64
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request

from PIL import Image
import pdfplumber
import pypdfium2 as pdfium
from pypdf import PdfReader,PdfWriter
from pypdf.generic import ArrayObject,BooleanObject,DictionaryObject,NameObject,NumberObject,TextStringObject
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

import analyzer
import image_quick_edit
import pdf_image_edit
import pdf_structure
import server


DESCRIPTION='Um quadrado azul sobre fundo branco.'
CONTEXT={'discipline':'Matemática','activity':'Atividade de sala','needs':'Leitor de tela',
         'technology':'NVDA','min_font':18}


def material(path,alt='',tagged=True):
    image=BytesIO();Image.new('RGB',(60,30),'blue').save(image,format='PNG');image.seek(0)
    buffer=BytesIO();pdf=canvas.Canvas(buffer,pagesize=(600,800))
    pdf._code.append('/P <</MCID 1>> BDC')
    pdf.setFont('Helvetica',12);pdf.drawString(60,730,'Texto pequeno acima da imagem.');pdf._code.append('EMC')
    if tagged:pdf._code.append('/Figure <</MCID 0>> BDC')
    pdf.drawImage(ImageReader(image),60,500,width=220,height=110)
    if tagged:pdf._code.append('EMC')
    pdf._code.append('/P <</MCID 2>> BDC')
    pdf.setFont('Helvetica',18);pdf.drawString(60,400,'Texto depois da imagem.');pdf._code.append('EMC');pdf.save()
    writer=PdfWriter(clone_from=BytesIO(buffer.getvalue()))
    if tagged:
        page=writer.pages[0]
        tree=DictionaryObject({NameObject('/Type'):NameObject('/StructTreeRoot')})
        tree_ref=writer._add_object(tree)
        document=DictionaryObject({NameObject('/Type'):NameObject('/StructElem'),NameObject('/S'):NameObject('/Document'),NameObject('/P'):tree_ref})
        document_ref=writer._add_object(document)
        children=[];parents={}
        for role,mcid in (('P',1),('Figure',0),('P',2)):
            node=DictionaryObject({NameObject('/Type'):NameObject('/StructElem'),NameObject('/S'):NameObject('/'+role),
                NameObject('/P'):document_ref,NameObject('/Pg'):page.indirect_reference,NameObject('/K'):NumberObject(mcid)})
            if role=='Figure' and alt:node[NameObject('/Alt')]=TextStringObject(alt)
            ref=writer._add_object(node);children.append(ref);parents[mcid]=ref
        document[NameObject('/K')]=ArrayObject(children)
        tree[NameObject('/K')]=document_ref
        tree[NameObject('/ParentTree')]=writer._add_object(DictionaryObject({NameObject('/Nums'):ArrayObject([
            NumberObject(0),ArrayObject([parents[n] for n in range(3)])])}))
        tree[NameObject('/ParentTreeNextKey')]=NumberObject(1)
        writer.root_object[NameObject('/StructTreeRoot')]=tree_ref
        writer.root_object[NameObject('/MarkInfo')]=DictionaryObject({NameObject('/Marked'):BooleanObject(True)})
        page[NameObject('/StructParents')]=NumberObject(0)
    writer.root_object[NameObject('/Lang')]=TextStringObject('pt-BR')
    writer.write(path)


class PDFImageAccessTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.folder=Path(temporary.name)
        self.source=self.folder/'source.pdf';self.target=self.folder/'fixed.pdf'
        for context in (patch.dict('os.environ',{'OPENROUTER_API_KEY':''}),patch('analyzer.ocr',return_value=([],''))):
            context.start();self.addCleanup(context.stop)

    def block(self,path):
        result=analyzer.analyze(path,dict(CONTEXT))
        return next(b for p in result['pages'] for b in p['blocks'] if b['type'] in ('image','pdf_image'))

    def assert_access(self,path,description=DESCRIPTION):
        reader=PdfReader(path);info=pdf_structure.inspect(reader)
        self.assertEqual(len(info['figures']),1)
        key,entry=next(iter(info['figures'].items()))
        node=pdf_image_edit.structure_node(reader,entry['path'])
        self.assertEqual(entry['alt'],description)
        with pdfplumber.open(path) as pdf:
            image=next(i for i in pdf.pages[0].images if i.get('mcid')==key[1])
            expected=[image[k] for k in ('x0','y0','x1','y1')]
        box=pdf_image_edit.figure_bounds(node)
        self.assertIsNotNone(box)
        for actual,wanted in zip(box,expected):self.assertAlmostEqual(actual,wanted,places=3)
        tree=reader.trailer['/Root']['/StructTreeRoot'].get_object()
        parents=pdf_image_edit.number_entries(tree['/ParentTree'])[reader.pages[0]['/StructParents']].get_object()
        self.assertEqual(parents[key[1]].get_object(),node)
        return box

    @contextmanager
    def product(self):
        data=self.folder/'http-jobs';data.mkdir()
        with patch.object(server,'DATA',data):
            http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
            worker=threading.Thread(target=http.serve_forever,daemon=True);worker.start()
            base='http://127.0.0.1:'+str(http.server_port)
            def request(path,body=None):
                query=urllib.request.Request(base+path,
                    data=json.dumps(body).encode() if body is not None else None,
                    headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(query,timeout=10) as response:
                    raw=response.read()
                    return json.loads(raw) if response.headers.get_content_type()=='application/json' else raw
            try:yield request
            finally:http.shutdown();worker.join(timeout=3);http.server_close()

    def test_upload_save_and_download_use_the_product_endpoints(self):
        material(self.source)
        with self.product() as request:
            job=request('/api/analyze',{'filename':'source.pdf','file':base64.b64encode(self.source.read_bytes()).decode(),'context':CONTEXT})
            issue=next(i for i in job['analysis']['issues'] if i.get('quick_image'))
            updated=request('/api/image-adjust',{'id':job['id'],'issue_id':issue['id'],'value':{'alt':DESCRIPTION,'scale':1}})
            downloaded=request('/api/job/'+updated['id']+'/file')
            self.target.write_bytes(downloaded)
            self.assert_access(self.target)
            self.assertEqual(updated['version'],2)
            self.assertEqual(request('/api/job/'+updated['id']+'/original'),self.source.read_bytes())
            self.assertEqual(request('/api/job/'+updated['id']+'/file'),downloaded)

    def test_old_pdf_is_repaired_by_download_without_changing_stored_material(self):
        material(self.source,DESCRIPTION)
        with self.product() as request:
            original=self.source.read_bytes()
            job=request('/api/analyze',{'filename':'old.pdf','file':base64.b64encode(original).decode(),'context':CONTEXT})
            self.target.write_bytes(request('/api/job/'+job['id']+'/file'))
            self.assert_access(self.target)
            self.assertEqual(server.file_path(job).read_bytes(),original)
            self.assertEqual(request('/api/job/'+job['id']+'/original'),original)

    def test_saving_description_adds_position_for_existing_tag(self):
        material(self.source)
        image_quick_edit.apply(self.source,self.target,self.block(self.source),{'alt':DESCRIPTION})
        self.assert_access(self.target)

    def test_new_tag_on_untagged_image_has_position_and_parent_link(self):
        material(self.source,tagged=False)
        image_quick_edit.apply(self.source,self.target,self.block(self.source),{'alt':DESCRIPTION})
        self.assert_access(self.target)

    def test_metadata_repair_preserves_pixels_page_count_and_text(self):
        material(self.source,DESCRIPTION)
        self.target.write_bytes(self.source.read_bytes())
        pdf_image_edit.sync_figure_bounds(self.target)
        self.assert_access(self.target)
        before=pdfium.PdfDocument(self.source);after=pdfium.PdfDocument(self.target)
        try:
            self.assertEqual(len(before),len(after))
            self.assertEqual(before[0].render(scale=1).to_pil().tobytes(),after[0].render(scale=1).to_pil().tobytes())
        finally:before.close();after.close()
        self.assertEqual(PdfReader(self.source).pages[0].extract_text(),PdfReader(self.target).pages[0].extract_text())

    def test_saving_same_text_repairs_old_pdf_then_becomes_a_noop(self):
        material(self.source,DESCRIPTION)
        data=self.folder/'jobs';data.mkdir()
        with patch.object(server,'DATA',data):
            job=server.create_job(self.source.read_bytes(),'source.pdf',dict(CONTEXT))
            issue=next(i for i in job['analysis']['issues'] if i.get('quick_image'))
            updated=server.adjust_image_job(job,issue,{'alt':DESCRIPTION,'scale':1})
            self.assertNotEqual(updated['id'],job['id'])
            self.assert_access(server.file_path(updated))
            issue=next(i for i in updated['analysis']['issues'] if i.get('quick_image'))
            repeated=server.adjust_image_job(updated,issue,{'alt':DESCRIPTION,'scale':1})
            self.assertTrue(repeated['unchanged']);self.assertEqual(repeated['id'],updated['id'])

    def test_enlargement_updates_accessibility_bounds(self):
        material(self.source)
        image_quick_edit.apply(self.source,self.target,self.block(self.source),{'alt':DESCRIPTION,'scale':1.25})
        box=self.assert_access(self.target)
        self.assertAlmostEqual(box[2]-box[0],275,places=3)
        self.assertAlmostEqual(box[3]-box[1],137.5,places=3)

    def test_font_reflow_and_recolor_keep_image_access_position(self):
        material(self.source,DESCRIPTION);pdf_image_edit.sync_figure_bounds(self.source)
        old=self.assert_access(self.source)
        initial=analyzer.analyze(self.source,dict(CONTEXT))
        issue=next(i for i in initial['issues'] if i['rule']=='font_size')
        analyzer.apply_edit(self.source,self.target,issue,20)
        new=self.assert_access(self.target)
        self.assertLess(new[1],old[1])
        color=self.folder/'color.pdf'
        from pdf_edit import recolor
        result=analyzer.analyze(self.target,dict(CONTEXT))
        block=next(b for b in result['pages'][0]['blocks'] if b.get('text','').startswith('Texto pequeno'))
        recolor(self.target,color,{**issue,'pdf_box':[block['x'],block['y'],block['x']+block['w'],block['y']+block['h']]},'#000000')
        self.assert_access(color)

    def test_legacy_alt_edit_route_adds_position(self):
        material(self.source)
        result=analyzer.analyze(self.source,dict(CONTEXT))
        issue=next(i for i in result['issues'] if i.get('quick_image'))
        analyzer.apply_edit(self.source,self.target,issue,DESCRIPTION)
        self.assert_access(self.target)

    def test_existing_shared_layout_attributes_are_preserved(self):
        layout=DictionaryObject({NameObject('/O'):NameObject('/Layout'),NameObject('/Placement'):NameObject('/Block')})
        other=DictionaryObject({NameObject('/O'):NameObject('/UserProperties'),NameObject('/P'):ArrayObject()})
        attributes=ArrayObject([other,layout,NumberObject(1)])
        figure=DictionaryObject({NameObject('/A'):attributes})
        pdf_image_edit.set_figure_bounds(figure,[60,500,280,610])
        self.assertEqual(figure['/A'][0],other)
        self.assertEqual(figure['/A'][1]['/Placement'],'/Block')
        self.assertEqual(figure['/A'][2],1)
        self.assertNotIn('/BBox',layout)

