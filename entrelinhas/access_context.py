"""Access priorities based on declared use, not on a diagnosis."""
import re
import unicodedata

def detect(context):
    text=' '.join(str(context.get(k,'')) for k in ('technology','needs')).lower()
    text=''.join(c for c in unicodedata.normalize('NFKD',text) if not unicodedata.combining(c))
    # Ignore explicitly negated phrases instead of treating them as preferences.
    text=re.sub(r'\b(?:nao (?:usa|utiliza|precisa de)|sem)\s+(?:leitor de tela|ampliador(?: de tela)?|nvda|jaws|voiceover|ampliacao)\b','',text)
    reader=bool(re.search(r'\b(nvda|jaws|voiceover|talkback|orca|braille|narrador)\b|leitor(?:es)? de tela',text))
    zoom=bool(re.search(r'baixa visao|ampli(?:a|ad)|\bzoom\b|fonte (?:grande|maior)|zoomtext|fusion|lupa',text))
    return {'screen_reader':reader,'magnification':zoom,
            'label':'Leitura ampliada e leitor de tela' if reader and zoom else 'Leitor de tela' if reader else 'Leitura ampliada' if zoom else 'Acesso a confirmar'}

def explain(issue,access):
    rule=issue['rule']
    if rule.startswith('alt_') or rule in {'image_review','pdf_figure_alt'}:
        if rule=='alt_quality':
            issue['explanation']='A descrição já existe. Confira se ela explica o que o aluno precisa saber para fazer a atividade.'
            issue['suggestion']='Leia a descrição e compare com a imagem. Complete os dados que faltarem.' if access['screen_reader'] else 'Confira se a descrição está clara. Se necessário, ajuste a legenda e o tamanho da imagem.'
        elif access['screen_reader'] and access['magnification']:
            issue['explanation']='O aluno usa ampliação e leitor de tela. A imagem precisa de uma descrição para ser ouvida e pode precisar de ampliação e legenda para a leitura visual.'
            issue['suggestion']='Descreva os dados importantes da imagem. Se necessário, amplie e acrescente uma legenda visível.'
        elif access['magnification']:
            issue['explanation']='Com leitura ampliada, detalhes da imagem podem ficar difíceis de ver. Uma imagem maior e uma legenda ajudam a acompanhar a atividade.'
            issue['suggestion']='Amplie a imagem se os detalhes estiverem pequenos e escreva uma legenda com a informação principal.'
        else:
            issue['explanation']='Sem uma descrição, o leitor de tela não informa o que esta imagem mostra.' if not rule=='alt_quality' else 'A descrição já existe. Confira se ela explica o que o aluno precisa saber para fazer a atividade.'
            issue['suggestion']='Descreva as informações importantes para a atividade. Em gráficos, inclua as categorias e os valores. A imagem será mantida.'
    elif rule=='contrast':
        issue['explanation']='O texto e o fundo têm cores muito parecidas. Isso pode dificultar a leitura.'
        issue['suggestion']='Escolha uma cor que destaque o texto do fundo e salve para conferir o resultado.'
    elif rule=='font_size':
        issue['explanation']='Este trecho usa uma fonte menor que o tamanho informado para o aluno.'
        issue['suggestion']='Escolha o tamanho abaixo e salve. Confira se o texto continua cabendo na página.'
    elif rule=='slide_title':
        issue['explanation']='O slide não tem um título identificado. Isso dificulta encontrar o assunto durante a navegação.'
        issue['suggestion']='Escreva um título curto para este slide.'
    elif rule=='pdf_language_missing':
        issue['explanation']='O idioma não foi definido. O leitor de tela pode pronunciar as palavras de forma incorreta.'
        issue['suggestion']='Informe o idioma do texto. Use pt-BR para português do Brasil.'
    elif rule=='pdf_heading_skip':
        heading=issue.get('heading_context',{});level=heading.get('level');previous=heading.get('previous_level')
        issue['explanation']=(f'Este trecho está marcado como Título {level}, mas vem depois de um Título {previous}, pulando um nível.' if previous else f'O primeiro título está marcado como Título {level}. A sequência deve começar no Título 1.')+' Isso atrapalha a navegação pelo leitor de tela.'
        issue['suggestion']=f'Se este trecho é uma subdivisão do anterior, use Título {heading.get("suggested_level",1)}. A alteração organiza a leitura, sem mudar a aparência do texto.' if previous else 'Use Título 1 para iniciar a hierarquia. A aparência do texto será mantida.'
    elif rule in {'table_review','pdf_table_headers'}:
        issue['explanation']='Confira os nomes das colunas. Eles ajudam o leitor de tela a relacionar cada valor ao seu significado.'
        issue['suggestion']='Marque a primeira linha como cabeçalho somente se ela tiver os nomes das colunas.'
    elif rule=='pdf_structure_review':
        issue['title']='Conferir a sequência de leitura'
        issue['explanation']='O leitor de tela usa marcações internas do PDF, chamadas tags, para saber o que ler primeiro. Elas existem neste arquivo, mas o site não consegue confirmar se a leitura segue a ordem certa.'
        issue['suggestion']='Ouça a página com um leitor de tela e confira se títulos, textos e imagens aparecem na ordem certa, sem pular ou repetir trechos. Se estiver tudo certo, marque como resolvido. Se a ordem estiver errada, ajuste no editor original.'
    elif rule in {'pdf_structure','pdf_tags_empty'}:
        issue['title']='PDF sem organização para o leitor de tela'
        issue['explanation']='O PDF não tem marcações internas utilizáveis, chamadas tags, que identificam títulos, textos e imagens. Sem elas, o leitor de tela pode ler o conteúdo em uma ordem confusa.'
        issue['suggestion']='No programa em que o material foi criado, organize os títulos e exporte o PDF com a opção de acessibilidade ativada. Depois envie a nova versão para conferir.'
    elif rule=='pdf_text_untagged':
        issue['title']='Texto fora da sequência de leitura'
        issue['explanation']='Parte do texto desta página não está ligada às marcações internas do PDF, chamadas tags. O leitor de tela pode pular esse conteúdo ou lê-lo fora de ordem.'
        issue['suggestion']='Confira a leitura desta página com um leitor de tela. Se houver trechos pulados ou fora de ordem, corrija no editor original e exporte o PDF com acessibilidade.'
    elif not issue.get('action'):
        issue['suggestion']='Este ponto exige revisão no editor original. Depois, envie o arquivo em “Testar nova versão”.'
