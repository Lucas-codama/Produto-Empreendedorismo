from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

import server


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path=Path(temporary.name)/'.env'
        self.path.write_text('OPENROUTER_API_KEY=local-key\nOPENROUTER_MODEL=local-model\nPORT=9999\n',encoding='utf-8')

    def test_local_ai_settings_override_stale_inherited_values(self):
        with patch.dict(os.environ,{'OPENROUTER_API_KEY':'old-key','OPENROUTER_MODEL':'old-model','PORT':'8765'},clear=True):
            server.load_app_environment(self.path)
            self.assertEqual(os.environ['OPENROUTER_API_KEY'],'local-key')
            self.assertEqual(os.environ['OPENROUTER_MODEL'],'local-model')
            self.assertEqual(os.environ['PORT'],'8765')

    def test_render_keeps_deployment_settings(self):
        with patch.dict(os.environ,{'RENDER':'true','OPENROUTER_API_KEY':'server-key','OPENROUTER_MODEL':'server-model'},clear=True):
            server.load_app_environment(self.path)
            self.assertEqual(os.environ['OPENROUTER_API_KEY'],'server-key')
            self.assertEqual(os.environ['OPENROUTER_MODEL'],'server-model')

    def test_missing_local_file_keeps_inherited_key(self):
        with patch.dict(os.environ,{'OPENROUTER_API_KEY':'inherited-key'},clear=True):
            server.load_app_environment(self.path.with_name('absent.env'))
            self.assertEqual(os.environ['OPENROUTER_API_KEY'],'inherited-key')

    def test_empty_local_key_disables_old_inherited_key(self):
        self.path.write_text('OPENROUTER_API_KEY=\n',encoding='utf-8')
        with patch.dict(os.environ,{'OPENROUTER_API_KEY':'old-key'},clear=True):
            server.load_app_environment(self.path)
            self.assertEqual(os.environ['OPENROUTER_API_KEY'],'')
