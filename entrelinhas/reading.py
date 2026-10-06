"""Editable companion reading document; never relabels the source as repaired."""
from html import escape

ROLES={'p','h1','h2','h3','figure','decorative'}

def initial(job):
    items=[]
    for page in job['analysis']['pages']:
        for block in page['blocks']:
            if block['type']=='text' and block.get('text','').strip():
                items.append({'id':block['id'],'text':block['text'],'role':'h2' if block.get('heading') else 'p','confirmed':False,'page':page['label']})
            elif block.get('image'):
                items.append({'id':block['id'],'text':block.get('alt','') or '', 'role':'decorative' if block.get('decorative') else 'figure','confirmed':False,'page':page['label']})
    return {'items':items,'language':'pt-BR','title':job['filename'],'reviewed':False}


def validate(job,value):
    from analyzer import MaterialError
    if not isinstance(value,dict) or not isinstance(value.get('items'),list):raise MaterialError('Confira os trechos da versão de leitura.')
    known={i['id']:i for i in initial(job)['items']};items=value['items']
    if len(items)!=len(known) or len(items)>5000:raise MaterialError('Mantenha todos os trechos identificados; marque como decorativo apenas imagens sem informação.')
    seen=set();result=[]
    images={b['id'] for p in job['analysis']['pages'] for b in p['blocks'] if b.get('image')}
    for item in items:
        if not isinstance(item,dict):raise MaterialError('Trecho inválido.')
        identity=item.get('id');text=item.get('text');role=item.get('role')
        if identity not in known or identity in seen or role not in ROLES or not isinstance(text,str) or len(text)>10000:raise MaterialError('Confira a identificação, o tipo e o texto de cada trecho.')
        if (identity in images)!=(role in {'figure','decorative'}):raise MaterialError('Mantenha o tipo de conteúdo do trecho.')
        if role!='decorative' and not text.strip():raise MaterialError('Preencha o texto ou a descrição dos trechos.')
        seen.add(identity);result.append(dict(known[identity],text=text.strip(),role=role,confirmed=item.get('confirmed') is True))
    language=value.get('language','pt-BR');title=value.get('title',job['filename'])
    import re
    if not isinstance(language,str) or not re.fullmatch(r'[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8})*',language):raise MaterialError('Informe um idioma como pt-BR.')
    if not isinstance(title,str) or not title.strip() or len(title)>180:raise MaterialError('Informe um título com até 180 caracteres.')
    return {'items':result,'language':language,'title':title.strip(),'reviewed':bool(result) and all(i['confirmed'] for i in result)}


def render(job):
    doc=job.get('reading') or initial(job)
    originals={b['id']:b for p in job['analysis']['pages'] for b in p['blocks']}
    e=lambda s:escape(str(s),quote=True)
    parts=[]
    for item in doc['items']:
        role=item['role'];text=e(item['text'])
        if role=='decorative':continue
        if role=='figure':
            image=originals[item['id']].get('image','')
            parts.append(f'<figure><img src="{e(image)}" alt="{text}"><figcaption>{text}</figcaption></figure>')
        else:parts.append(f'<{role}>{text}</{role}>')
    pending='' if doc.get('reviewed') else '<p class="notice">Texto e ordem de leitura aguardam conferência do professor.</p>'
    return f'''<!doctype html><html lang="{e(doc['language'])}"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(doc['title'])}</title>
<style>body{{font:1.2rem/1.65 Arial,sans-serif;background:#fff;color:#111;max-width:50rem;margin:2rem auto;padding:0 1.2rem}}p{{white-space:pre-wrap}}img{{max-width:100%;height:auto}}h1,h2,h3{{line-height:1.25}}.notice{{padding:1rem;border:2px solid #333}}button{{font:inherit}}@media print{{.tools{{display:none}}}}</style>
<main><h1>{e(doc['title'])}</h1>{pending}{''.join(parts)}</main></html>'''.encode('utf-8')
