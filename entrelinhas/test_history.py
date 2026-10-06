import json
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch
import unittest
import server,history_store,test_analyzer


class HistoryTests(unittest.TestCase):
    setUpClass=classmethod(test_analyzer.ServerTests.setUpClass.__func__)
    tearDownClass=classmethod(test_analyzer.ServerTests.tearDownClass.__func__)
    request=test_analyzer.ServerTests.request

    def test_clear_and_restore_preserve_files_versions_and_reading(self):
        job=json.loads(self.request('/api/demo',{})[0])
        eligible=[i['id'] for i in job['analysis']['issues'] if i['action']=='font']
        revised=json.loads(self.request('/api/assist',{'id':job['id'],'issues':eligible})[0])
        original=server.file_path(job).read_bytes();second=server.file_path(revised).read_bytes()
        sentinel=server.DATA/'outside-history.txt';sentinel.write_text('preserve',encoding='utf-8')
        cleared=json.loads(self.request('/api/history/clear',{})[0])
        self.assertIn(job['id'],cleared['ids']);self.assertIn(revised['id'],cleared['ids'])
        self.assertEqual(json.loads(self.request('/api/jobs')[0]),[])
        self.assertEqual(sentinel.read_text(encoding='utf-8'),'preserve')
        self.assertFalse(server.file_path(job).exists())
        restored=json.loads(self.request('/api/history/restore',{'token':cleared['undo_token']})[0])
        self.assertEqual(restored['count'],cleared['count'])
        self.assertEqual(server.file_path(job).read_bytes(),original);self.assertEqual(server.file_path(revised).read_bytes(),second)
        current=json.loads(self.request('/api/job/'+revised['id'])[0]);self.assertEqual(current['root_id'],job['id'])

    def test_empty_history_and_bad_restore_do_not_delete(self):
        cleared=json.loads(self.request('/api/history/clear',{})[0])
        empty=json.loads(self.request('/api/history/clear',{})[0])
        self.assertEqual(empty['count'],0);self.assertIsNone(empty['undo_token'])
        for token in ['../jobs','a'*31,'missing']:
            with self.assertRaises(HTTPError) as error:self.request('/api/history/restore',{'token':token})
            self.assertEqual(error.exception.code,400)
        if cleared['undo_token']:self.request('/api/history/restore',{'token':cleared['undo_token']})

    def test_failed_move_rolls_back_history(self):
        job1=json.loads(self.request('/api/demo',{})[0]);job2=json.loads(self.request('/api/demo',{})[0])
        existing=Path.rename;counter=0
        def fail_second(path,target):
            nonlocal counter
            if Path(target).parent.parent.name=='trash':
                counter+=1
                if counter==2:raise OSError('Synthetic move failure')
            return existing(path,target)
        with patch.object(Path,'rename',fail_second):
            with self.assertRaises(OSError):history_store.clear(server.DATA)
        self.assertTrue(server.file_path(job1).exists());self.assertTrue(server.file_path(job2).exists())

    def test_restore_never_overwrites_newer_job(self):
        job=json.loads(self.request('/api/demo',{})[0]);cleared=json.loads(self.request('/api/history/clear',{})[0])
        collision=server.job_path(job['id']);collision.mkdir();marker=collision/'marker.txt';marker.write_text('new file',encoding='utf-8')
        with self.assertRaises(HTTPError):self.request('/api/history/restore',{'token':cleared['undo_token']})
        self.assertEqual(marker.read_text(encoding='utf-8'),'new file')
        marker.unlink();collision.rmdir();self.request('/api/history/restore',{'token':cleared['undo_token']})

if __name__=='__main__':unittest.main(verbosity=2)
