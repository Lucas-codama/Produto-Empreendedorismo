import json
from http.cookiejar import CookieJar
from urllib.request import Request, build_opener, HTTPCookieProcessor
from urllib.error import HTTPError
from unittest.mock import patch
import unittest
from pathlib import Path
import server,accounts,workspace_store,test_analyzer

class WorkspaceTests(unittest.TestCase):
    setUpClass=classmethod(test_analyzer.ServerTests.setUpClass.__func__)
    tearDownClass=classmethod(test_analyzer.ServerTests.tearDownClass.__func__)

    def client(self):return build_opener(HTTPCookieProcessor(CookieJar()))
    def request(self,client,path,body=None,headers=None):
        req=Request(self.url+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json',**(headers or {})})
        with client.open(req) as r:return r.read(),r.headers
    def api(self,client,path,body=None):return json.loads(self.request(client,path,body)[0])
    def register(self,client,label):
        return self.api(client,'/api/account/register',dict(name=label,email=label+'@example.test',password='Senha de teste 2026!'))

    def test_accounts_isolate_jobs_profiles_progress_and_history(self):
        guest=self.client();one=self.client();two=self.client()
        self.register(one,'isolation-one');self.register(two,'isolation-two')
        self.assertEqual(self.api(two,'/api/history/clear',{})['count'],0)
        job=self.api(one,'/api/demo',{})
        profile=self.api(one,'/api/profiles/save',dict(name='Ampliação',needs='Fonte ampliada',technology='Zoom',min_font=20))
        issue=job['analysis']['issues'][1]
        saved=self.api(one,'/api/progress',dict(id=job['id'],page=issue['page'] or 0,issue_id=issue['id'],mode='step',reviewed=[issue['id']],filters=dict(category='all',status='reviewed'),scroll=120))
        self.assertEqual(self.api(one,'/api/workspace')['progress'][job['id']],saved)
        for stranger in (guest,two):
            self.assertNotIn(job['id'],[j['id'] for j in self.api(stranger,'/api/jobs')])
            self.assertNotIn(profile['id'],[p['id'] for p in self.api(stranger,'/api/workspace')['profiles']])
            for suffix in ('','/file','/original','/reading','/report'):
                with self.assertRaises(HTTPError) as err:self.api(stranger,'/api/job/'+job['id']+suffix)
                self.assertEqual(err.exception.code,400)
        token=self.api(one,'/api/history/clear',{})['undo_token']
        self.assertIsNone(self.api(one,'/api/workspace')['resume'])
        with self.assertRaises(HTTPError):self.api(two,'/api/history/restore',dict(token=token))
        self.api(one,'/api/history/restore',dict(token=token))
        self.assertEqual(self.api(one,'/api/workspace')['resume']['id'],job['id'])

    def test_login_cookie_logout_and_new_browser_restore(self):
        first=self.client();self.register(first,'resume-login')
        job=self.api(first,'/api/demo',{})
        self.api(first,'/api/progress',dict(id=job['id'],page=0,issue_id=None,mode='side',reviewed=[],filters=dict(category='images',status='pending')))
        second=self.client()
        _,headers=self.request(second,'/api/account/login',dict(email='RESUME-LOGIN@example.test',password='Senha de teste 2026!'))
        self.assertIn('HttpOnly',headers['Set-Cookie']);self.assertIn('SameSite=Strict',headers['Set-Cookie'])
        self.assertEqual(self.api(second,'/api/workspace')['resume']['id'],job['id'])
        cookie=headers['Set-Cookie'].split(';')[0]
        self.api(second,'/api/account/logout',{})
        self.assertIsNone(self.api(second,'/api/account')['user'])
        self.assertIsNone(json.loads(self.request(self.client(),'/api/account',headers={'Cookie':cookie})[0])['user'])

    def test_import_is_explicit_idempotent_and_preserves_guest(self):
        guest=self.client();own=self.client();job=self.api(guest,'/api/demo',{})
        self.register(own,'import-account')
        self.assertEqual(self.api(own,'/api/jobs'),[])
        result=self.api(own,'/api/account/import-local',{})
        self.assertGreater(result['copied'],0)
        self.assertEqual(self.api(own,'/api/account/import-local',{})['copied'],0)
        self.assertEqual(self.request(own,'/api/job/'+job['id']+'/file')[0],self.request(guest,'/api/job/'+job['id']+'/file')[0])
        self.api(own,'/api/history/clear',{})
        self.assertEqual(self.api(guest,'/api/job/'+job['id'])['id'],job['id'])

    def test_progress_rejects_nonexistent_pages_issues_and_filters(self):
        client=self.client();job=self.api(client,'/api/demo',{})
        for bad in ({'page':999},{'page':True},{'issue_id':'unknown'},{'reviewed':['unknown']},{'filters':{'category':'fake'}},{'filters':{'status':'fake'}}):
            with self.subTest(bad=bad),self.assertRaises(HTTPError) as error:self.api(client,'/api/progress',{'id':job['id'],'page':0,**bad})
            self.assertEqual(error.exception.code,400)

    def test_profiles_update_delete_and_bad_font(self):
        client=self.client();body=dict(name='Leitura',needs='20 pt',technology='Leitor',min_font=20)
        p=self.api(client,'/api/profiles/save',body)
        self.api(client,'/api/profiles/save',{**body,'id':p['id'],'name':'Novo nome'})
        found=[x for x in self.api(client,'/api/workspace')['profiles'] if x['id']==p['id']]
        self.assertEqual(len(found),1);self.assertEqual(found[0]['name'],'Novo nome')
        for font in ('NaN',200,'infinity'):
            with self.assertRaises(HTTPError):self.api(client,'/api/profiles/save',{**body,'min_font':font})
        self.api(client,'/api/profiles/delete',dict(id=p['id']))
        self.assertNotIn(p['id'],[x['id'] for x in self.api(client,'/api/workspace')['profiles']])

    def test_foreign_origin_blocked_for_accounts(self):
        with self.assertRaises(HTTPError) as err:self.request(self.client(),'/api/account/login',{},headers={'Origin':'https://other.example'})
        self.assertEqual(err.exception.code,403)

class AccountSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=test_analyzer.temporary_workspace();self.db=accounts.Accounts(Path(self.tmp.name)/'accounts.sqlite')
    def tearDown(self):test_analyzer.cleanup_workspace(self.tmp)
    def test_hashes_random_salts_and_hashed_sessions(self):
        body=dict(name='User',email='one@example.test',password='Uma senha de teste 2026')
        one,token=self.db.register(body,'one');self.db.register({**body,'email':'two@example.test'},'two')
        with self.db.connect() as db:
            users=db.execute('SELECT salt,password_hash FROM users').fetchall();session=db.execute('SELECT token_hash FROM sessions').fetchone()[0]
        self.assertNotEqual(users[0]['salt'],users[1]['salt']);self.assertNotEqual(users[0]['password_hash'],users[1]['password_hash'])
        self.assertNotEqual(session,token);self.assertEqual(len(session),64)
        with patch('accounts.time.time',return_value=1e12):self.assertIsNone(self.db.user('entrelinhas_session='+token))
    def test_throttle_persists_and_password_minimum(self):
        with self.assertRaises(server.MaterialError):self.db.register(dict(name='X',email='x@example.test',password='1234567'),'minimum')
        for _ in range(12):self.db.throttle('attempt')
        reopened=accounts.Accounts(self.db.path)
        with self.assertRaises(server.MaterialError):reopened.throttle('attempt')
    def test_password_boundaries_and_login_at_eight_characters(self):
        body=dict(name='Teste',email='eight@example.test',password='Teste123')
        user,_=self.db.register(body,'eight-register')
        logged,_=self.db.login(body,'eight-login')
        self.assertEqual(logged['id'],user['id'])
        self.assertEqual(self.db.password('x'*128),'x'*128)
        for value in ('x'*7,'x'*129,None):
            with self.subTest(length=len(value) if value else None),self.assertRaises(server.MaterialError):self.db.password(value)
    def test_wrong_password_generic_and_malformed_cookie(self):
        self.db.register(dict(name='User',email='known@example.test',password='Uma senha de teste 2026'),'known')
        errors=[]
        for email in ('known@example.test','missing@example.test'):
            with self.assertRaises(server.MaterialError) as err:self.db.login(dict(email=email,password='wrong'),'login')
            errors.append(str(err.exception))
        self.assertEqual(errors[0],errors[1]);self.assertIsNone(self.db.user('bad-cookie'))

if __name__=='__main__':unittest.main(verbosity=2)
