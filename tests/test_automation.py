import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
from urllib.parse import quote
from datetime import date
from credential_vault import Vault
from browser_bridge import BrowserBridge,parse_capture,register,unregister
from companion_scope import harvester_request
from checker_health import CheckerHealth
from tests import test_discovery_review as fixtures

class ScopeTests(unittest.TestCase):
    def test_passive_request_rejects_active_flags_unknown_fields_and_unbounded_limits(self):
        good={'target':'example.org','sources':['crtsh'],'limit':50,'source_workers':1,'deadline_seconds':60}
        self.assertEqual(harvester_request(good),good)
        for changes in [{'dns_resolve':True},{'screenshot':True},{'sources':['all']},{'target':'https://example.org'},{'limit':0},{'source_workers':4},{'deadline_seconds':3600},{'proxies':True}]:
            with self.assertRaises(ValueError):harvester_request({**good,**changes})

class CredentialTests(unittest.TestCase):
    @unittest.skipUnless(os.name=='nt','Windows DPAPI')
    def test_secret_persists_encrypted_and_can_be_forgotten(self):
        with tempfile.TemporaryDirectory() as temp:
            vault=Vault(temp);secret='synthetic-hiker-key-for-tests';vault.save(secret)
            self.assertNotIn(secret.encode(),vault.path.read_bytes());self.assertTrue(vault.status()['saved'])
            self.assertEqual(Vault(temp).load()['hiker_key'],secret)
            vault.forget();self.assertFalse(vault.path.exists())
    def test_invalid_key_is_never_written(self):
        with tempfile.TemporaryDirectory() as temp:
            vault=Vault(temp)
            with self.assertRaises(ValueError):vault.save('bad')
            self.assertFalse(vault.path.exists())

class BrowserTests(unittest.TestCase):
    def payload(self):return {'case_id':'a'*24,'data':{'schema':'vidocq-browser-v1','title':'Reviewed public bio','reference':'https://example.org/bio','excerpt':'Selected public text.','links':['https://www.tiktok.com/@different_handle']}}
    def test_uri_decoding_pending_review_and_expiry(self):
        with tempfile.TemporaryDirectory() as temp:
            value=self.payload();uri='vidocq-evidence://capture?data='+quote(json.dumps(value));self.assertEqual(parse_capture(uri),value)
            bridge=BrowserBridge(temp);bridge.receive(value);self.assertEqual(bridge.list()[0]['data']['excerpt'],'Selected public text.')
            key=bridge.list()[0]['id'];self.assertEqual(bridge.pop(key)['case_id'],'a'*24);self.assertEqual(bridge.list(),[])
            with self.assertRaises(ValueError):bridge.pop(key)
            bridge.receive(value);bridge.pending[0]['created']-=601;self.assertEqual(bridge.list(),[])
            self.assertFalse(list(Path(temp).glob('*.json')),'Captures should remain in memory pending approval.')
    def test_review_can_retry_after_save_failure_and_other_relay_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            bridge=BrowserBridge(temp);bridge.receive(self.payload());key=bridge.list()[0]['id']
            self.assertEqual(bridge.peek(key)['case_id'],'a'*24);self.assertEqual(len(bridge.list()),1)
            bridge.publish(12345);other=BrowserBridge(temp);other.publish(12346)
            bridge.close();self.assertTrue((Path(temp)/'browser-relay.json').exists())
            other.close();self.assertFalse((Path(temp)/'browser-relay.json').exists())
    def test_invalid_uri_and_local_source_refused(self):
        for uri in ['http://example.org','vidocq-evidence://other?data={}']:
            with self.assertRaises(ValueError):parse_capture(uri)
        value=self.payload();value['data']['reference']='https://127.0.0.1/'
        with self.assertRaises(ValueError):parse_capture('vidocq-evidence://capture?data='+quote(json.dumps(value)))
    @unittest.skipUnless(os.name=='nt','Windows native protocol')
    def test_user_protocol_registration_and_owned_cleanup(self):
        import uuid,winreg
        name='vidocq-test-'+uuid.uuid4().hex
        register(executable=Path('fixture.exe').resolve(),scheme=name)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Software\\Classes\\'+name+'\\shell\\open\\command') as key:self.assertIn('--browser-capture',winreg.QueryValueEx(key,'')[0])
        unregister(executable=Path('different.exe').resolve(),scheme=name)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Software\\Classes\\'+name):pass
        unregister(executable=Path('fixture.exe').resolve(),scheme=name)
        with self.assertRaises(FileNotFoundError):winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Software\\Classes\\'+name)

class EngineTests(unittest.TestCase):
    setUp=fixtures.ReviewCaseTests.setUp
    tearDown=fixtures.ReviewCaseTests.tearDown
    research=fixtures.ReviewCaseTests.research
    context=fixtures.ReviewCaseTests.context
    make=fixtures.ReviewCaseTests.make
    run_case=fixtures.ReviewCaseTests.run_case
    def test_ai_queries_execute_and_cited_draft_is_exported(self):
        class Model:
            def generate(inner,case,run,mode,consent):
                if mode=='planning':return {'queries':[{'terms':['Example Person','example'],'reason':'supplied identifiers'}]}
                if mode=='leads':return {'leads':[]}
                record=run['records'][0];return {'claims':[{'citation':record['id'],'quote':'Reviewed public profile','text':'The supplied excerpt describes a public profile.'}]}
        self.service.llm=Model();case=self.make(investigation={'enabled':True,'ai_assisted':True,'allow_maigret':False,'max_searches':5})
        self.service.browser_capture(case['id'],{'consent':True,'title':'Public fixture','reference':'https://example.org/bio','excerpt':'Reviewed public profile for Example Person.'},self.notebook.save_finding)
        run=self.run_case(case);self.assertEqual(run['ai']['executed_queries'],1);self.assertIn(['Example Person','example'],self.contexts);self.assertTrue(run['ai']['summary']['claims'])
        from case_reports import report_markdown
        self.assertIn('AI-assisted findings',report_markdown(run))
    def test_reviewed_public_link_follows_different_handle_with_parent_citation(self):
        case=self.make(investigation={'enabled':True,'follow_published_links':True,'follow_clues':True,'depth':1,'max_followups':2,'allow_maigret':True,'maigret_sites':['TikTok']})
        from discovery_tools import import_links
        data=import_links({'mode':'browser','data':{'schema':'vidocq-browser-v1','title':'Linked account','reference':'https://example.org/bio','excerpt':'A reviewed public link.','links':['https://www.tiktok.com/@different_handle']}})
        self.service.link_capture(case['id'],data,self.notebook.save_finding)
        run=self.run_case(case);self.assertIn(('tiktok','different_handle'),self.calls)
        task=next(t for t in run['search_log'] if t['origin']=='approved-published-link');self.assertTrue(task['parent_citation'])
        self.collectors.maigret.assert_any_call('different_handle',run['id'],['TikTok'])
        self.assertFalse(run['link_evidence'][0]['ownership_verified'])
    def test_ai_failure_is_a_visible_gap_and_does_not_stop_deterministic_searches(self):
        self.service.llm=MagicMock();self.service.llm.generate.side_effect=ValueError('Model unavailable')
        run=self.run_case(self.make(investigation={'enabled':True,'ai_assisted':True,'allow_maigret':False}))
        self.assertEqual(run['status'],'complete');self.assertTrue(self.calls);self.assertEqual(run['coverage_assessment']['status'],'incomplete');self.assertIn('Model unavailable',run['ai']['errors'])

class HealthTests(unittest.TestCase):
    def test_verified_control_mismatch_disables_checker_until_control_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            client=MagicMock();client.quarantined_sites={};client.maigret.return_value={'results':[{'checks':[{'site':'GitHub','outcome':'absent'}]}]}
            health=CheckerHealth(temp,client);payload={'site':'GitHub','username':'publicfixture','expected':'candidate','public_verified_on':date.today().isoformat(),'public_verified':True,'consent':True}
            self.assertEqual(health.run(payload)['state'],'control-mismatch');self.assertIn('GitHub',client.quarantined_sites)
            client.maigret.return_value={'results':[{'checks':[{'site':'GitHub','outcome':'blocked'}]}]}
            health.run(payload);restored=MagicMock();restored.quarantined_sites={};CheckerHealth(temp,restored)
            self.assertIn('GitHub',restored.quarantined_sites,'Unavailable retries must not clear a previous mismatch.')
            client.maigret.return_value={'results':[{'checks':[{'site':'GitHub','outcome':'candidate'}]}]}
            self.assertEqual(health.run(payload)['state'],'partial-validation');self.assertIn('GitHub',client.quarantined_sites)
            client.maigret.return_value={'results':[{'checks':[{'site':'GitHub','outcome':'absent'}]}]}
            self.assertEqual(health.run({**payload,'username':'absentfixture','expected':'absent'})['state'],'passed');self.assertNotIn('GitHub',client.quarantined_sites)
            with self.assertRaises(ValueError):health.run({**payload,'public_verified':False})

class ManagedTests(unittest.TestCase):
    def test_changed_bundled_binary_never_executes(self):
        from managed_collectors import ManagedCollectors
        with tempfile.TemporaryDirectory() as temp:
            bundle=Path(temp)/'bundle';bundle.mkdir();(bundle/'photon.exe').write_bytes(b'changed')
            (bundle/'manifest.json').write_text(json.dumps({'photon':{'size':7,'sha256':'0'*64}}))
            manager=ManagedCollectors(Path(temp)/'data',bundle)
            with patch('managed_collectors.subprocess.Popen') as launch:
                with self.assertRaisesRegex(ValueError,'integrity'):manager.ensure('photon')
                launch.assert_not_called()
    def test_startup_restores_choices_without_lookups_and_disabling_is_persisted(self):
        from automation_setup import AutomationSetup
        with tempfile.TemporaryDirectory() as temp:
            Path(temp,'automations.json').write_text(json.dumps({'mwmbl':True,'maigret':True}))
            web,collectors,connectors,ai=[MagicMock() for _ in range(4)]
            setup=AutomationSetup(temp,web,collectors,connectors,ai);setup.manager=MagicMock();setup.start();setup.worker.join(3)
            web.configure.assert_called_once_with({'provider':'mwmbl','enabled':True});collectors.setup_maigret.assert_called_once()
            collectors.maigret.assert_not_called();connectors.osintgram.assert_not_called();ai.setup.assert_not_called()
            setup.apply({'consent':True});setup.worker.join(3)
            self.assertFalse(any(json.loads(Path(temp,'automations.json').read_text()).values()))

class PhotonTests(unittest.TestCase):
    def test_actual_runner_transport_enforces_scope_robots_and_attempt_budget(self):
        import types,requests
        from scripts.photon_companion import collect
        core=types.ModuleType('core');utils=types.ModuleType('core.utils');zap=types.ModuleType('core.zap')
        utils.writer=MagicMock();zap.zap=MagicMock();core.utils=utils;core.zap=zap
        fetched=[];statuses=[]
        def fetch(url):
            fetched.append(url)
            if url.endswith('robots.txt'):return 'User-agent: *\nDisallow: /private'
            if url.endswith('/fail'):raise ValueError('Synthetic unavailable page')
            return '<a href="https://github.com/example">Published account</a>'
        def photon(*args,**kwargs):
            for url in ['https://example.org/','https://example.org/private','https://example.org/logout','https://elsewhere.org/','https://example.org/fail','https://example.org/extra']:
                statuses.append(requests.get(url).status_code)
        original=requests.sessions.Session.request
        with patch.dict('sys.modules',{'core':core,'core.utils':utils,'core.zap':zap}),patch('scripts.photon_companion.runpy.run_path',side_effect=photon),patch('scripts.photon_companion.time.sleep'):
            result=collect({'consent':True,'url':'https://example.org','pages':2,'depth':2},fetch)
        self.assertEqual(fetched,['https://example.org/robots.txt','https://example.org/','https://example.org/fail'])
        self.assertEqual(statuses,[200,404,404,404,404,404]);self.assertEqual(len(result['pages']),1)
        self.assertEqual(result['edges'][0]['target'],'https://github.com/example');self.assertEqual(len(result['pages'][0]['sha256']),64)
        self.assertIs(requests.sessions.Session.request,original);utils.writer.assert_not_called();zap.zap.assert_not_called()
    def test_permission_and_robots_failure_prevent_crawl(self):
        from scripts.photon_companion import collect
        with patch('scripts.photon_companion.runpy.run_path') as run:
            with self.assertRaises(ValueError):collect({'url':'https://example.org'})
            with self.assertRaises(ValueError):collect({'url':'https://example.org','consent':True},lambda url:(_ for _ in ()).throw(ValueError('No robots permission')))
            run.assert_not_called()
