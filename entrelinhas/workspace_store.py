"""Profiles and review positions, persisted beside the owner's materials."""
import json
import math
from pathlib import Path
import threading
import uuid
import access_context
from analyzer import MaterialError

LOCK = threading.RLock()

def is_example(job):
    if 'is_example' in job:
        return job['is_example'] is True
    # Recognize examples saved before this flag existed, without deleting files.
    return job.get('filename') == 'Atividade_Geografia.pptx' and job.get('analysis', {}).get('context') == {
        'discipline': 'Geografia', 'activity': 'Atividade de sala',
        'needs': 'Leitura ampliada; preferência informada de fonte de pelo menos 20 pt; acesso ao gráfico por descrição.',
        'technology': 'Ampliação de tela e leitor de tela', 'min_font': 20,
    }

def read(folder):
    path = Path(folder)/'workspace.json'
    with LOCK:
        if not path.exists():
            return {'profiles': [], 'progress': {}, 'last_job_id': None}
        return json.loads(path.read_text(encoding='utf-8'))

def write(folder, data):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    temporary = folder/'workspace.new'
    temporary.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    temporary.replace(folder/'workspace.json')

def save_profile(folder, body):
    profile = {}
    for key, limit in [('name',60),('needs',3000),('technology',3000)]:
        value = body.get(key)
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit:
            raise MaterialError('Preencha o nome, as necessidades e as tecnologias do perfil.')
        profile[key] = value.strip()
    font = body.get('min_font')
    try:
        font = float(font) if font not in (None, '') else None
    except (ValueError, TypeError):
        raise MaterialError('Informe um tamanho de fonte válido.')
    if font is not None and (not math.isfinite(font) or not 6 <= font <= 96):
        raise MaterialError('A fonte preferida deve ficar entre 6 e 96 pt.')
    profile['min_font'] = font
    if 'access_preferences' in body:
        try:profile['access_preferences']=access_context.validate_preferences(body['access_preferences'])
        except ValueError as error:raise MaterialError(str(error)) from error
    with LOCK:
        state = read(folder)
        identity = body.get('id')
        if identity and not any(p['id']==identity for p in state['profiles']):
            raise MaterialError('Perfil não encontrado.')
        if not identity and len(state['profiles']) >= 40:
            raise MaterialError('O limite é de 40 perfis salvos.')
        profile['id'] = identity or uuid.uuid4().hex
        state['profiles'] = [profile if p['id']==profile['id'] else p for p in state['profiles']] if identity else state['profiles']+[profile]
        write(folder, state)
        return profile

def remove_profile(folder, identity):
    with LOCK:
        state = read(folder)
        state['profiles'] = [p for p in state['profiles'] if p['id']!=identity]
        write(folder, state)

def can_resolve(issue):
    return issue.get('rule')=='alt_quality' or (not issue.get('action') and not issue.get('quick_image'))


def save_progress(folder, job, body):
    issues = {i['id'] for i in job['analysis']['issues']}
    pages = len(job['analysis']['pages'])
    page = body.get('page', 0)
    reviewed = body.get('reviewed', [])
    resolved = body.get('resolved', [])
    eligible = {i['id'] for i in job['analysis']['issues'] if can_resolve(i)} | set(job.get('resolved_issues',[]))
    if not isinstance(resolved,list) or len(resolved)>2000 or any(not isinstance(i,str) or i not in eligible for i in resolved):
        raise MaterialError('Resolução inválida para essa análise.')
    if isinstance(page, bool) or not isinstance(page, int) or not 0 <= page < pages:
        raise MaterialError('Página inválida para essa análise.')
    if not isinstance(reviewed, list) or len(reviewed)>2000 or any(not isinstance(i,str) or i not in issues for i in reviewed):
        raise MaterialError('Conferência inválida para essa análise.')
    selected = body.get('issue_id')
    drafts=body.get('drafts',{})
    if not isinstance(drafts,dict) or len(drafts)>2000:
        raise MaterialError('Rascunho inválido para essa análise.')
    for identity,fields in drafts.items():
        if identity not in issues or not isinstance(fields,dict) or set(fields)-{'description','value','scale','visible'}:
            raise MaterialError('Rascunho inválido para essa análise.')
        if any((name=='visible' and type(value) is not bool) or (name!='visible' and (not isinstance(value,str) or len(value)>3000)) for name,value in fields.items()):
            raise MaterialError('Rascunho inválido para essa análise.')
    if selected is not None and selected not in issues:
        raise MaterialError('Apontamento não encontrado.')
    filters = body.get('filters', {})
    if not isinstance(filters, dict) or filters.get('category','all') not in ('all','contrast','images','font','structure') or filters.get('status','all') not in ('all','pending','reviewed','resolved','human'):
        raise MaterialError('Filtro inválido.')
    scroll = body.get('scroll', 0)
    if not isinstance(scroll,(int,float)) or not math.isfinite(scroll) or not 0 <= scroll <= 100000:
        scroll = 0
    progress = {'page':page,'issue_id':selected,'mode':'step' if body.get('mode')=='step' else 'side', 'reviewed':list(dict.fromkeys(reviewed)), 'resolved':list(dict.fromkeys(resolved)), 'filters':{'category':filters.get('category','all'),'status':filters.get('status','all')},'scroll':scroll}
    if is_example(job):
        return progress
    progress['drafts']=drafts
    with LOCK:
        state = read(folder)
        state['progress'][job['id']] = progress
        state['last_job_id'] = job['id']
        # Bound metadata growth while keeping the most recently touched jobs.
        state['progress'].pop(job['id'], None)
        state['progress'][job['id']] = progress
        while len(state['progress'])>300:
            state['progress'].pop(next(iter(state['progress'])))
        write(folder, state)
    return progress
