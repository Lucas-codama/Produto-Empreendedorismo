"""Ten-page, deliberately flawed, tagged PDF with an independent answer key."""
from pathlib import Path
from io import BytesIO
import json
from PIL import Image,ImageDraw,ImageFont
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader,PdfWriter
from pypdf.generic import DictionaryObject,NameObject,ArrayObject,NumberObject,TextStringObject,BooleanObject
import pypdfium2 as pdfium
import analyzer

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'output'/'Teste_Acessibilidade'
TARGET=OUT/'Teste_Acessibilidade_10_Paginas.pdf'
W,H=595.28,841.89


def make():
    OUT.mkdir(parents=True,exist_ok=True)
    pdfmetrics.registerFont(TTFont('TestArial','C:/Windows/Fonts/arial.ttf'))
    pdfmetrics.registerFont(TTFont('TestArialBold','C:/Windows/Fonts/arialbd.ttf'))
    chart=Image.new('RGB',(1100,620),'white');draw=ImageDraw.Draw(chart)
    f=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',36);fb=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',42)
    draw.text((65,30),'Valores de três regiões',fill='#202138',font=fb)
    draw.line((80,490,1020,490),fill='#202138',width=4)
    for x,value,label in [(180,20,'A'),(465,40,'B'),(750,60,'C')]:
        y=490-value*5;draw.rectangle((x,y,x+145,488),fill='#5473BC')
        draw.text((x+40,y-48),str(value),fill='#202138',font=f);draw.text((x+55,515),label,fill='#202138',font=f)
    draw.text((65,570),'Dados fictícios para o teste.',fill='#202138',font=f)
    pages=[];stream=BytesIO();c=canvas.Canvas(stream,pagesize=(W,H));c.setTitle('Teste de acessibilidade - 10 páginas');c.setAuthor('Entrelinhas')
    current=[]
    def mark(role,render,alt=None):
        index=len(current);c._code.append(f'/{role} <</MCID {index}>> BDC');render();c._code.append('EMC')
        item={'role':role,'mcid':index}
        if alt is not None:item['alt']=alt
        current.append(item);return item
    def text(value,y,size=22,color='#202138',role='P',bold=False):
        def paint():
            c.setFont('TestArialBold' if bold else 'TestArial',size);c.setFillColor(color);c.drawString(58,y,value)
        return mark(role,paint)
    def header(number,title,role='H1'):
        nonlocal current
        current=[];c.setFillColor('#FAF7F3');c.rect(0,0,W,H,fill=1,stroke=0)
        text(f'ENTRELINHAS / CASO {number:02}',772,20,color='#5B478B',bold=True)
        text(title,718,30,role=role,bold=True)
    def figure(alt):
        return mark('Figure',lambda:c.drawImage(ImageReader(chart),58,290,width=480,height=270),alt)
    def finish(number,order=None):
        c._code.append('/Artifact BMC');c.setFillColor('#5B478B');c.setFont('TestArial',20);c.drawString(58,52,'Documento com barreiras intencionais');c.drawRightString(W-58,52,str(number));c._code.append('EMC')
        pages.append({'items':list(current),'order':order});c.showPage()
    header(1,'Contraste insuficiente')
    c.setFillColor('#FFFF00');c.roundRect(48,430,500,142,18,fill=1,stroke=0)
    text('Compare os valores das regiões A e B.',510,22,'#FFFFFF');finish(1)
    header(2,'Fonte pequena')
    text('O prazo para entregar a atividade é sexta-feira, às 17h.',520,9)
    text('A resposta deve ter no máximo cinco linhas.',498,9);finish(2)
    header(3,'Imagem sem descrição');figure(None);finish(3)
    header(4,'Descrição genérica');figure('imagem_01.png');finish(4)
    header(5,'Descrição que não corresponde');figure('Fotografia de um cachorro correndo na praia.');finish(5)
    header(6,'Tabela sem cabeçalhos')
    table={'role':'Table','children':[]}
    for ri,row in enumerate([['Região','Valor'],['A','20'],['B','40'],['C','60']]):
        tr={'role':'TR','children':[]};table['children'].append(tr)
        for ci,value in enumerate(row):
            x=58+ci*240;y=520-ri*68
            c.setFillColor('#5B478B' if ri==0 else '#FFFFFF');c.rect(x,y-20,240,68,fill=1,stroke=0)
            def paint(value=value,x=x,y=y,ri=ri):
                c.setFont('TestArialBold' if ri==0 else 'TestArial',22);c.setFillColor('#FFFFFF' if ri==0 else '#202138');c.drawString(x+18,y,value)
            tr['children'].append(mark('TD',paint))
    table_ids={leaf['mcid'] for row in table['children'] for leaf in row['children']}
    finish(6);pages[-1]['order']=[i for i in pages[-1]['items'] if i['mcid'] not in table_ids]+[table]
    header(7,'Hierarquia de títulos quebrada',role='H3')
    text('Este título pula do nível 1 para o nível 3.',520);finish(7)
    # Every visible character on this page is baked into the image.
    current=[]
    scan=Image.new('RGB',(1190,1684),'#FAF7F3');draw=ImageDraw.Draw(scan)
    sf=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',44);sb=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',60)
    for point,value,font,color in [((116,105),'ENTRELINHAS / CASO 08',sf,'#5B478B'),((116,195),'Texto apenas na imagem',sb,'#202138'),((116,600),'Atividade: descreva o ciclo da água.',sf,'#202138'),((116,690),'Explique a evaporação e a chuva.',sf,'#202138'),((116,1520),'Documento com barreiras intencionais',sf,'#5B478B')]:draw.text(point,value,fill=color,font=font)
    mark('Figure',lambda:c.drawImage(ImageReader(scan),0,0,W,H),'Página digitalizada com uma atividade sobre o ciclo da água.')
    pages.append({'items':list(current),'order':None});c.showPage()
    header(9,'Ordem de leitura invertida')
    first=text('1. Primeiro, observe o gráfico e anote A.',540)
    second=text('2. Depois, compare A com B e conclua.',450)
    order=[i for i in current if i not in [first,second]]+[second,first];finish(9,order)
    header(10,'Página de comparação')
    text('Texto legível, com fonte de 22 pontos.',620)
    figure('Gráfico de barras com os valores A: 20, B: 40 e C: 60. Os dados são fictícios.');finish(10)
    c.save();writer=PdfWriter();writer.clone_document_from_reader(PdfReader(BytesIO(stream.getvalue())))
    tree=DictionaryObject({NameObject('/Type'):NameObject('/StructTreeRoot')});tree_ref=writer._add_object(tree)
    document=DictionaryObject({NameObject('/Type'):NameObject('/StructElem'),NameObject('/S'):NameObject('/Document'),NameObject('/P'):tree_ref})
    document_ref=writer._add_object(document);sections=[];numbers=[]
    for pi,spec in enumerate(pages):
        page=writer.pages[pi];page[NameObject('/StructParents')]=NumberObject(pi);page[NameObject('/Tabs')]=NameObject('/S')
        section=DictionaryObject({NameObject('/Type'):NameObject('/StructElem'),NameObject('/S'):NameObject('/Sect'),NameObject('/P'):document_ref,NameObject('/Pg'):page.indirect_reference})
        section_ref=writer._add_object(section);sections.append(section_ref);parents=[None]*len(spec['items'])
        def node(item,parent):
            el=DictionaryObject({NameObject('/Type'):NameObject('/StructElem'),NameObject('/S'):NameObject('/'+item['role']),NameObject('/P'):parent,NameObject('/Pg'):page.indirect_reference})
            ref=writer._add_object(el)
            if 'children' in item:el[NameObject('/K')]=ArrayObject([node(child,ref) for child in item['children']])
            else:
                el[NameObject('/K')]=NumberObject(item['mcid']);parents[item['mcid']]=ref
                if 'alt' in item:el[NameObject('/Alt')]=TextStringObject(item['alt'])
            return ref
        section[NameObject('/K')]=ArrayObject([node(item,section_ref) for item in spec['order'] or spec['items']])
        numbers.extend([NumberObject(pi),ArrayObject(parents)])
    document[NameObject('/K')]=ArrayObject(sections);tree[NameObject('/K')]=document_ref
    tree[NameObject('/ParentTree')]=writer._add_object(DictionaryObject({NameObject('/Nums'):ArrayObject(numbers)}))
    tree[NameObject('/ParentTreeNextKey')]=NumberObject(len(pages))
    writer.root_object[NameObject('/StructTreeRoot')]=tree_ref;writer.root_object[NameObject('/Lang')]=TextStringObject('pt-BR')
    writer.root_object[NameObject('/MarkInfo')]=DictionaryObject({NameObject('/Marked'):BooleanObject(True)})
    writer.write(TARGET)
    context={'discipline':'Teste de acessibilidade','activity':'Material de exemplo','needs':'Leitura ampliada e descrições de imagens. Preferência de fonte: 20 pt.','technology':'Leitor de tela e ampliação','min_font':20}
    result=analyzer.analyze(TARGET,dict(context));(OUT/'Resultado_Real.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    cases=[('Contraste','Alerta automático: branco sobre amarelo, cerca de 1,07:1.'),('Fonte','Alerta automático: texto de 9 pt abaixo da preferência de 20 pt.'),('Imagem sem descrição','Alerta automático de ausência de descrição na imagem e na tag Figure.'),('Descrição genérica','Alerta automático para imagem_01.png.'),('Descrição incorreta','Conferência humana: a imagem é um gráfico; a descrição fala de um cachorro. O site não reconhece o significado de fotografias sem revisão.'),('Tabela sem cabeçalhos','Alerta automático de Table sem TH.'),('Hierarquia de títulos','Alerta automático de salto de H1 para H3.'),('Texto digitalizado','Alerta de página sem texto extraível. O OCR real aguarda instalação neste computador.'),('Ordem de leitura','Conferência humana: as tags colocam a etapa 2 antes da etapa 1. A revisão geral de estrutura continua necessária.'),('Página de comparação','Nenhum ponto de atenção previsto para fonte, contraste ou ausência de descrição. A descrição ainda pede conferência de sentido.')]
    lines=['# Gabarito do teste de acessibilidade','','Arquivo: Teste_Acessibilidade_10_Paginas.pdf. São 10 páginas; as barreiras foram inseridas intencionalmente. A última é uma página de comparação.','',
           'Use disciplina **Teste de acessibilidade**, atividade **Material de exemplo**, necessidades **Leitura ampliada e descrição de imagens**, tecnologia **Leitor de tela e ampliação** e fonte mínima **20 pt**. O parâmetro é deste teste, não um mínimo universal.','',
           '| Página | Caso | Resultado esperado |','|---|---|---|']
    lines += [f'| {i+1} | {title} | {expected} |' for i,(title,expected) in enumerate(cases)]
    lines += ['','Uma barreira pode produzir mais de um apontamento. O PDF tem estrutura técnica para permitir testar descrições e tags por página. As páginas 5 e 9 exigem conferência humana, mesmo quando a estrutura existe.','',
              '## Resultado do motor atual','']
    for i in range(10):
        issues=[item for item in result['issues'] if item['page']==i]
        lines.append(f"- Página {i+1}: "+('; '.join(item['title'] for item in issues) or 'nenhum apontamento específico de página')+'.')
    (OUT/'Gabarito.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    render=ROOT/'.runtime/fixture-preview';render.mkdir(exist_ok=True)
    thumbs=[]
    with pdfium.PdfDocument(TARGET) as pdf:
        for index in range(len(pdf)):
            page=pdf[index];bitmap=page.render(scale=1.3);image=bitmap.to_pil().convert('RGB').copy();image.save(render/f'pagina-{index+1:02}.png');bitmap.close();page.close()
            image.thumbnail((300,425));thumbs.append(image)
    sheet=Image.new('RGB',(5*320,2*455),'#DDD7DF')
    for index,image in enumerate(thumbs):sheet.paste(image,((index%5)*320+10,(index//5)*455+10))
    sheet.save(render/'todas-as-paginas.png')
    print(json.dumps({'pdf':str(TARGET),'pages':len(pages),'counts':result['counts'],'per_page':{str(i+1):[j['rule'] for j in result['issues'] if j['page']==i] for i in range(10)}},ensure_ascii=False))

if __name__=='__main__':make()
