import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from urllib.request import Request
from urllib.error import HTTPError
import updater as u

PAYLOAD = b'MZ' + b'new-executable' * 100
DIGEST = hashlib.sha256(PAYLOAD).hexdigest()
def release(**overrides):
    r = {'tag_name':'v2.4.0', 'draft':False, 'prerelease':False, 'body':'Notes', 'assets':[
        {'id':123,'name':'Vidocq.exe','state':'uploaded','size':len(PAYLOAD),'digest':'sha256:'+DIGEST}]}
    r.update(overrides)
    return r

class ReleaseTests(unittest.TestCase):
    def test_numeric_versions(self):
        self.assertGreater(u.version_tuple('v2.10.0'),u.version_tuple('2.9.9'))
        self.assertIsNone(u.select_release(release(tag_name='v2.3.0')))
        self.assertIsNone(u.select_release(release(tag_name='v2.2.1')))
    def test_bad_version_and_unstable(self):
        for tag in ['latest','v2.4.0-beta','v02.4.0','2.4','2.4.0;evil']:
            with self.assertRaises(ValueError):u.version_tuple(tag)
        for r in [release(draft=True),release(prerelease=True)]:
            with self.assertRaises(ValueError):u.select_release(r)
    def test_exact_asset_and_digest(self):
        for change in [{'name':'other.exe'},{'digest':None},{'size':0},{'id':'123'},{'state':'new'}]:
            r=release();r['assets'][0].update(change)
            with self.assertRaises(ValueError):u.select_release(r)
        r=release();r['assets']*=2
        with self.assertRaises(ValueError):u.select_release(r)
    def test_asset_url_is_derived(self):
        r=release();r['assets'][0]['url']='https://evil.test/exe'
        self.assertEqual(u.select_release(r)['asset_url'],u.API+'/releases/assets/123')
    def test_redirect_allowlist(self):
        for url in ['http://github.com/x','https://github.com.evil.test/x','https://x@y.github.com/x','https://github.com:8443/x','file:///x']:
            with self.assertRaises(ValueError):u.checked_url(url)
    def test_token_not_forwarded_to_cdn(self):
        req=Request(u.API+'/releases/assets/123',headers={'Authorization':'Bearer secret'})
        redirected=u.SafeRedirect().redirect_request(req,None,302,'',{},'https://release-assets.githubusercontent.com/path')
        self.assertIsNone(redirected.get_header('Authorization'))
    def test_private_repository_message(self):
        with patch.object(u,'open_github',side_effect=HTTPError(u.API,404,'',{},None)):
            with self.assertRaisesRegex(ValueError,'Contents: read'):u.fetch_release()

class DownloadTests(unittest.TestCase):
    def test_valid_download_and_progress(self):
        with tempfile.TemporaryDirectory() as t, patch.object(u,'open_github',return_value=io.BytesIO(PAYLOAD)):
            path=Path(t)/'Vidocq.exe';progress=[]
            u.download_release(u.select_release(release()),path,progress=progress.append)
            self.assertEqual(path.read_bytes(),PAYLOAD);self.assertEqual(progress[-1],len(PAYLOAD))
    def test_corrupt_truncated_and_oversize_never_install(self):
        for payload in [PAYLOAD[:-1],b'MZ'+b'x'*(len(PAYLOAD)-2),PAYLOAD+b'x']:
            with tempfile.TemporaryDirectory() as t, patch.object(u,'open_github',return_value=io.BytesIO(payload)):
                path=Path(t)/'Vidocq.exe'
                with self.assertRaises(ValueError):u.download_release(u.select_release(release()),path)
                self.assertFalse(path.exists());self.assertFalse(path.with_suffix('.partial').exists())
    def test_non_executable_rejected_even_with_matching_hash(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x';p.write_bytes(b'not an exe')
            with self.assertRaises(ValueError):u.verify_executable(p,p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest())

class InstallationTests(unittest.TestCase):
    def setup_job(self,root):
        target=root/'Vidocq.exe';target.write_bytes(b'MZold')
        staged=root/'new.exe';staged.write_bytes(PAYLOAD)
        job={'target':str(target),'staged':str(staged),'size':len(PAYLOAD),'sha256':DIGEST,
             'version':'2.4.0','parent_pid':0,'ready':str(root/'ready'),'result':str(root/'result.json'),'ready_timeout':0}
        p=root/'job.json';p.write_text(json.dumps(job));return p,job
    def test_success_keeps_backup_and_notebook(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p,j=self.setup_job(root);notebook=root/'workspace.sqlite3';notebook.write_bytes(b'notebook')
            def start(*a,**kw):Path(j['ready']).touch();return Mock()
            with patch.object(u,'wait_for_parent'),patch.object(u.subprocess,'Popen',side_effect=start):
                self.assertEqual(u.apply_update(p),0)
            self.assertEqual(Path(j['target']).read_bytes(),PAYLOAD)
            self.assertEqual((root/'Vidocq.exe.previous').read_bytes(),b'MZold')
            self.assertEqual(notebook.read_bytes(),b'notebook')
    def test_failed_start_rolls_back(self):
        with tempfile.TemporaryDirectory() as t:
            p,j=self.setup_job(Path(t));child=Mock();child.poll.return_value=1
            with patch.object(u,'wait_for_parent'),patch.object(u.subprocess,'Popen',return_value=child):
                self.assertEqual(u.apply_update(p),1)
            self.assertEqual(Path(j['target']).read_bytes(),b'MZold')
            self.assertEqual(json.loads(Path(j['result']).read_text())['status'],'failed')
    def test_corruption_keeps_existing_app(self):
        with tempfile.TemporaryDirectory() as t:
            p,j=self.setup_job(Path(t));Path(j['staged']).write_bytes(b'corrupt')
            with patch.object(u.subprocess,'Popen') as popen:self.assertEqual(u.apply_update(p),1);popen.assert_not_called()
            self.assertEqual(Path(j['target']).read_bytes(),b'MZold')
    def test_install_failure_after_backup_rolls_back(self):
        with tempfile.TemporaryDirectory() as t:
            p,j=self.setup_job(Path(t));replace=u.replace_retry
            def fail(source,target,**kw):
                if str(source).endswith('.incoming'):raise PermissionError('locked')
                replace(source,target,**kw)
            with patch.object(u,'wait_for_parent'),patch.object(u,'replace_retry',side_effect=fail),patch.object(u.subprocess,'Popen'):
                self.assertEqual(u.apply_update(p),1)
            self.assertEqual(Path(j['target']).read_bytes(),b'MZold')

class ManagerTests(unittest.TestCase):
    def test_token_stays_out_of_status(self):
        with tempfile.TemporaryDirectory() as t:
            manager=u.UpdateManager(t);manager.token='very-secret'
            self.assertNotIn('very-secret',json.dumps(manager.status()))
    def test_prevent_duplicate_work_and_out_of_order_install(self):
        with tempfile.TemporaryDirectory() as t:
            manager=u.UpdateManager(t)
            with self.assertRaises(ValueError):manager.install()
            manager.state['phase']='downloading'
            with self.assertRaises(ValueError):manager.check()
    def test_offline_error_is_actionable(self):
        with tempfile.TemporaryDirectory() as t,patch.object(u,'fetch_release',side_effect=OSError('private internals')):
            manager=u.UpdateManager(t);manager._check()
            self.assertEqual(manager.status()['phase'],'error');self.assertNotIn('private internals',manager.status()['message'])
