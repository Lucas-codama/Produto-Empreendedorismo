"""Reversible history clearing. Only managed job directories are moved."""
from pathlib import Path
from datetime import datetime,timezone
import json
import re
import uuid


def checked_folder(path,root):
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Não foi possível mover um dos materiais do histórico.')
    return path


def clear(data):
    data=Path(data)
    if data.is_symlink():raise ValueError('A pasta de materiais não está disponível para esta operação.')
    trash=data.parent/'trash'
    if trash.is_symlink():raise ValueError('A lixeira local não está disponível.')
    candidates=[]
    for path in data.iterdir():
        if re.fullmatch('[0-9a-f]{32}',path.name) and path.is_dir() and (path/'analysis.json').is_file():
            checked_folder(path,data);candidates.append(path)
    if not candidates:return {'count':0,'ids':[],'undo_token':None}
    trash.mkdir(exist_ok=True)
    token=uuid.uuid4().hex;batch=trash/token;batch.mkdir()
    checked_folder(batch,trash)
    moved=[]
    try:
        for path in candidates:
            destination=checked_folder(batch/path.name,batch)
            checked_folder(path,data).rename(destination);moved.append(path.name)
        manifest={'ids':moved,'created_at':datetime.now(timezone.utc).isoformat()}
        (batch/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    except Exception:
        for identity in reversed(moved):
            source=checked_folder(batch/identity,batch);destination=checked_folder(data/identity,data)
            if not destination.exists():source.rename(destination)
        raise
    return {'count':len(moved),'ids':moved,'undo_token':token}


def restore(data,token):
    data=Path(data)
    if not re.fullmatch('[0-9a-f]{32}',token or ''):raise ValueError('Não foi possível localizar os materiais para recuperar.')
    trash=data.parent/'trash';batch=checked_folder(trash/token,trash)
    if data.is_symlink() or trash.is_symlink():raise ValueError('A pasta de materiais não está disponível.')
    try:manifest=json.loads((batch/'manifest.json').read_text(encoding='utf-8'))
    except FileNotFoundError:raise ValueError('Essa limpeza já foi desfeita ou não está disponível.')
    identities=manifest.get('ids',[])
    if not identities or len(set(identities))!=len(identities) or any(not isinstance(i,str) or not re.fullmatch('[0-9a-f]{32}',i) for i in identities):raise ValueError('Os materiais não puderam ser recuperados.')
    for identity in identities:
        source=checked_folder(batch/identity,batch);destination=checked_folder(data/identity,data)
        if not source.is_dir() or destination.exists():raise ValueError('Um material não pode ser recuperado sem sobrescrever outro arquivo.')
    moved=[]
    try:
        for identity in identities:
            checked_folder(batch/identity,batch).rename(checked_folder(data/identity,data));moved.append(identity)
    except Exception:
        for identity in reversed(moved):checked_folder(data/identity,data).rename(checked_folder(batch/identity,batch))
        raise
    manifest['restored_at']=datetime.now(timezone.utc).isoformat()
    (batch/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    return {'count':len(moved),'ids':moved}
