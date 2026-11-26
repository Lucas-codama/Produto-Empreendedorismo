"""SQLite revision archive. Completed revisions are immutable review snapshots."""
from contextlib import closing
from datetime import datetime,timezone
from pathlib import Path
import json
import sqlite3


def database(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(folder/'reviews.sqlite',timeout=15)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS revisions(
            id TEXT PRIMARY KEY, root_id TEXT NOT NULL, parent_id TEXT, filename TEXT NOT NULL,
            version INTEGER NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL,
            completed_at TEXT);
        CREATE INDEX IF NOT EXISTS revision_roots ON revisions(root_id,version);
        CREATE TABLE IF NOT EXISTS findings(
            revision_id TEXT NOT NULL REFERENCES revisions(id), issue_id TEXT NOT NULL,
            resolved INTEGER NOT NULL, method TEXT NOT NULL, data TEXT NOT NULL,
            PRIMARY KEY(revision_id,issue_id));
        CREATE TABLE IF NOT EXISTS changes(
            revision_id TEXT NOT NULL REFERENCES revisions(id), sequence INTEGER NOT NULL,
            data TEXT NOT NULL, PRIMARY KEY(revision_id,sequence));
        CREATE TABLE IF NOT EXISTS ai_acceptances(
            content_key TEXT PRIMARY KEY, accepted_count INTEGER NOT NULL,
            result TEXT NOT NULL);
    ''')
    return db


def summary(folder,identity):
    if not (Path(folder)/'reviews.sqlite').exists():return None
    with closing(database(folder)) as db:
        row=db.execute('SELECT * FROM revisions WHERE id=?',(identity,)).fetchone()
        if row is None:return None
        counts=db.execute('SELECT COUNT(*),COALESCE(SUM(resolved),0) FROM findings WHERE revision_id=?',(identity,)).fetchone()
        return {**dict(row),'total':counts[0],'resolved_count':counts[1]}


def sync(folder,job,resolved=()):
    if job.get('is_example'):return None
    now=datetime.now(timezone.utc).isoformat();identity=job['id'];resolved=set(resolved)
    with closing(database(folder)) as db,db:
        old=db.execute('SELECT status FROM revisions WHERE id=?',(identity,)).fetchone()
        if old and old['status']=='completed':return summary(folder,identity)
        db.execute('INSERT OR IGNORE INTO revisions VALUES(?,?,?,?,?,?,?,NULL)',
            (identity,job['root_id'],job.get('parent_id'),job['filename'],job['version'],job['created_at'],'active'))
        prior=db.execute('SELECT * FROM findings WHERE revision_id=?',(job.get('parent_id'),)).fetchall() if not old else []
        current={i['id']:i for i in job['analysis']['issues']}
        for row in prior:
            if row['issue_id'] in current:continue
            data=json.loads(row['data']);data['resolved_in_version']=job['version']
            changed=any(edit.get('page')==data.get('page') and edit.get('block_id')==data.get('block_id') for edit in job.get('edits',[]))
            method=row['method'] if row['resolved'] else 'edited' if changed else 'not_found'
            db.execute('INSERT OR IGNORE INTO findings VALUES(?,?,?,?,?)',(identity,row['issue_id'],1,method,json.dumps(data,ensure_ascii=False)))
        for issue in current.values():
            done=issue['id'] in resolved;method='edited' if issue['id'] in job.get('edited_issue_ids',[]) else 'manual' if done else 'pending'
            data={key:issue.get(key) for key in ('id','rule','title','location','page','block_id','text','explanation','evidence')}
            data['version']=job['version']
            db.execute('INSERT OR REPLACE INTO findings VALUES(?,?,?,?,?)',(identity,issue['id'],int(done),method,json.dumps(data,ensure_ascii=False)))
        if not old:
            inherited=db.execute('SELECT data FROM changes WHERE revision_id=? ORDER BY sequence',(job.get('parent_id'),)).fetchall()
            edits=[json.loads(r['data']) for r in inherited]+[{**edit,'version':job['version'],'at':now} for edit in job.get('edits',[])]
            db.executemany('INSERT INTO changes VALUES(?,?,?)',[(identity,n,json.dumps(edit,ensure_ascii=False)) for n,edit in enumerate(edits)])
        complete=all(i['id'] in resolved for i in current.values())
        if complete:db.execute("UPDATE revisions SET status='completed',completed_at=? WHERE id=?",(now,identity))
    return summary(folder,identity)


def details(folder,identity):
    result=summary(folder,identity)
    if result is None:return None
    with closing(database(folder)) as db:
        result['findings']=[{**json.loads(row['data']),'resolved':bool(row['resolved']),'method':row['method']}
            for row in db.execute('SELECT * FROM findings WHERE revision_id=? ORDER BY rowid',(identity,))]
        result['changes']=[json.loads(row['data']) for row in db.execute('SELECT data FROM changes WHERE revision_id=? ORDER BY sequence',(identity,))]
    return result


def root_completed(folder,root_id):
    if not (Path(folder)/'reviews.sqlite').exists():return False
    with closing(database(folder)) as db:
        row=db.execute('SELECT status FROM revisions WHERE root_id=? ORDER BY version DESC LIMIT 1',(root_id,)).fetchone()
        return row is not None and row['status']=='completed'


def ai_status(folder,content_key):
    if not (Path(folder)/'reviews.sqlite').exists():return {'accepted_count':0,'result':None}
    with closing(database(folder)) as db:
        row=db.execute('SELECT accepted_count,result FROM ai_acceptances WHERE content_key=?',(content_key,)).fetchone()
        return {'accepted_count':row['accepted_count'],'result':json.loads(row['result'])} if row else {'accepted_count':0,'result':None}


def accept_ai(folder,content_key,result):
    with closing(database(folder)) as db,db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT accepted_count FROM ai_acceptances WHERE content_key=?',(content_key,)).fetchone()
        count=row['accepted_count'] if row else 0
        if count>=2:return None
        db.execute('INSERT OR REPLACE INTO ai_acceptances VALUES(?,?,?)',(content_key,count+1,json.dumps(result,ensure_ascii=False)))
        return count+1


def remember_ai(folder,content_key,result):
    """Cache a verified suggestion without consuming or resetting user approvals."""
    with closing(database(folder)) as db,db:
        db.execute('INSERT INTO ai_acceptances VALUES(?,0,?) '
            'ON CONFLICT(content_key) DO UPDATE SET result=excluded.result',
            (content_key,json.dumps(result,ensure_ascii=False)))
