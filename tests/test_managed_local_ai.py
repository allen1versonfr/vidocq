import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock,patch
from zipfile import ZipFile
import managed_local_ai as ai
from local_drafts import LocalDrafts


def spec(data,url='https://huggingface.co/model'):
    return {'url':url,'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}


class Response(io.BytesIO):
    def __init__(self,data,status=200,content_range=''):
        super().__init__(data);self.url='https://us.aws.cdn.hf.co/model';self.status=status;self.headers={'Content-Range':content_range}


class DownloadTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'model.gguf';self.cancel=threading.Event()
    def tearDown(self):self.temp.cleanup()
    def test_resume_and_verify_before_atomic_install(self):
        data=b'complete pinned model';self.path.with_suffix('.gguf.part').write_bytes(data[:8]);opener=MagicMock();opener.open.return_value=Response(data[8:],206,'bytes 8-'+str(len(data)-1)+'/'+str(len(data)))
        ai.download(spec(data),self.path,self.cancel,lambda *a:None,opener)
        self.assertEqual(self.path.read_bytes(),data);self.assertFalse(self.path.with_suffix('.gguf.part').exists());self.assertEqual(opener.open.call_args.args[0].headers['Range'],'bytes=8-')
        opener.reset_mock();ai.download(spec(data),self.path,self.cancel,lambda *a:None,opener);opener.open.assert_not_called()
    def test_checksum_failure_preserves_existing_model_and_never_installs_bad_bytes(self):
        self.path.write_bytes(b'existing');opener=MagicMock();opener.open.return_value=Response(b'bad!')
        with self.assertRaisesRegex(ValueError,'checksum'):ai.download(spec(b'good'),self.path,self.cancel,lambda *a:None,opener)
        self.assertEqual(self.path.read_bytes(),b'existing');self.assertFalse(self.path.with_suffix('.gguf.part').exists())
    def test_range_ignored_restarts_instead_of_appending(self):
        data=b'good model';self.path.with_suffix('.gguf.part').write_bytes(b'good');opener=MagicMock();opener.open.return_value=Response(data)
        ai.download(spec(data),self.path,self.cancel,lambda *a:None,opener);self.assertEqual(self.path.read_bytes(),data)
    def test_invalid_range_and_unapproved_redirect_refused(self):
        self.path.with_suffix('.gguf.part').write_bytes(b'a');opener=MagicMock();opener.open.return_value=Response(b'bc',206,'bytes 0-2/3')
        with self.assertRaises(ValueError):ai.download(spec(b'abc'),self.path,self.cancel,lambda *a:None,opener)
        for url in ['http://huggingface.co/a','https://example.org/a','https://user:pass@huggingface.co/a','https://huggingface.co:8000/a']:
            with self.assertRaises(ValueError):ai.checked_url(url)
    def test_cancellation_retains_partial_download(self):
        self.cancel.set();opener=MagicMock();opener.open.return_value=Response(b'good model')
        with self.assertRaisesRegex(ValueError,'cancelled'):ai.download(spec(b'good model'),self.path,self.cancel,lambda *a:None,opener)
        self.assertFalse(self.path.exists())


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.data=Path(self.temp.name)/'workspace';self.manager=ai.ManagedLocalAI(self.data)
        self.runtime={'llama-server.exe':spec(b'fake executable')};self.model={**spec(b'fake model'),'name':'synthetic','filename':'model.gguf'}
        self.patch_model=patch.object(ai,'MODEL',self.model);self.patch_files=patch.object(ai,'RUNTIME_FILES',self.runtime);self.patch_model.start();self.patch_files.start()
    def tearDown(self):self.manager.stop();self.patch_files.stop();self.patch_model.stop();self.temp.cleanup()
    def install_fixture(self):
        root=self.manager.root;(root/'runtime').mkdir(parents=True)
        (root/'runtime'/'llama-server.exe').write_bytes(b'fake executable');(root/'model.gguf').write_bytes(b'fake model')
        (root/'installed.json').write_text(json.dumps({'model_sha256':self.model['sha256'],'runtime_sha256':ai.RUNTIME['sha256']}))
    def test_settings_survive_update_and_start_nothing_on_reopen(self):
        self.install_fixture();self.manager.set_enabled(True,'cpu')
        with patch('managed_local_ai.subprocess.Popen') as process:
            reopened=ai.ManagedLocalAI(self.data);self.assertTrue(reopened.enabled);self.assertTrue(reopened.installed());self.assertEqual(reopened.settings['backend'],'cpu');self.assertFalse(reopened.status()['running']);process.assert_not_called()
        self.manager.set_enabled(False);self.assertTrue((self.manager.root/'model.gguf').exists())
    def test_setup_needs_consent_and_disabled_drafts_start_nothing(self):
        with patch('managed_local_ai.download') as download,patch('managed_local_ai.subprocess.Popen') as process:
            with self.assertRaises(ValueError):self.manager.setup(False)
            client=LocalDrafts();client.manager=self.manager
            with self.assertRaises(ValueError):client.generate({'names':['Example']},None,'queries',True)
            download.assert_not_called();process.assert_not_called()
    def test_tampered_runtime_or_extra_dll_cannot_execute(self):
        self.install_fixture();self.manager.set_enabled(True)
        (self.manager.root/'runtime'/'unowned.dll').write_bytes(b'unknown')
        with patch('managed_local_ai.subprocess.Popen') as process:
            with self.assertRaisesRegex(ValueError,'Unexpected'):self.manager.ensure()
            process.assert_not_called()
        (self.manager.root/'runtime'/'unowned.dll').unlink();(self.manager.root/'runtime'/'llama-server.exe').write_bytes(b'FAKE executable')
        with patch('managed_local_ai.subprocess.Popen') as process:
            with self.assertRaises(ValueError):self.manager.ensure()
            process.assert_not_called()
    def test_vulkan_failure_falls_back_to_cpu_with_auth_and_fixed_loopback(self):
        self.install_fixture();self.manager.set_enabled(True)
        gpu=MagicMock();gpu.poll.return_value=1
        cpu=MagicMock();cpu.poll.return_value=None
        with patch('managed_local_ai.subprocess.Popen',side_effect=[gpu,cpu]) as process,patch('managed_local_ai.WindowsJob'),patch.object(self.manager,'_request',return_value={'status':'ok'}):
            port,key=self.manager.ensure()
            self.assertEqual(self.manager.backend_used,'cpu');self.assertTrue(key);self.assertGreater(port,0)
            args=process.call_args.args[0];self.assertIn('--offline',args);self.assertIn('--no-webui',args);self.assertIn('127.0.0.1',args);self.assertIn('none',args);self.assertEqual(process.call_args.kwargs['env']['LLAMA_API_KEY'],key)
            self.assertNotIn(key,' '.join(args))
    def test_archive_member_hashes_checked_and_no_traversal(self):
        archive=Path(self.temp.name)/'fixture.zip';out=Path(self.temp.name)/'runtime'
        with ZipFile(archive,'w') as z:z.writestr('../escape.exe',b'bad');z.writestr('llama-server.exe',b'fake executable')
        ai.extract_runtime(archive,out);self.assertEqual((out/'llama-server.exe').read_bytes(),b'fake executable');self.assertFalse((out.parent/'escape.exe').exists())
        with ZipFile(archive,'w') as z:z.writestr('llama-server.exe',b'FAKE executable')
        with self.assertRaises(ValueError):ai.extract_runtime(archive,out)
    def test_corrupt_settings_do_not_crash_startup(self):
        self.data.mkdir();(self.data/'local-ai.json').write_text('[]');self.assertFalse(ai.ManagedLocalAI(self.data).enabled)
    @unittest.skipUnless(os.name=='nt','Windows lifecycle guard')
    def test_windows_job_closes_its_own_runtime_process(self):
        process=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
        try:job=ai.WindowsJob(process);job.close();process.wait(timeout=10);self.assertIsNotNone(process.returncode)
        finally:
            if process.poll() is None:process.terminate();process.wait(timeout=5)
