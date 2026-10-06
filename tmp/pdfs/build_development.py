from pathlib import Path
from html import escape
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Flowable
from reportlab.lib.enums import TA_LEFT

ROOT = Path(r'C:\Users\Lucas\Documents\Produto Empreendedorismo')
OUT = ROOT / 'output' / 'pdf'
OUT.mkdir(parents=True, exist_ok=True)
PDF = OUT / 'Desenvolvimento_do_Produto_Preenchido.pdf'
MD = ROOT / 'output' / 'Planejamento_Desenvolvimento_do_Produto.md'

pdfmetrics.registerFont(TTFont('Arial', r'C:\Windows\Fonts\arial.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Bold', r'C:\Windows\Fonts\arialbd.ttf'))
pdfmetrics.registerFontFamily('Arial', normal='Arial', bold='Arial-Bold', italic='Arial', boldItalic='Arial-Bold')
NAVY = colors.HexColor('#24264F')
TEAL = colors.HexColor('#126665')
INK = colors.HexColor('#202534')
MUTED = colors.HexColor('#536070')
PALE = colors.HexColor('#F0F4F7')
LINE = colors.HexColor('#D5DCE4')
ORANGE = colors.HexColor('#9B4510')
WIDTH = A4[0] - 84

styles = {
    'body': ParagraphStyle('body', fontName='Arial', fontSize=10.4, leading=14.6, textColor=INK, spaceAfter=7),
    'small': ParagraphStyle('small', fontName='Arial', fontSize=9.2, leading=12.5, textColor=MUTED, spaceAfter=6),
    'cell': ParagraphStyle('cell', fontName='Arial', fontSize=10, leading=13.5, textColor=INK),
    'matrix': ParagraphStyle('matrix', fontName='Arial', fontSize=9.1, leading=12.4, textColor=INK),
    'label': ParagraphStyle('label', fontName='Arial-Bold', fontSize=9.8, leading=13.2, textColor=NAVY),
    'white': ParagraphStyle('white', fontName='Arial-Bold', fontSize=9.6, leading=13, textColor=colors.white),
    'h1': ParagraphStyle('h1', fontName='Arial-Bold', fontSize=21, leading=26, textColor=NAVY, spaceAfter=12),
    'h2': ParagraphStyle('h2', fontName='Arial-Bold', fontSize=12.4, leading=16, textColor=TEAL, spaceBefore=10, spaceAfter=7),
    'eyebrow': ParagraphStyle('eyebrow', fontName='Arial-Bold', fontSize=9.4, leading=13, textColor=TEAL, spaceAfter=8),
}

problem = ('Professores do ensino médio regular nem sempre recebem formação específica para reconhecer e corrigir '
           'barreiras de acessibilidade em documentos, slides, atividades e avaliações. A falta de conhecimento, '
           'familiaridade e tempo dificulta a preparação desses materiais. O problema central do projeto é a '
           'dificuldade de integrar, com qualidade, os conteúdos escolares às tecnologias assistivas utilizadas '
           'pelos estudantes cegos e com baixa visão.')
user = 'Professor do ensino médio regular. Beneficiário final: estudante cego ou com baixa visão.'
value = ('Ajudar o professor a preparar materiais mais acessíveis, compreender as barreiras e suas correções e '
         'ganhar autonomia e rapidez ao longo do trabalho. O aprendizado é um benefício esperado, sem atribuição '
         'de notas ao professor ou medição obrigatória de seu aprendizado.')
inputs = [
    ('Disciplina', 'Área em que o material será utilizado.'),
    ('Tipo de atividade', 'Prova, atividade, tarefa de sala, material de estudo ou apresentação.'),
    ('Necessidades do estudante', 'Informações conhecidas pelo professor sobre como o estudante acessa os conteúdos.'),
    ('Tecnologias assistivas', 'Recursos que o estudante efetivamente utiliza; não são deduzidos pelo arquivo.'),
]
scope = ('Documentos de texto e apresentações são as duas categorias principais: PDF, arquivos do Word '
         '(prioritariamente DOCX) e PowerPoint (PPTX). Imagens inseridas nesses materiais fazem parte da análise. '
         'Imagens enviadas separadamente e páginas digitalizadas integram o escopo planejado; a cobertura de '
         'formatos e funções será desenvolvida e verificada por etapas.')

concepts = [
    {
        'name': 'Verificador educativo de materiais',
        'problem': 'Dificuldade de perceber as barreiras do material e compreender por que prejudicam o acesso ao conteúdo.',
        'user': user,
        'value': 'Oferecer um diagnóstico explicado e um relatório que ajudem o professor a reconhecer os problemas e aprender a corrigi-los.',
        'how': 'O professor envia o arquivo e o contexto mínimo. A plataforma identifica possíveis barreiras, localiza os problemas e explica suas consequências. O professor corrige no programa original e pode reenviar uma nova versão.',
        'features': 'Análise contextualizada; localização dos problemas; explicações e recomendações; relatório para baixar; acompanhamento da nova versão.',
        'difference': 'Organizar a verificação em torno do estudante e da atividade escolar, com linguagem educativa e orientações para preparar os próximos materiais.',
        'notes': 'A correção ocorre principalmente fora da plataforma. Favorece um começo com diagnóstico e relatório, mantendo o professor responsável pela revisão.',
        'representation': 'Arquivo e contexto -> diagnóstico explicado -> relatório -> correção externa -> nova verificação. Esboço de tela: lista de problemas por localização, explicação e recomendação.',
        'mode': 'report',
    },
    {
        'name': 'Assistente de adaptação guiada',
        'problem': 'Dificuldade de transformar o diagnóstico em uma correção prática e verificar se as alterações resolveram as barreiras.',
        'user': user,
        'value': 'Acompanhar o professor na revisão, permitindo compreender, corrigir e conferir os problemas no próprio fluxo de trabalho.',
        'how': 'Após enviar arquivo e contexto, o professor escolhe a visualização. Pode corrigir os elementos compatíveis na plataforma ou editar o arquivo original e reenviá-lo. A análise da versão revisada mostra problemas resolvidos, pendentes e novos.',
        'features': 'Original e versão marcada lado a lado; revisão de um problema por vez; relatório geral; correção orientada; histórico e comparação entre versões.',
        'difference': 'Conectar a explicação ao ponto exato do material e acompanhar a revisão pelo professor, respeitando a finalidade pedagógica e o perfil do estudante.',
        'notes': 'É a base do conceito geral. Edição, localização e comparação dependem do formato; funções sem suporte precisam ser informadas claramente ao professor.',
        'representation': 'Original | versão com marcações; ao selecionar um problema, abrir explicação, sugestão e ação de correção. Alternativamente, conduzir o professor por uma barreira de cada vez.',
        'mode': 'guided',
    },
    {
        'name': 'Adaptador assistido de materiais',
        'problem': 'Falta de tempo para realizar adaptações, especialmente quando há várias barreiras ou materiais a preparar.',
        'user': user,
        'value': 'Propor uma versão adaptada com mais rapidez, mantendo as explicações e a aprovação do professor.',
        'how': 'O professor fornece o material e o contexto e solicita a adaptação. A plataforma sugere alterações ou gera uma versão revisada, registra o que mudou e apresenta itens que exigem revisão. O professor confere e aprova antes do uso.',
        'features': 'Geração opcional de adaptações; comparação entre original e proposta; explicações das mudanças; revisão e aprovação pelo professor; verificação posterior.',
        'difference': 'Combinar a assistência à adaptação com o contexto escolar, o perfil do estudante e a preservação do objetivo da atividade.',
        'notes': 'É um recurso adicional. A automação não deve alterar a exigência da avaliação nem entregar respostas ao estudante. A abrangência depende da validação de cada tipo de alteração.',
        'representation': 'Original e contexto -> solicitar adaptação -> versão proposta e explicações -> revisão do professor -> verificação e aprovação.',
        'mode': 'auto',
    },
]

criteria = [
    ('Qualidade da acessibilidade', 'Adequação ao estudante, às suas tecnologias assistivas e ao objetivo da atividade.',
     'Identifica barreiras e orienta; a melhoria depende da correção externa e da verificação posterior.',
     'Conecta diagnóstico, correção e nova verificação; favorece acompanhar a melhoria do material.',
     'Propõe adaptações; a qualidade depende da precisão das alterações e da revisão do professor.'),
    ('Aprendizado e autonomia', 'Potencial da proposta para apoiar a compreensão e a ação independente do professor.',
     'Explicações podem ajudar o professor a reconhecer e evitar erros nos próximos materiais.',
     'Explicação e prática de correção ficam próximas; o professor participa das decisões.',
     'Explicações ficam disponíveis, mas o uso automático exige cuidado para manter a participação do professor.'),
    ('Facilidade de uso', 'Clareza das etapas, localização dos problemas e esforço para concluir a revisão.',
     'Fluxo mais enxuto, com relatório; exige alternar com o programa de edição.',
     'Oferece três modos e revisão localizada; a interface precisa manter essa variedade compreensível.',
     'Reduz ações manuais, mas exige uma forma clara de revisar e aprovar as alterações.'),
    ('Rapidez', 'Tempo e retrabalho para analisar, corrigir e verificar uma nova versão.',
     'Concentra os problemas em um relatório; a correção permanece manual.',
     'Revisão por problema e acompanhamento das versões podem reduzir retrabalho.',
     'Pode acelerar alterações apoiadas; revisão e casos complexos continuam necessários.'),
    ('Viabilidade de implementação', 'Funções necessárias para construir e manter a solução com os recursos disponíveis.',
     'Requer importação, verificações, explicações e relatório; concentra um conjunto inicial de funções.',
     'Acrescenta marcações, edição e comparação de versões; exige desenvolvimento por formato.',
     'Acrescenta geração e exportação das adaptações; exige validação técnica e pedagógica de cada função.'),
]
synthesis = ('O verificador educativo fornece a base de diagnóstico e explicação. O assistente de adaptação guiada '
             'é o núcleo escolhido para integrar análise, participação do professor e revisão das versões. O adaptador '
             'assistido será uma opção complementar para tarefas em que a automação possa ser revisada com segurança. '
             'Assim, a escolha final reúne as contribuições dos três conceitos, com desenvolvimento por etapas.')
general = ('Plataforma web de análise e adaptação orientada de documentos didáticos para estudantes cegos e com '
           'baixa visão. O professor informa o contexto da atividade e as necessidades e tecnologias assistivas do '
           'estudante. A plataforma identifica e explica barreiras, recomenda correções e permite trabalhar por '
           'visualização lado a lado, passo a passo ou relatório geral. O professor pode corrigir na plataforma ou '
           'no arquivo original, reenviar versões e acompanhar a resolução dos problemas. Uma função adicional '
           'pode propor uma versão adaptada, sujeita à revisão e aprovação do professor. A primeira versão será '
           'um site executado localmente para testes.')
justifications = [
    ('Qualidade da acessibilidade', 'A análise considera o estudante real e o uso pedagógico do material. A revisão das versões permite acompanhar se as alterações resolvem as barreiras sem mudar o objetivo da atividade.'),
    ('Aprendizado e autonomia', 'Localizar, explicar e orientar cada correção ajuda o professor a compreender seus erros e evitá-los em novos materiais. A ferramenta atua como apoio formativo temporário, sem avaliar ou dar notas ao professor.'),
    ('Facilidade de uso', 'Os três modos apresentam a mesma análise de formas diferentes, permitindo que o professor escolha a organização mais útil para seu trabalho.'),
    ('Rapidez', 'Problemas localizados, revisão orientada e comparação entre versões reduzem a repetição de etapas. A adaptação assistida oferece um caminho adicional para tarefas que precisem de maior rapidez.'),
    ('Viabilidade de implementação', 'O site local permite testar o fluxo com o grupo e ampliar a avaliação. Importação, verificações, edição e adaptação serão implementadas progressivamente, com cobertura explícita para cada formato.'),
]
features = [
    ('Contexto obrigatório', 'Solicitar disciplina, tipo de atividade, necessidades do estudante e tecnologias assistivas. Conteúdo, objetivo pedagógico e preferências detalhadas podem ser acrescentados.'),
    ('Diagnóstico contextualizado', 'Verificar barreiras relacionadas a texto, legibilidade, contraste, imagens, descrições, estrutura e leitura por tecnologias assistivas, conforme a cobertura implementada. Gráficos, tabelas e fórmulas exigem atenção ao sentido e ao objetivo pedagógico.'),
    ('Orientação para cada problema', 'Apresentar localização, evidência, motivo da barreira e sugestão de correção. Identificar itens que dependem de revisão humana.'),
    ('Três modos de trabalho', 'Original e versão marcada lado a lado; um problema por vez; relatório geral para baixar. Marcações visuais também terão identificação textual.'),
    ('Duas formas de corrigir', 'Editar elementos apoiados dentro da plataforma ou corrigir o arquivo original e reenviá-lo. Preservar o original e permitir a revisão das mudanças.'),
    ('Verificação entre versões', 'Mostrar barreiras resolvidas, pendentes e novas, com foco nas alterações e sem repetir desnecessariamente explicações já apresentadas.'),
    ('Adaptação assistida opcional', 'Propor correções ou uma versão adaptada para o professor revisar e aprovar. Preservar o conteúdo e a finalidade da atividade.'),
    ('Interface acessível', 'Planejar navegação por teclado, identificação de controles, leitura por leitor de tela, ampliação e informação compreensível sem depender somente de cores.'),
]
tests = [
    ('1. Grupo', 'Materiais de exemplo, incluindo versões com barreiras conhecidas e versões corrigidas.', 'Conferir envio, contexto, localização, explicações, três modos, relatório e reenvio de versões.'),
    ('2. Professor', 'Um professor da escola, conforme disponibilidade.', 'Verificar clareza das orientações, esforço de correção e adequação ao preparo de aulas e avaliações.'),
    ('3. Estudante cega', 'Convidar a colega da escola, conforme disponibilidade e interesse.', 'Testar o acesso aos materiais com a tecnologia assistiva que ela utiliza e identificar barreiras que a análise não apontou.'),
    ('4. Professora especialista', 'Convidar a professora com doutorado na área de acessibilidade.', 'Revisar diagnóstico, adaptações, explicações e preservação dos objetivos pedagógicos.'),
]
observations = [
    'A participação dos professores e da estudante está planejada; os convites e testes ainda serão organizados pelo grupo.',
    'Os testes com a colega representam sua experiência individual. Pretende-se ampliar a avaliação para pessoas com baixa visão e outros perfis conforme houver participantes disponíveis.',
    'Aprendizado e autonomia são benefícios e critérios do conceito. A plataforma não atribui notas ao professor nem presume seu aprendizado por uma alteração no arquivo.',
    'O primeiro produto será um site no navegador, executado localmente. Um programa instalado poderá ser considerado em uma etapa futura.',
    'O suporte a diferentes formatos, a edição no navegador e a geração de adaptações são funções planejadas, com implantação e verificação progressivas.',
]
sources = [
    ('Documento da atividade', '1as Atividades_Desenvolvimento_de_Produto_01.pdf - roteiro de conceitos, representação, comparação e fechamento fornecido pelo professor.'),
    ('Trabalho anterior do grupo', 'APRESENTACAO CONCEITO.pdf; Documento sem título-17.pdf; levantamento dos principais dados sobre o problema; apresentação sobre inclusão de estudantes com deficiência visual.'),
    ('Respostas do planejamento', 'Definições fornecidas por Lucas Santana nesta conversa, consolidadas em 05/10/2026.'),
    ('Microsoft Support', 'Rules for the Accessibility Checker', 'https://support.microsoft.com/en-us/accessibility/office-accessibility/rules-for-the-accessibility-checker'),
    ('Adobe Help', 'Create and verify PDF accessibility, Acrobat Pro', 'https://helpx.adobe.com/acrobat/using/create-verify-pdf-accessibility.html'),
]

story = []
markdown = []

def P(text, style='body'):
    return Paragraph(escape(text).replace('\n', '<br/>'), styles[style])

def heading(title, eyebrow=None, newpage=False):
    if newpage:
        story.append(PageBreak())
    if eyebrow:
        story.append(P(eyebrow.upper(), 'eyebrow'))
    story.append(P(title, 'h1'))
    markdown.extend(['', '# ' + title, ''])

def para(text, style='body'):
    story.append(P(text, style))
    markdown.extend([text, ''])

def sub(title):
    story.append(P(title, 'h2'))
    markdown.extend(['', '## ' + title, ''])

def keytable(rows, left=128):
    data = [[P(label, 'label'), P(text, 'cell')] for label, text in rows]
    t = Table(data, colWidths=[left, WIDTH-left], hAlign='LEFT')
    t.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('BACKGROUND',(0,0),(0,-1),PALE),
        ('LINEBELOW',(0,0),(-1,-1),0.4,LINE),
        ('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
    ]))
    story.append(t)
    story.append(Spacer(1,7))
    for label,text in rows:
        markdown.extend(['**' + label + ':** ' + text, ''])

class Wireframe(Flowable):
    def __init__(self, mode):
        Flowable.__init__(self)
        self.mode=mode
        self.width=WIDTH
        self.height=138
    def draw(self):
        c=self.canv
        w=self.width
        c.setStrokeColor(LINE);c.setFillColor(PALE)
        c.roundRect(0,0,w,132,7,fill=1,stroke=1)
        c.setFillColor(NAVY);c.roundRect(0,105,w,27,7,fill=1,stroke=0)
        c.rect(0,105,w,15,fill=1,stroke=0)
        c.setFont('Arial-Bold',10);c.setFillColor(colors.white)
        title={'report':'DIAGNÓSTICO E RELATÓRIO','guided':'REVISÃO ORIENTADA','auto':'ADAPTAÇÃO ASSISTIDA'}[self.mode]
        c.drawString(12,115,title)
        def text(x,y,s,bold=False,color=INK,size=9):
            c.setFont('Arial-Bold' if bold else 'Arial',size);c.setFillColor(color);c.drawString(x,y,s)
        def panel(x,y,pw,ph):
            c.setFillColor(colors.white);c.setStrokeColor(LINE);c.roundRect(x,y,pw,ph,4,fill=1,stroke=1)
        if self.mode=='report':
            panel(10,12,w-20,82)
            text(20,79,'Problema 01 | Imagem sem descrição',True)
            text(20,62,'Localização: página 2. A informação visual precisa de uma alternativa textual.')
            text(20,46,'Ação: descrever o conteúdo necessário para realizar a atividade.')
            text(20,26,'Baixar relatório',True,TEAL)
            text(235,26,'Enviar versão corrigida',True,TEAL)
        elif self.mode=='guided':
            panel(10,12,148,82);panel(168,12,148,82);panel(326,12,w-336,82)
            text(19,79,'Original',True);text(177,79,'Com marcações',True)
            for x in [20,178]:
                c.setStrokeColor(LINE);c.line(x,64,x+117,64);c.line(x,58,x+90,58)
                c.setFillColor(PALE);c.rect(x,24,117,27,fill=1,stroke=0)
                text(x+8,33,'Imagem da atividade',size=8)
            c.setStrokeColor(ORANGE);c.setLineWidth(1.6);c.roundRect(175,21,123,33,4,fill=0,stroke=1)
            text(299,46,'1',True,ORANGE)
            text(337,79,'Problema 01',True)
            text(337,62,'Falta descrição.',size=8.6)
            text(337,46,'Entender e corrigir',True,TEAL,size=8.6)
            text(337,27,'Verificar nova versão',size=8.6)
        else:
            panel(10,12,153,82);panel(179,12,153,82);panel(348,12,w-358,82)
            text(20,79,'Material original',True)
            text(20,59,'Arquivo + contexto')
            text(20,35,'Solicitar adaptação',True,TEAL)
            text(189,79,'Versão proposta',True)
            text(189,59,'Alterações explicadas')
            text(189,35,'Comparar versões',True,TEAL)
            text(358,79,'Revisão',True)
            text(358,59,'Professor confere')
            text(358,35,'Aprovar',True,TEAL)
        c.setLineWidth(1)

class Flow(Flowable):
    def __init__(self, labels):
        Flowable.__init__(self)
        self.labels=labels;self.width=WIDTH;self.height=56
    def draw(self):
        c=self.canv;n=len(self.labels);gap=13;bw=(WIDTH-gap*(n-1))/n
        for i,lines in enumerate(self.labels):
            x=i*(bw+gap)
            c.setFillColor(PALE);c.setStrokeColor(LINE);c.roundRect(x,5,bw,44,4,fill=1,stroke=1)
            c.setFillColor(NAVY);c.setFont('Arial-Bold',8.3)
            for j,line in enumerate(lines):c.drawCentredString(x+bw/2,32-j*12,line)
            if i<n-1:
                c.setStrokeColor(TEAL);c.line(x+bw+3,27,x+bw+gap-3,27)
                c.line(x+bw+gap-6,30,x+bw+gap-3,27);c.line(x+bw+gap-6,24,x+bw+gap-3,27)

heading('Atividades de desenvolvimento de produto', 'Planejamento preenchido | Trabalho e Empreendedorismo')
para('Tema: Matrícula não garante inclusão. Professor: Adson Rezende. Turma: 303 - A. Planejamento consolidado em 05/10/2026.', 'small')
para('Produto: plataforma web de análise e adaptação orientada de documentos didáticos. Os nomes abaixo descrevem as possibilidades de conceito; a marca comercial ainda poderá ser definida.', 'small')
sub('Base comum aos conceitos')
keytable([('Problema/oportunidade', problem),('Usuário principal',user),('Proposta de valor',value)])
sub('Contexto mínimo fornecido pelo professor')
keytable(inputs)
para('Informações detalhadas sobre conteúdo, objetivo pedagógico e preferências do estudante são complementares. O professor precisa conhecer o estudante antes de definir as adaptações.', 'small')
sub('Materiais e forma de acesso')
para(scope)
para('Acesso pelo navegador, com execução local na primeira versão de teste. A plataforma parte do material que o professor já possui e preserva sua decisão final.')

for i,concept in enumerate(concepts,1):
    heading('Conceito ' + str(i) + ': ' + concept['name'], 'Desenvolvimento dos três conceitos', True)
    keytable([
        ('Nome do conceito',concept['name']),('Problema/oportunidade',concept['problem']),('Usuário principal',concept['user']),
        ('Proposta de valor',concept['value']),('Como funciona?',concept['how']),('Principais características',concept['features']),
        ('Principal diferencial',concept['difference']),('Observações',concept['notes'])
    ])
    sub('Representação visual pretendida')
    story.append(Wireframe(concept['mode']))
    para('Esboço ilustrativo do conceito, sem resultados de testes.', 'small')
    para(concept['representation'], 'small')

heading('Comparação dos conceitos', 'Matriz qualitativa | Cinco critérios | Sem pesos', True)
para('Comparação das características previstas para as três alternativas. As avaliações são hipóteses de projeto e serão revistas após os testes; não representam medições de desempenho já realizadas.', 'small')
matrix = [[P('Critério', 'white')]+[P('Conceito '+str(i)+'<br/>', 'white') for i in []]]
matrix = [[P('Critério','white'),P('1. Verificador educativo','white'),P('2. Adaptação guiada','white'),P('3. Adaptador assistido','white')]]
for title,definition,*values in criteria:
    matrix.append([P(title,'label')]+[P(v,'matrix') for v in values])
t=Table(matrix,colWidths=[102,(WIDTH-102)/3,(WIDTH-102)/3,(WIDTH-102)/3],hAlign='LEFT',repeatRows=1)
t.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,0),NAVY),('BACKGROUND',(0,1),(0,-1),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),
    ('GRID',(0,0),(-1,-1),0.4,LINE),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
    ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)
]))
story.append(t)
markdown.extend(['| Critério | Conceito 1 | Conceito 2 | Conceito 3 |','|---|---|---|---|'])
for title,definition,*values in criteria:markdown.append('| '+' | '.join([title]+values)+' |')
sub('Síntese da avaliação')
para(synthesis)
para('Não serão atribuídos pesos. Aprendizado e autonomia avaliam o potencial formativo do conceito; a plataforma analisa o material e não atribui notas ao professor.', 'small')

heading('Conceito geral do produto', 'Fechamento da atividade', True)
keytable([('Conceito GERAL',general)])
sub('Justificativa da conceituação geral')
for label,text in justifications:
    story.append(Paragraph('<b>'+escape(label)+'.</b> '+escape(text),styles['body']))
    markdown.extend(['**'+label+':** '+text,''])
sub('Fluxo integrado pretendido')
story.append(Flow([['Arquivo e','contexto'],['Diagnóstico','explicado'],['Corrigir ou','adaptar'],['Revisar nova','versão'],['Professor','aprova']]))
para('Fluxo: enviar arquivo e contexto -> receber diagnóstico -> corrigir ou solicitar adaptação -> verificar a versão revisada -> revisar e aprovar para o uso.', 'small')
para('A correção orientada é o caminho principal. A geração de adaptações permanece uma opção adicional para acelerar tarefas, com revisão das mudanças e preservação do objetivo pedagógico.')

heading('Funcionalidades e formas de uso', 'Detalhamento do conceito selecionado', True)
keytable(features, left=135)
sub('As três visualizações pertencem ao mesmo produto')
para('Lado a lado, passo a passo e relatório geral são formas de apresentar e trabalhar com a mesma análise. Elas não substituem os três conceitos comparados na matriz: diagnóstico educativo, correção guiada e adaptação assistida.')
para('O professor escolhe o modo mais útil. Ao receber uma segunda versão, o sistema apresenta a evolução das barreiras detectadas, mantendo os problemas identificados em texto e por localização.')

heading('Plano de testes e observações', 'Validação prevista para a primeira versão', True)
para('O teste começa com o grupo e poderá envolver outras pessoas da escola, conforme disponibilidade e interesse. Os convites serão feitos pelo próprio grupo.')
for stage,participants,purpose in tests:
    sub(stage)
    para(participants+' '+purpose)
sub('O que será observado nos testes')
para('Comparar original e versão corrigida: quais barreiras foram detectadas, quais passaram despercebidas, quais alertas não se confirmaram e quais problemas foram resolvidos. Registrar tempo de tarefa, clareza das explicações, facilidade dos três modos e acesso efetivo ao conteúdo com os recursos usados pelo estudante.')
para('A revisão da professora especialista ajudará a estabelecer referências para conferir os diagnósticos e as adaptações. O relato do estudante ajudará a verificar se o material permite compreender e realizar a atividade, preservando sua finalidade.')
sub('Observações do planejamento')
for note in observations:
    story.append(P('- '+note,'small'))
    markdown.extend(['- '+note,''])

heading('Diferencial e referências', 'Fundamentação do planejamento', True)
sub('O que já existe nas soluções consultadas')
para('A documentação do Microsoft Accessibility Checker descreve identificação de problemas em arquivos do Office, explicações e sugestões de correção [1]. A documentação do Adobe Acrobat descreve verificações de PDF, relatório, orientações de correção, nova verificação e itens que exigem conferência manual [2].')
sub('Diferencial proposto para o projeto')
para('O diferencial é combinar esses tipos de recurso em um fluxo dedicado ao professor do ensino médio: análise com contexto da atividade e necessidades do estudante; orientação pedagógica durante a correção; três formas de visualização; revisão entre versões; e adaptação assistida opcional com decisão final do professor.')
para('Essa diferenciação é uma proposta de posicionamento do produto, baseada no problema pesquisado pelo grupo. Sua utilidade deverá ser verificada nos testes. A contribuição está na organização e contextualização do fluxo, sem pressupor exclusividade de cada função isolada.', 'small')
sub('Fontes utilizadas')
for item in sources:
    if len(item)==2:
        label,text=item
        para(label+': '+text,'small')
    else:
        label,title,url=item
        num='1' if label.startswith('Microsoft') else '2'
        story.append(Paragraph('['+num+'] <b>'+escape(label)+'.</b> '+escape(title)+'. Acesso em 05/10/2026. <link href="'+url+'" color="#126665">Abrir documentação oficial</link>.',styles['small']))
        markdown.extend(['['+num+'] '+label+'. ['+title+']('+url+'). Acesso em 05/10/2026.',''])
sub('Correspondência com a entrega solicitada')
para('Conceitos desenvolvidos e refinados: páginas 2 a 4. Representação visual de cada conceito: páginas 2 a 4. Matriz de comparação e síntese: página 5. Conceito geral e justificativa: página 6. Funcionalidades e observações: páginas 7 e 8.', 'small')

def footer(canvas,doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE);canvas.line(42,39,A4[0]-42,39)
    canvas.setFillColor(MUTED);canvas.setFont('Arial',8)
    canvas.drawString(42,25,'Trabalho e Empreendedorismo | Matrícula não garante inclusão')
    canvas.drawRightString(A4[0]-42,25,str(doc.page))
    canvas.restoreState()

doc=SimpleDocTemplate(str(PDF),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=39,bottomMargin=54,
                      title='Atividades de Desenvolvimento de Produto - Planejamento preenchido',
                      author='Lucas Santana e grupo',subject='Plataforma de acessibilidade de materiais didáticos')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
MD.write_text('\n'.join(markdown).strip()+'\n',encoding='utf-8')
print(json.dumps({'pdf':str(PDF),'editable':str(MD)},ensure_ascii=False))
