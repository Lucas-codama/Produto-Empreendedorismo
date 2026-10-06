"""Reproducible capability audit with independent, deliberately adverse files.

Never uploads materials or changes saved jobs. Fixtures remain local.
"""
from pathlib import Path
from io import BytesIO
import json

from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image, ImageDraw
from pptx import Presentation
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color
from reportlab.lib.utils import ImageReader

import analyzer
import vision_checks

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / '.runtime' / 'audit-fixtures'
OUTPUT = ROOT.parent / 'output'
CONTEXT = dict(discipline='Geografia', activity='Atividade', needs='Ampliação e leitor de tela',
               technology='Leitor de tela', min_font=20)


def run():
    FIXTURES.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(exist_ok=True)
    cases = []

    def check(name, path, expected, predicate, limit=False, context=None,pending=False):
        result = analyzer.analyze(path, context or CONTEXT)
        ok = bool(predicate(result))
        cases.append(dict(case=name, expected=expected, status='ATIVAÇÃO PENDENTE' if pending else ('CONFERÊNCIA DO PROFESSOR' if limit else 'CONFIRMADO') if ok else 'FALHOU',
                          fixture=str(path), measured=result['measured'],
                          findings=[dict(rule=i['rule'], severity=i['severity'], evidence=i['evidence']) for i in result['issues']]))
        return result

    def rules(r): return {i['rule'] for i in r['issues']}

    def pdf(name, fg, bg=None, size=11, gradient=False, cmyk=False):
        path = FIXTURES / (name + '.pdf')
        c = canvas.Canvas(str(path), pagesize=(300, 200))
        if gradient:
            c.linearGradient(0, 0, 300, 0, [Color(0,0,0), Color(.15,.15,.15)], extend=True)
        elif bg:
            c.setFillColorRGB(*bg); c.rect(0,0,300,200,fill=1,stroke=0)
        if cmyk: c.setFillColorCMYK(*fg)
        else: c.setFillColorRGB(*fg)
        c.setFont('Helvetica',size); c.drawString(30,110,'Texto para verificar'); c.save()
        return path

    white_yellow = pdf('branco-amarelo', (1,1,1), (1,1,0))
    check('PDF branco sobre amarelo', white_yellow, 'Contraste 1,07:1 e fonte de 11 pt abaixo de 20 pt.',
          lambda r: {'contrast','font_size'} <= rules(r) and '1.07:1' in next(i['evidence'] for i in r['issues'] if i['rule']=='contrast'))
    check('PDF preto sobre amarelo', pdf('preto-amarelo',(0,0,0),(1,1,0)), 'Não emitir alerta de contraste.', lambda r: 'contrast' not in rules(r) and r['measured']['contrast']>0)
    check('Fonte no limite individual', pdf('fonte-20',(0,0,0),size=20), '20 pt não fica abaixo da preferência de 20 pt.', lambda r: 'font_size' not in rules(r) and r['measured']['font']>0)
    check('Sem preferência individual', white_yellow, 'Não inventar um tamanho mínimo.', lambda r: 'font_size' not in rules(r),context=dict(CONTEXT,min_font=None))
    check('PDF com degradê escuro e texto preto', pdf('degrade-escuro',(0,0,0),gradient=True), 'Medir o fundo renderizado e detectar baixo contraste.', lambda r: 'contrast' in rules(r) and r['measured']['contrast']>0)
    check('PDF com cor CMYK', pdf('cmyk',(0,0,0,.2),cmyk=True), 'Converter pela renderização do PDF e detectar baixo contraste.',lambda r:'contrast' in rules(r) and r['measured']['contrast']>0)

    from PIL import ImageFont
    bitmap=Image.new('RGB',(1000,300),'yellow');ImageDraw.Draw(bitmap).text((35,85),'Texto em imagem',fill='white',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',64))
    path=FIXTURES/'digitalizado.pdf';c=canvas.Canvas(str(path),pagesize=(300,200));c.drawImage(ImageReader(bitmap),0,0,300,200);c.save()
    check('PDF digitalizado',path,'Reconhecer texto localmente e estimar contraste. Ativação depende da instalação do Tesseract.',lambda r:'ocr_review' in rules(r) and r['measured']['contrast']>0,pending=not vision_checks.executable())
    path=FIXTURES/'imagem.jpg';bitmap.save(path)
    check('JPG com texto',path,'Reconhecer texto localmente e estimar contraste; conferir transcrição. Ativação depende da instalação do Tesseract.',lambda r:'ocr_review' in rules(r) and r['measured']['text']>0,pending=not vision_checks.executable())
    path=FIXTURES/'tags-vazias.pdf';writer=PdfWriter();writer.clone_document_from_reader(PdfReader(white_yellow));writer.root_object[NameObject('/StructTreeRoot')]=DictionaryObject({NameObject('/Type'):NameObject('/StructTreeRoot')});writer.write(path)
    check('PDF com árvore de tags vazia',path,'Detectar erro objetivo de árvore vazia e texto não associado à estrutura.',lambda r:{'pdf_tags_empty','pdf_text_untagged'}<=rules(r))

    image_stream=BytesIO();bitmap.save(image_stream,format='PNG')
    for desc,name,expected_rule in [('', 'alt-ausente','alt_missing'),('imagem_12.png','alt-generico','alt_placeholder'),('Descrição propositalmente falsa: um cachorro azul.','alt-falso','alt_quality')]:
        doc=Document();pic=doc.add_picture(BytesIO(image_stream.getvalue()));pic._inline.docPr.set('descr',desc)
        path=FIXTURES/(name+'.docx');doc.save(path)
        check(name,path,'Detectar '+expected_rule+'; não certificar o sentido da imagem.',lambda r,rule=expected_rule:rule in rules(r),limit=name=='alt-falso')
    doc=Document();pic=doc.add_picture(BytesIO(image_stream.getvalue()))
    decorative=OxmlElement('a:extLst');ext=OxmlElement('a:ext');ext.set('uri','{C183D7F6-B498-43B3-948B-1728B52AA6E4}')
    from lxml import etree
    flag=etree.SubElement(ext,'{http://schemas.microsoft.com/office/drawing/2017/decorative}decorative');flag.set('val','1');decorative.append(ext);pic._inline.docPr.append(decorative)
    path=FIXTURES/'decorativa.docx';doc.save(path)
    check('Imagem marcada decorativa',path,'Respeitar o marcador sem pedir descrição; intenção ainda é humana.',lambda r:'alt_missing' not in rules(r) and r['measured']['images']==1)

    doc=Document();doc.add_paragraph('Texto do corpo acessível.').runs[0].font.size=Pt(20)
    run=doc.sections[0].header.paragraphs[0].add_run('Cabeçalho invisível: branco e pequeno');run.font.color.rgb=RGBColor(255,255,255);run.font.size=Pt(8)
    path=FIXTURES/'cabecalho.docx';doc.save(path)
    check('DOCX com problema apenas no cabeçalho',path,'Medir texto do cabeçalho e detectar contraste e fonte pequena.',lambda r:{'contrast','font_size'}<=rules(r) and any('Cabeçalho' in i['location'] for i in r['issues']))
    doc=Document();paragraph=doc.add_paragraph('Texto em sombreamento sólido preto');run=paragraph.runs[0];run.font.size=Pt(20);run.font.color.rgb=RGBColor(0,0,0)
    shade=OxmlElement('w:shd');shade.set(qn('w:val'),'solid');shade.set(qn('w:color'),'000000');shade.set(qn('w:fill'),'FFFFFF');paragraph._p.get_or_add_pPr().append(shade)
    path=FIXTURES/'sombreamento-solid.docx';doc.save(path)
    check('DOCX com padrão de sombreamento sólido',path,'Não usar incorretamente a cor de preenchimento branca como fundo.',lambda r:'contrast_unknown' in rules(r) or 'contrast' in rules(r))

    for titled in [True,False]:
        prs=Presentation();slide=prs.slides.add_slide(prs.slide_layouts[0 if titled else 6])
        if titled:slide.shapes.title.text='Título real'
        else:
            from pptx.util import Inches
            slide.shapes.add_textbox(Inches(1),Inches(1),Inches(5),Inches(1)).text='Texto que parece um título'
        path=FIXTURES/('titulo-real.pptx' if titled else 'titulo-caixa.pptx');prs.save(path)
        check('PPTX título reservado' if titled else 'PPTX título em caixa comum',path,'Reconhecer o espaço reservado; caixa comum não confirma título semântico.',lambda r,t=titled:('slide_title' not in rules(r)) if t else ('slide_title' in rules(r)))

    source=FIXTURES/'corrigir.docx';doc=Document();run=doc.add_paragraph('Conteúdo preservado.').runs[0];run.font.size=Pt(10);run.font.color.rgb=RGBColor(230,230,230);doc.save(source)
    result=analyzer.analyze(source,CONTEXT);dest=FIXTURES/'cor-corrigida.docx';issue=next(i for i in result['issues'] if i['rule']=='contrast');analyzer.apply_edit(source,dest,issue)
    result=check('Correção real de contraste em DOCX',dest,'Cor gravada e baixo contraste desaparece; conteúdo preservado.',lambda r:'contrast' not in rules(r) and Document(dest).paragraphs[0].text=='Conteúdo preservado.')
    final=FIXTURES/'fonte-corrigida.docx';analyzer.apply_edit(dest,final,next(i for i in result['issues'] if i['rule']=='font_size'),20)
    check('Correção real de fonte e original preservado',final,'Fonte de 20 pt salva; original permanece em 10 pt.',lambda r:'font_size' not in rules(r) and Document(final).paragraphs[0].runs[0].font.size.pt==20 and Document(source).paragraphs[0].runs[0].font.size.pt==10)

    data=dict(engine_version=analyzer.ENGINE_VERSION,cases=cases)
    (OUTPUT/'Auditoria_Verificacoes.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Auditoria das verificações do Entrelinhas','',f'Motor: {analyzer.ENGINE_VERSION}. Data: 06/10/2026. Sem IA. Testes locais com arquivos sintéticos, sem envio de materiais.', '',
           'O resultado confirma apenas os casos e recursos abaixo. Não certifica conformidade integral, compatibilidade com leitores de tela nem todos os arquivos desses formatos.', '',
           '| Caso | Resultado | Critério |','|---|---|---|']
    lines += [f"| {c['case']} | {c['status']} | {c['expected']} |" for c in cases]
    baseline=OUTPUT/'Auditoria_Verificacoes_Antes.json'
    if baseline.exists():
        failed=[c['case'] for c in json.loads(baseline.read_text(encoding='utf-8'))['cases'] if c['status']=='FALHOU']
        lines += ['', '## Problemas encontrados e tratados nesta auditoria', '',
                  'A execução anterior às correções apresentou falhas em: '+', '.join(failed)+'.',
                  'Agora os fundos complexos de PDF são medidos pela renderização; o padrão sólido do Word usa a cor visível do padrão. Cabeçalhos, rodapés, notas, caixas de texto e hyperlinks do Word são extraídos e podem receber correções de fonte, cor e descrição.',
                  'A inspeção de PDF inclui árvore vazia, MCIDs, títulos, figuras, idioma e cabeçalhos de tabelas. A ordem semântica ainda requer conferência.',
                  'A evidência inicial foi preservada em `Auditoria_Verificacoes_Antes.json`.']
    lines += ['', '## Limites', '',
              '- OCR clássico local foi integrado para PNG/JPG/PDF digitalizado. Neste computador sua instalação foi cancelada pelo Windows; ativação e teste real aguardam autorização. Nenhum arquivo é enviado a uma API.',
              '- PDF e imagens ganham uma versão de leitura editável em HTML. Isso não altera nem certifica as tags do PDF original.',
              '- Descrição de imagem é metadado: o significado e a adequação pedagógica exigem conferência humana.',
              '- A estrutura técnica do PDF é inspecionada. A sequência que preserva o significado, gráficos e relações de tabelas precisam ser conferidos pelo professor.',
              '- Contraste de renderização e contraste de imagens são estimativas. Tamanho físico de fonte em imagem não é inferido pela altura dos pixels.',
              '- Word: o corpo, células, cabeçalhos, rodapés, notas, caixas e hyperlinks são analisados. A prévia não reproduz a paginação original.',
              '- Não verifica ortografia, linguagem clara, idioma, links, uso exclusivo de cores, conteúdo de gráficos, fórmulas ou layout após ampliação.',
              '- Não houve teste com NVDA, JAWS ou a tecnologia assistiva do estudante.', '',
              'Reprodução: `python -m unittest -v test_analyzer test_extended` e `python audit_capabilities.py`. Evidências por regra, contagens e arquivos em `Auditoria_Verificacoes.json`.', '',
              'Referência usada na correção do sombreamento: [Microsoft — padrões de sombreamento](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.shadingpatternvalues?view=openxml-3.0.1). O padrão sólido tem preenchimento integral e não permite presumir a cor de fundo declarada como cor visível.']
    (OUTPUT/'Auditoria_Verificacoes.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(engine_version=analyzer.ENGINE_VERSION,total=len(cases),summary={s:sum(c['status']==s for c in cases) for s in ['CONFIRMADO','CONFERÊNCIA DO PROFESSOR','ATIVAÇÃO PENDENTE','FALHOU']},failures=[c['case'] for c in cases if c['status']=='FALHOU']),ensure_ascii=False))
    return cases


if __name__=='__main__':raise SystemExit(1 if any(c['status']=='FALHOU' for c in run()) else 0)
