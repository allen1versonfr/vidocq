import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from burn import BurnManager,mark_workspace,safe_root,OWNED_FILES

class BurnTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='Vidocq-burn-fixture-');self.root=Path(self.temp.name)/'workspace';self.root.mkdir()
        (self.root/'workspace.sqlite3').write_bytes(b'synthetic database fixture')
        (self.root/'personal-file.txt').write_text('Preserve this unrelated file.')
        self.manager=BurnManager(self.root)
    def tearDown(self):self.temp.cleanup()
    def test_preview_lists_only_owned_files_and_does_not_delete(self):
        p=self.manager.preview();names={Path(x['path']).name for x in p['files']}
        self.assertEqual(names,set(OWNED_FILES));self.assertEqual({Path(x['path']).name for x in p['files'] if x['exists']},{'workspace.sqlite3','.vidocq-owner.json'});self.assertTrue((self.root/'workspace.sqlite3').exists());self.assertFalse(p['remove_executable'])
        self.assertIn('backups',' '.join(p['limitations']))
    @unittest.skipUnless(os.name=='nt','Windows helper')
    def test_managed_ai_files_are_previewed_and_deleted_but_unknown_files_survive(self):
        from local_ai_assets import MODEL
        ai_root=self.root/'local-ai';runtime=ai_root/'runtime';runtime.mkdir(parents=True)
        model=ai_root/MODEL['filename'];model.write_bytes(b'synthetic model')
        (runtime/'llama-server.exe').write_bytes(b'synthetic executable')
        (ai_root/'private-notes.txt').write_text('Preserve unrelated data')
        (self.root/'local-ai.json').write_text('{"enabled":false}')
        plan=self.manager.preview();self.assertIn(str(model),[f['path'] for f in plan['files']])
        folder=self.helper(preserve_plan=True)
        try:
            self.assertFalse(model.exists());self.assertFalse((runtime/'llama-server.exe').exists());self.assertFalse((self.root/'local-ai.json').exists());self.assertTrue((ai_root/'private-notes.txt').exists());self.assertFalse(folder.exists())
        finally:
            if folder.exists():shutil.rmtree(folder)
    @unittest.skipUnless(os.name=='nt','Windows helper')
    def test_ai_prefix_does_not_allow_deleting_unowned_files(self):
        unknown=self.root/'local-ai'/'unowned.txt';unknown.parent.mkdir();unknown.write_text('Preserve')
        folder=self.helper(lambda p:p['files'].append({'path':str(unknown),'exists':True,'size':8}))
        try:self.assertTrue(unknown.exists());self.assertTrue((folder/'failure.txt').exists());self.assertTrue((self.root/'workspace.sqlite3').exists())
        finally:shutil.rmtree(folder)
    def test_refuses_roots_and_source_executable_removal(self):
        for path in [Path.home(),Path.cwd(),Path(Path.cwd().anchor)]:
            with self.assertRaises(ValueError):safe_root(path)
        with patch('burn.sys.frozen',False,create=True):
            with self.assertRaises(ValueError):self.manager.preview(True)
    def test_typed_confirmation_token_and_expiry_are_required(self):
        plan=self.manager.preview()
        for data in [{'token':plan['token'],'confirmation':'burn'},{'token':'wrong','confirmation':'BURN VIDOCQ'}]:
            with self.assertRaises(ValueError):self.manager.execute(data)
        self.manager.plan['created']-=301
        with self.assertRaises(ValueError):self.manager.execute({'token':plan['token'],'confirmation':'BURN VIDOCQ'})
        self.assertTrue((self.root/'workspace.sqlite3').exists())
    def test_changed_workspace_requires_new_preview(self):
        plan=self.manager.preview();(self.root/'startup.log').write_text('new log')
        with self.assertRaisesRegex(ValueError,'files changed'):self.manager.execute({'token':plan['token'],'confirmation':'BURN VIDOCQ'})
    def test_changed_owner_is_rejected(self):
        plan=self.manager.preview();(self.root/'.vidocq-owner.json').write_text(json.dumps({'application':'Vidocq','id':'replacement'}))
        with self.assertRaisesRegex(ValueError,'identity changed'):self.manager.execute({'token':plan['token'],'confirmation':'BURN VIDOCQ'})
    def test_symbolic_links_are_refused(self):
        link=Path(self.temp.name)/'linked-workspace'
        try:link.symlink_to(self.root,target_is_directory=True)
        except OSError:self.skipTest('Symlink creation unavailable on this runner.')
        with self.assertRaises(ValueError):BurnManager(link).preview()
    @unittest.skipUnless(os.name=='nt','Windows helper')
    def test_execute_schedules_hidden_helper_without_deleting_live_files(self):
        plan=self.manager.preview()
        with patch('burn.subprocess.Popen') as process:
            result=self.manager.execute({'token':plan['token'],'confirmation':'BURN VIDOCQ'})
        self.assertTrue(result['closing']);self.assertTrue(self.manager.pending);self.assertTrue((self.root/'workspace.sqlite3').exists())
        args=process.call_args.args[0];self.assertIn('Hidden',args);self.assertNotIn('-Command',args)
        job=Path(args[-1]);self.assertTrue(job.parent.name.startswith('Vidocq-burn-'));shutil.rmtree(job.parent)
    def helper(self,alter=None,preserve_plan=False):
        if not preserve_plan:self.manager.preview()
        plan=self.manager.plan
        folder=Path(tempfile.mkdtemp(prefix='Vidocq-burn-helper-fixture-'));script=folder/'cleanup.ps1';job=folder/'job.json'
        script.write_bytes(Path('scripts/burn_cleanup.ps1').read_bytes())
        data={**plan,'parent_pid':99999999,'helper_directory':str(folder)}
        if alter:alter(data)
        job.write_text(json.dumps(data),encoding='utf-8')
        subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script),'-Job',str(job)],check=True,timeout=30,capture_output=True)
        return folder
    @unittest.skipUnless(os.name=='nt','Windows helper')
    def test_real_helper_deletes_fixture_database_but_preserves_unknown_file(self):
        folder=self.helper()
        try:
            self.assertFalse((self.root/'workspace.sqlite3').exists());self.assertTrue((self.root/'personal-file.txt').exists());self.assertFalse(folder.exists())
        finally:
            if folder.exists():shutil.rmtree(folder)
    @unittest.skipUnless(os.name=='nt','Windows helper')
    def test_real_helper_rejects_out_of_scope_manifest_without_deleting_anything(self):
        sentinel=Path(self.temp.name)/'sentinel.txt';sentinel.write_text('Do not delete')
        folder=self.helper(lambda p:p['files'].append({'path':str(sentinel),'size':13}))
        try:
            self.assertTrue(sentinel.exists());self.assertTrue((self.root/'workspace.sqlite3').exists());self.assertTrue((folder/'failure.txt').exists())
        finally:shutil.rmtree(folder)
    @unittest.skipUnless(os.name=='nt','Windows helper')
    def test_real_helper_checks_and_removes_previewed_executable_and_backup(self):
        target=Path(self.temp.name)/'fixture.exe';target.write_bytes(b'MZ synthetic executable fixture')
        backup=target.with_name(target.name+'.previous');backup.write_bytes(b'MZ synthetic prior fixture')
        with patch('burn.sys.frozen',True,create=True),patch('burn.sys.executable',str(target)):
            self.manager.preview(True)
        folder=self.helper(preserve_plan=True)
        try:
            self.assertFalse(target.exists());self.assertFalse(backup.exists());self.assertFalse((self.root/'workspace.sqlite3').exists());self.assertTrue((self.root/'personal-file.txt').exists())
        finally:
            if folder.exists():shutil.rmtree(folder)
    @unittest.skipUnless(os.name=='nt','Windows helper')
    def test_changed_executable_hash_prevents_all_deletion(self):
        target=Path(self.temp.name)/'fixture.exe';target.write_bytes(b'MZ synthetic executable fixture')
        with patch('burn.sys.frozen',True,create=True),patch('burn.sys.executable',str(target)):
            self.manager.preview(True)
        target.write_bytes(b'MZ replaced fixture')
        folder=self.helper(preserve_plan=True)
        try:
            self.assertTrue(target.exists());self.assertTrue((self.root/'workspace.sqlite3').exists());self.assertIn('identity mismatch',(folder/'failure.txt').read_text())
        finally:shutil.rmtree(folder)
