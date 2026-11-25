"""Access priorities based on declared use, not on a diagnosis."""
import re
import unicodedata

CHANNELS={'visual':'Leitura visual ampliada','speech':'Leitor de tela com voz','braille':'Linha Braille','unknown':'A confirmar com o estudante'}
TOOLS={'nvda':'NVDA','jaws':'JAWS','voiceover':'VoiceOver','talkback':'TalkBack','orca':'Orca','narrator':'Narrador do Windows','zoomtext':'ZoomText','fusion':'Fusion','os_magnifier':'Lupa do sistema','browser_zoom':'Zoom do navegador','braille_display':'Linha Braille','other':'Outro recurso','unknown':'Ainda não sei'}

def validate_preferences(value):
    """Explicit choices are authoritative; old free-text profiles remain readable."""
    if not isinstance(value,dict) or set(value)-{'channels','tools','image_scale','visible_caption'}:
        raise ValueError('Confira as preferências de acesso do estudante.')
    result={}
    for key,allowed in (('channels',CHANNELS),('tools',TOOLS)):
        items=value.get(key)
        if not isinstance(items,list) or not items or len(items)>len(allowed) or any(not isinstance(i,str) or i not in allowed for i in items):
            raise ValueError('Selecione como o estudante acessa o material e os recursos que utiliza.')
        if 'unknown' in items and len(set(items))>1:
            raise ValueError('Use “Ainda não sei” somente quando não houver outra opção selecionada.')
        result[key]=list(dict.fromkeys(items))
    scale=value.get('image_scale',1)
    if type(scale) not in (int,float) or scale not in (1,1.25,1.5,2):
        raise ValueError('Escolha uma ampliação de imagem válida.')
    caption=value.get('visible_caption','auto')
    if caption not in ('auto','yes','no'):
        raise ValueError('Escolha uma preferência de legenda válida.')
    result.update(image_scale=scale,visible_caption=caption)
    return result

def legacy_detect(context):
    text=' '.join(str(context.get(k,'')) for k in ('technology','needs')).lower()
    text=''.join(c for c in unicodedata.normalize('NFKD',text) if not unicodedata.combining(c))
    # Ignore explicitly negated phrases instead of treating them as preferences.
    text=re.sub(r'\b(?:nao (?:usa|utiliza|precisa de)|sem)\s+(?:leitor de tela|ampliador(?: de tela)?|nvda|jaws|voiceover|ampliacao)\b','',text)
    reader=bool(re.search(r'\b(nvda|jaws|voiceover|talkback|orca|braille|narrador)\b|leitor(?:es)? de tela',text))
    zoom=bool(re.search(r'baixa visao|ampli(?:a|ad)|\bzoom\b|fonte (?:grande|maior)|zoomtext|fusion|lupa',text))
    return {'screen_reader':reader,'magnification':zoom,
            'label':'Leitura ampliada e leitor de tela' if reader and zoom else 'Leitor de tela' if reader else 'Leitura ampliada' if zoom else 'Acesso a confirmar'}

def detect(context):
    preferences=context.get('access_preferences')
    if preferences is None:
        return {**legacy_detect(context),'source':'legacy','braille':False,'image_scale':1,'visible_caption':None,'tools':[],'checks':[]}
    p=validate_preferences(preferences);channels=p['channels']
    reader='speech' in channels or 'braille' in channels
    visual='visual' in channels
    checks=[]
    for tool in p['tools']:
        name=TOOLS[tool]
        if tool in {'nvda','jaws','voiceover','talkback','orca','narrator','fusion'} and reader:
            checks.append({'tool':name,'text':'Abra o arquivo com '+name+' no aplicativo usado pelo estudante. Confira títulos, sequência de leitura, tabelas e descrições de imagens.'})
        if tool in {'zoomtext','fusion','os_magnifier','browser_zoom'} and visual:
            checks.append({'tool':name,'text':'Abra o arquivo com '+name+' na ampliação usada pelo estudante. Confira se textos e imagens continuam legíveis, sem cortes ou sobreposições.'})
    if 'braille' in channels:
        checks.append({'tool':'Linha Braille','text':'Com o leitor de tela e a linha Braille utilizados pelo estudante, confira textos, tabelas e símbolos. Fórmulas podem exigir preparação específica; o site não faz transcrição Braille.'})
    if 'unknown' in channels or 'unknown' in p['tools'] or 'other' in p['tools']:
        checks.append({'tool':'Confirmar recurso de acesso','text':'Confirme com o estudante ou com o AEE como ele lê os materiais e teste o arquivo com esse recurso.'})
    if not checks:
        checks.append({'tool':'Testar o material','text':'Confira o arquivo no aplicativo e com os recursos que o estudante realmente utiliza.'})
    return {'screen_reader':reader,'magnification':visual,'braille':'braille' in channels,'source':'explicit',
            'label':' + '.join(CHANNELS[c] for c in channels),'tools':[TOOLS[t] for t in p['tools']],
            'image_scale':p['image_scale'],'visible_caption':visual if p['visible_caption']=='auto' else p['visible_caption']=='yes','checks':checks}

def personalize(issues,access):
    """Prioritize the declared reading channels without hiding other findings."""
    for issue in issues:
        rule=issue['rule']
        visual=rule in {'contrast','font_size','contrast_unknown','font_unknown'}
        structure=rule.startswith('pdf_') or rule in {'slide_title','table_review','image_only','ocr_review'}
        image=rule.startswith('alt_') or rule in {'image_review','pdf_figure_alt'}
        priority=(visual and access['magnification']) or ((structure or image) and access['screen_reader']) or (image and access['magnification'])
        issue['access_priority']=bool(priority)
        if access.get('braille') and image:
            issue['explanation']+=' Na linha Braille, o acesso à informação da imagem depende de uma descrição em texto.'
        if access.get('braille') and rule=='pdf_structure_review':
            issue['suggestion']='Leia a página com o leitor de tela e a linha Braille usados pelo estudante. Confira se títulos, textos e descrições seguem a sequência correta, sem omissões ou repetições. Se houver erro, corrija no editor original.'
    if access.get('source')=='explicit':
        def rank(issue):
            if not issue['access_priority']:return 2
            if access['magnification'] and not access['screen_reader']:
                return 0 if issue['rule'] in {'contrast','font_size','contrast_unknown','font_unknown'} else 1
            return 0
        issues.sort(key=rank)
    for index,issue in enumerate(issues):issue['number']=index+1

def explain(issue,access):
    rule=issue['rule']
    if rule.startswith('alt_') or rule in {'image_review','pdf_figure_alt'}:
        if rule=='alt_quality':
            issue['explanation']='A descrição já existe. Confira se ela explica o que o aluno precisa saber para fazer a atividade.'
            issue['suggestion']='Leia a descrição e compare com a imagem. Complete os dados que faltarem.' if access['screen_reader'] else 'Confira se a descrição está clara. Se necessário, ajuste a legenda e o tamanho da imagem.'
        elif access['screen_reader'] and access['magnification']:
            issue['explanation']='O aluno combina leitura visual e leitor de tela. A imagem precisa de descrição em texto e pode precisar de ampliação e legenda para a leitura visual.'
            issue['suggestion']='Descreva os dados importantes da imagem. Se necessário, amplie e acrescente uma legenda visível.'
        elif access['magnification']:
            issue['explanation']='Com leitura ampliada, detalhes da imagem podem ficar difíceis de ver. Uma imagem maior e uma legenda ajudam a acompanhar a atividade.'
            issue['suggestion']='Amplie a imagem se os detalhes estiverem pequenos e escreva uma legenda com a informação principal.'
        elif access.get('source')=='explicit' and not access['screen_reader']:
            issue['explanation']='Esta imagem precisa de uma descrição. Confirme com o estudante como ele acessa esse conteúdo.'
            issue['suggestion']='Descreva a informação importante para a atividade. Depois confirme se ele precisa de ampliação, legenda ou descrição para leitor de tela.'
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
