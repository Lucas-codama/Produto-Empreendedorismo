from __future__ import annotations

import argparse
from contextvars import ContextVar
from functools import lru_cache, wraps
import base64
import binascii
from datetime import datetime, timezone
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import mimetypes
import os
from pathlib import Path
import re
import shutil
import tempfile
import threading
import uuid
from urllib.parse import unquote, urlparse, quote

from analyzer import MaterialError, MAX_BYTES, ENGINE_VERSION, analyze, apply_edit, decorate_actions, demo_pptx
import pypdfium2 as pdfium
import reading
import history_store
import accounts
import workspace_store
from vision_checks import PDF_LOCK

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / 'static'
DATA = ROOT / '.runtime' / 'jobs'
RENDER_LOCK = PDF_LOCK
JOB_LOCK = threading.RLock()
CURRENT_USER = ContextVar('entrelinhas_user', default=None)

@lru_cache(maxsize=12)
def account_database(path):
    return accounts.Accounts(path)

def identity_store():
    return account_database(str(DATA.parent/'accounts.sqlite'))

def workspace_path():
    user = CURRENT_USER.get()
    return DATA.parent/'accounts'/user['id'] if user else DATA.parent

def data_path():
    folder = workspace_path()/'jobs' if CURRENT_USER.get() else DATA
    folder.mkdir(parents=True, exist_ok=True)
    return folder

def scoped_request(method):
    @wraps(method)
    def wrapped(self):
        cookie = self.headers.get('Cookie','')
        self.user = identity_store().user(cookie) if 'entrelinhas_session=' in cookie else None
        token = CURRENT_USER.set(self.user)
        try:
            return method(self)
        finally:
            CURRENT_USER.reset(token)
    return wrapped


def job_path(identity):
    if not re.fullmatch('[0-9a-f]{32}', identity or ''):
        raise MaterialError('Análise não encontrada.')
    return data_path() / identity


def load_job(identity):
    try:
        with JOB_LOCK:
            target=job_path(identity)/'analysis.json'
            job=json.loads(target.read_text(encoding='utf-8'))
            if job['analysis'].get('engine_version')!=ENGINE_VERSION:
                job['analysis']=decorate_actions(analyze(file_path(job),dict(job['analysis']['context'])))
                job.pop('ai_review',None)
                if job.get('parent_id'):
                    previous=load_job(job['parent_id'])
                    job['comparison']=compare(previous,job['analysis'])
                temporary=target.with_suffix('.new')
                temporary.write_text(json.dumps(job,ensure_ascii=False),encoding='utf-8');temporary.replace(target)
            job['is_example'] = workspace_store.is_example(job)
            return job
    except FileNotFoundError:
        raise MaterialError('Essa análise não está mais disponível neste computador.')


def file_path(job):
    return job_path(job['id']) / ('material' + job['extension'])


def compare(previous, current):
    if not previous:
        return None
    old = {i['id']: i for i in previous['analysis']['issues']}
    new = {i['id']: i for i in current['issues']}
    return {'previous_version': previous['version'], 'persistent': len(old.keys() & new.keys()),
            'not_found': len(old.keys() - new.keys()), 'new': len(new.keys() - old.keys()),
            'not_found_items': [old[k]['title'] for k in old.keys() - new.keys()],
            'note': 'Itens que não reapareceram precisam ser conferidos. A comparação usa regra e localização; mudanças na estrutura do arquivo podem deslocar os elementos.'}


def create_job(content, filename, context, previous=None, edits=None, is_example=False):
    with JOB_LOCK:
        return _create_job(content,filename,context,previous,edits,is_example)


def _create_job(content, filename, context, previous=None, edits=None, is_example=False):
    identity = uuid.uuid4().hex
    folder = job_path(identity)
    folder.mkdir(parents=True)
    extension = Path(filename).suffix.lower()
    path = folder / ('material' + extension)
    try:
        path.write_bytes(content)
        result = decorate_actions(analyze(path, context))
        job = {'id': identity, 'root_id': previous['root_id'] if previous else identity,
               'parent_id': previous['id'] if previous else None, 'filename': Path(filename).name[:180],
               'extension': extension, 'version': previous['version'] + 1 if previous else 1,
               'created_at': datetime.now(timezone.utc).isoformat(), 'analysis': result,
               'comparison': compare(previous, result), 'edits': edits or [],
               'is_example': workspace_store.is_example(previous) if previous else is_example}
        (folder / 'analysis.json').write_text(json.dumps(job, ensure_ascii=False), encoding='utf-8')
        return job
    except Exception:
        if not folder.resolve().is_relative_to(data_path().resolve()):
            raise RuntimeError('Unexpected material folder')
        shutil.rmtree(folder)
        raise


def edit_job(job, requests):
    with JOB_LOCK:
        return _edit_job(job,requests)


def _edit_job(job, requests):
    issues = {i['id']: i for i in job['analysis']['issues']}
    if not requests or len(requests) > 100:
        raise MaterialError('Selecione de 1 a 100 ajustes por vez.')
    with tempfile.TemporaryDirectory(dir=DATA.parent, prefix='edits-') as folder:
        current = file_path(job)
        edits = []
        for index, request in enumerate(requests):
            issue = issues.get(request.get('issue_id'))
            if issue is None or not issue.get('action'):
                raise MaterialError('Um dos ajustes não é compatível com essa análise.')
            value = request.get('value')
            if issue['action'] == 'font':
                value = value or job['analysis']['context']['min_font']
            destination = Path(folder) / (str(index) + job['extension'])
            apply_edit(current, destination, issue, value)
            current = destination
            edits.append({'title': issue['title'], 'location': issue['location'], 'action': issue['action'],
                          'note': 'Conferir o resultado, o espaço disponível e a finalidade da atividade.'})
        return create_job(current.read_bytes(), job['filename'], dict(job['analysis']['context']), job, edits)


def report(job):
    a = job['analysis']
    context = a['context']
    def e(value): return escape(str(value))
    items = ''.join(f'<section><h2>{i["number"]}. {e(i["title"])}</h2><p><strong>Localização:</strong> {e(i["location"])}</p>'
                    f'<p><strong>Evidência:</strong> {e(i["evidence"] or "Revisão de contexto e estrutura")}</p>'
                    f'<p>{e(i["explanation"])}</p><p><strong>Orientação:</strong> {e(i["suggestion"])}</p></section>' for i in a['issues'])
    coverage = ''.join(f'<li><strong>{e(c["name"])}:</strong> {e(c["detail"])}</li>' for c in a['checks'])
    comparison = ''
    if job['comparison']:
        c = job['comparison']
        comparison = f'<h2>Comparação com a versão {c["previous_version"]}</h2><p>{c["persistent"]} itens persistentes; {c["not_found"]} não reapareceram; {c["new"]} itens novos.</p><p>{e(c["note"])}</p>'
    return f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Relatório de acessibilidade - {e(job['filename'])}</title><style>body{{font:16px/1.6 system-ui,sans-serif;max-width:900px;margin:40px auto;padding:0 24px;color:#202534}}h1,h2{{color:#24264f}}h1{{font-size:30px}}h2{{font-size:20px}}section{{border-top:1px solid #c7cfd5;margin-top:24px;padding-top:16px}}.summary{{background:#eef5f3;padding:20px}}@media print{{body{{margin:0;max-width:none}}section{{break-inside:avoid}}}}</style>
<main><h1>Entrelinhas | Relatório de verificação</h1><p>{e(job['filename'])} | Versão {job['version']}</p>
<div class="summary"><strong>{a['counts']['attention']} pontos de atenção e {a['counts']['review']} itens para revisão humana.</strong><p>Este relatório registra verificações parciais. Não certifica acessibilidade completa.</p></div>
<h2>Contexto informado</h2><p><strong>Disciplina:</strong> {e(context['discipline'])}<br><strong>Atividade:</strong> {e(context['activity'])}<br><strong>Necessidades:</strong> {e(context['needs'])}<br><strong>Tecnologias assistivas:</strong> {e(context['technology'])}</p>
<h2>Cobertura desta análise</h2><ul>{coverage}</ul><p>{e(a['info']['preview'])}</p>{comparison}<h2>Itens encontrados</h2>{items or '<p>Nenhum item foi apontado pelas regras aplicadas. Confira os aspectos não verificados e teste o acesso ao material.</p>'}
<h2>Referência para o contraste</h2><p><a href="https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html">W3C: contraste mínimo</a>. Descrições, sentido pedagógico e uso com tecnologias assistivas exigem revisão do professor e teste com o estudante.</p></main></html>'''.encode('utf-8')


class Handler(BaseHTTPRequestHandler):
    def valid_host(self):
        if os.environ.get('ALLOW_REMOTE', 'true').lower() in {'true', '1', 'yes'} or os.environ.get('RENDER'):
            return True
        host = self.headers.get('Host', '')
        return host in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}

    def log_message(self, *_):
        pass

    def send(self, content, status=200, content_type='application/json; charset=utf-8', disposition=None, headers=None):
        if not isinstance(content, bytes):
            content = json.dumps(content, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
        if disposition:
            self.send_header('Content-Disposition', disposition)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(content)

    @scoped_request
    def do_GET(self):
        if not self.valid_host():
            return self.send({'error': 'Abra este serviço pelo endereço local.'}, 403)
        try:
            path = unquote(urlparse(self.path).path)
            if path == '/api/health':
                return self.send({'app': 'entrelinhas', 'status': 'ok'})
            if path == '/api/account':
                return self.send({'user':self.user, 'scope':self.user['id'] if self.user else 'guest','storage':'local-server','online_sync':False})
            if path == '/api/workspace':
                state = workspace_store.read(workspace_path())
                def available_personal(identity):
                    target = job_path(identity)/'analysis.json'
                    if not target.exists():
                        return None
                    record = json.loads(target.read_text(encoding='utf-8'))
                    return None if workspace_store.is_example(record) else record
                state['progress'] = {identity:progress for identity,progress in state['progress'].items()
                                     if available_personal(identity)}
                last = state.get('last_job_id')
                j = available_personal(last) if last else None
                if last and j is None and (job_path(last)/'analysis.json').exists():
                    last = next((identity for identity in reversed(state['progress'])), None)
                    j = available_personal(last) if last else None
                state['last_job_id'] = last if j else None
                if j:
                    state['resume'] = {'id':last,'filename':j['filename'],'version':j['version']}
                else:
                    state['resume'] = None
                return self.send(state)
            if path == '/api/jobs':
                records = []
                with JOB_LOCK:
                    for file in data_path().glob('*/analysis.json'):
                        j = json.loads(file.read_text(encoding='utf-8'))
                        if workspace_store.is_example(j):
                            continue
                        records.append({k: j[k] for k in ['id', 'filename', 'version', 'created_at', 'root_id']})
                return self.send(sorted(records, key=lambda j: j['created_at'], reverse=True)[:20])
            match = re.fullmatch(r'/api/job/([0-9a-f]{32})(?:/(file|original|report|reading|page/\d+))?', path)
            if match:
                job = load_job(match[1]); suffix = match[2]
                if suffix is None:
                    return self.send(job)
                if suffix == 'report':
                    return self.send(report(job), content_type='text/html; charset=utf-8',
                                     disposition="attachment; filename*=UTF-8''"+quote('Relatorio_Entrelinhas_v'+str(job['version'])+'.html'))
                if suffix == 'reading':
                    return self.send(reading.render(job),content_type='text/html; charset=utf-8',
                                     disposition="attachment; filename*=UTF-8''"+quote('Leitura_'+job['filename']+'.html'))
                if suffix in {'file', 'original'}:
                    material = load_job(job['root_id']) if suffix == 'original' else job
                    name = ('Material_v'+str(material['version'])+'_') + material['filename'] if suffix == 'file' else material['filename']
                    return self.send(file_path(material).read_bytes(), content_type='application/octet-stream',
                                     disposition="attachment; filename*=UTF-8''"+quote(name))
                index = int(suffix.split('/')[1])
                if not 0 <= index < len(job['analysis']['pages']) or job['extension'] != '.pdf':
                    raise MaterialError('Página não encontrada.')
                with RENDER_LOCK:
                    pdf = pdfium.PdfDocument(str(file_path(job)))
                    page = pdf[index]; bitmap = page.render(scale=1.5)
                    image = bitmap.to_pil(); output = BytesIO(); image.save(output, format='PNG')
                    bitmap.close(); page.close(); pdf.close()
                return self.send(output.getvalue(), content_type='image/png')
            target = (STATIC / (path.lstrip('/') or 'index.html')).resolve()
            if STATIC.resolve() not in target.parents or not target.is_file():
                return self.send({'error': 'Página não encontrada.'}, 404)
            content_type = mimetypes.guess_type(str(target))[0] or 'application/octet-stream'
            return self.send(target.read_bytes(), content_type=content_type+'; charset=utf-8' if content_type.startswith('text/') else content_type)
        except MaterialError as exc:
            self.send({'error': str(exc)}, 400)
        except Exception:
            self.send({'error': 'Não foi possível abrir esse recurso.'}, 500)

    @scoped_request
    def do_POST(self):
        if not self.valid_host():
            return self.send({'error': 'Abra este serviço pelo endereço local.'}, 403)
        try:
            origin = self.headers.get('Origin')
            host = self.headers.get('Host', '')
            allowed = {f'http://{host}', f'https://{host}'}
            if origin and origin not in allowed:
                return self.send({'error': 'Essa operação deve ser feita no site local.'}, 403)
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.send({'error': 'Formato de requisição inválido.'}, 400)
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 30 * 1024 * 1024:
                return self.send({'error': 'Requisição muito grande ou vazia.'}, 413)
            body = json.loads(self.rfile.read(length))
            if not isinstance(body,dict):
                raise MaterialError('Formato de requisição inválido.')
            path = urlparse(self.path).path
            if path in {'/api/account/register','/api/account/login'}:
                database = identity_store()
                user, token = database.register(body,self.client_address[0]) if path.endswith('/register') else database.login(body,self.client_address[0])
                return self.send({'user':user,'scope':user['id']},headers={'Set-Cookie':database.cookie(token)})
            if path == '/api/account/update':
                if not self.user:
                    return self.send({'error':'Entre na conta para editar seu perfil.'}, 401)
                user = identity_store().update_profile(self.user['id'], body)
                return self.send({'user':user,'scope':user['id']})
            if path == '/api/account/logout':
                database=identity_store();database.logout(self.headers.get('Cookie'))
                return self.send({'user':None,'scope':'guest'},headers={'Set-Cookie':database.cookie('')})
            if path == '/api/account/import-local':
                if not self.user:
                    raise MaterialError('Entre na conta antes de copiar os materiais.')
                destination=data_path();destination.mkdir(parents=True,exist_ok=True)
                copied=0
                with JOB_LOCK, workspace_store.LOCK:
                    for source in DATA.iterdir():
                        if not re.fullmatch('[0-9a-f]{32}',source.name) or not source.is_dir() or source.is_symlink() or not (source/'analysis.json').is_file():
                            continue
                        if any(p.is_symlink() for p in source.rglob('*')):
                            continue
                        if workspace_store.is_example(json.loads((source/'analysis.json').read_text(encoding='utf-8'))):
                            continue
                        target=destination/source.name
                        if not target.exists():
                            stage=destination/(source.name+'.copy')
                            try:
                                shutil.copytree(source,stage);stage.replace(target);copied+=1
                            finally:
                                if stage.exists():shutil.rmtree(stage)
                    local=workspace_store.read(DATA.parent);own=workspace_store.read(workspace_path())
                    known={p['id'] for p in own['profiles']}
                    own['profiles']=(own['profiles']+[p for p in local['profiles'] if p['id'] not in known])[:40]
                    own['progress']={**local['progress'],**own['progress']}
                    own['last_job_id']=own.get('last_job_id') or local.get('last_job_id')
                    workspace_store.write(workspace_path(),own)
                return self.send({'copied':copied})
            if path == '/api/profiles/save':
                return self.send(workspace_store.save_profile(workspace_path(),body))
            if path == '/api/profiles/delete':
                workspace_store.remove_profile(workspace_path(),body.get('id'))
                return self.send({'ok':True})
            if path == '/api/progress':
                return self.send(workspace_store.save_progress(workspace_path(),load_job(body.get('id')),body))
            if path in {'/api/history/clear','/api/history/restore'}:
                with JOB_LOCK:
                    result=history_store.clear(data_path()) if path.endswith('/clear') else history_store.restore(data_path(),body.get('token'))
                return self.send(result)
            if path == '/api/demo':
                context = {'discipline': 'Geografia', 'activity': 'Atividade de sala',
                           'needs': 'Leitura ampliada; preferência informada de fonte de pelo menos 20 pt; acesso ao gráfico por descrição.',
                           'technology': 'Ampliação de tela e leitor de tela', 'min_font': 20}
                with tempfile.TemporaryDirectory(dir=DATA.parent, prefix='demo-') as tmp:
                    file = Path(tmp) / 'Atividade_Geografia.pptx'; demo_pptx(file)
                    job = create_job(file.read_bytes(), file.name, context, is_example=True)
                return self.send(job)
            if path == '/api/analyze':
                try:
                    content = base64.b64decode(body.get('file', ''), validate=True)
                except (binascii.Error, ValueError):
                    raise MaterialError('Não foi possível receber o arquivo.')
                if len(content) > MAX_BYTES:
                    raise MaterialError('O limite por material é de 20 MB.')
                parent = load_job(body['parent_id']) if body.get('parent_id') else None
                context = body.get('context', {})
                return self.send(create_job(content, body.get('filename', ''), context, parent))
            if path in {'/api/edit', '/api/assist'}:
                job = load_job(body.get('id'))
                if path == '/api/edit':
                    requests = [{'issue_id': body.get('issue_id'), 'value': body.get('value')}]
                else:
                    selected = body.get('issues', [])
                    eligible = {i['id'] for i in job['analysis']['issues'] if i['action'] in {'font', 'contrast'}}
                    if any(i not in eligible for i in selected):
                        raise MaterialError('A assistência aplica somente ajustes técnicos compatíveis e revisados.')
                    requests = [{'issue_id': i} for i in selected]
                return self.send(edit_job(job, requests))
            if path=='/api/reading':
                with JOB_LOCK:
                    job=load_job(body.get('id'));job['reading']=reading.validate(job,body.get('reading'))
                    temporary=job_path(job['id'])/'analysis.new'
                    temporary.write_text(json.dumps(job,ensure_ascii=False),encoding='utf-8')
                    temporary.replace(job_path(job['id'])/'analysis.json')
                return self.send(job)
            return self.send({'error': 'Operação não encontrada.'}, 404)
        except (MaterialError, ValueError, TypeError, KeyError) as exc:
            self.send({'error': str(exc) if isinstance(exc, MaterialError) else 'Confira os dados enviados e tente novamente.'}, 400)
        except Exception:
            self.send({'error': 'A operação não pôde ser concluída. O arquivo original foi preservado.'}, 500)


def main():
    parser = argparse.ArgumentParser()
    default_port = int(os.environ.get('PORT', 8765))
    parser.add_argument('--port', type=int, default=default_port)
    args = parser.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('0.0.0.0', args.port), Handler)
    print(f'Entrelinhas: http://0.0.0.0:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
