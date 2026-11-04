import copy,json,sqlite3,tempfile,threading,time,unittest
import http.cookiejar,urllib.request,urllib.error,types
from http.server import ThreadingHTTPServer
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock,patch
import app
from ai_evidence import selections,validate
from benchmark_evaluation import validate_key,evaluate,compare_conditions
from child_environment import environment
from run_control import RunControl,CURRENT,reserve,timeout
from checker_health import CheckerHealth
from credential_vault import Vault
from automation_setup import AutomationSetup
from web_search import WebSearch
from case_reports import CaseService
from tests import test_automation as fixtures

class EvidenceContractTests(unittest.TestCase):
    def setUp(self):
        self.records=[{'id':'R1','excerpt':'Public profile bio links https://www.instagram.com/linkedfixture/','reference':'https://example.org/bio'},{'id':'R2','excerpt':'A separate public profile describes different fixture information.','reference':'https://example.net/bio'}]
        self.spans,self.links=selections(self.records)
    def test_id_only_outputs_reconstruct_exact_evidence(self):
        result=validate({'selection_ids':['R1-S1']},'synthesis',self.records,[],self.spans,self.links,[])
        self.assertEqual(result['claims'][0]['quote'],self.records[0]['excerpt'])
        result=validate({'link_ids':['R1-L1']},'leads',self.records,[],self.spans,self.links,[])
        self.assertEqual(result['leads'][0]['url'],'https://www.instagram.com/linkedfixture/')
    def test_invalid_item_does_not_discard_valid_selection(self):
        result=validate({'selection_ids':['R1-S1','missing']},'synthesis',self.records,[],self.spans,self.links,[])
        self.assertEqual(len(result['claims']),1);self.assertEqual(len(result['rejected_items']),1)
    def test_extra_model_action_is_clipped_without_losing_known_actions(self):
        result=validate({'comparisons':[],'next_step_indexes':[0,1,2,3]},'assessment',self.records,[],self.spans,self.links,['A','B','C','D'])
        self.assertEqual(result['next_steps'],['A','B','C']);self.assertEqual(len(result['rejected_items']),1)
    def test_mobile_profile_does_not_expand_to_a_platform_domain(self):
        from assisted_investigation import extract_clues
        result=extract_clues('https://m.instagram.com/fixture/',app.normalize)
        self.assertEqual(result,[{'kind':'instagram','value':'fixture'}])
    def test_selection_context_is_bounded_and_diverse(self):
        records=[{'id':'R'+str(i),'excerpt':'Public fixture biography. '*100,'reference':'https://example.org/'+str(i)} for i in range(12)]
        spans,_=selections(records)
        self.assertLessEqual(len(spans),24);self.assertEqual(len({s['citation'] for s in spans.values()}),12)
    def test_two_source_selection_and_temporal_observation_labels(self):
        payload={'comparisons':[{'type':'difference','selection_ids':['R1-S1','R2-S1']}],'next_step_indexes':[]}
        result=validate(payload,'assessment',self.records,[],self.spans,self.links,[])
        self.assertTrue(result['comparisons'][0]['independent_sources'])
        self.records[1]['reference']=self.records[0]['reference']
        result=validate(payload,'assessment',self.records,[],self.spans,self.links,[])
        self.assertFalse(result['comparisons'][0]['independent_sources'])
    def test_child_environment_excludes_unrelated_secrets(self):
        with patch.dict('os.environ',{'OPENAI_API_KEY':'fixture-secret','VIDOCQ_BRAVE_API_KEY':'fixture-secret','PATH':'fixture-path'},clear=True):
            result=environment({'LLAMA_API_KEY':'explicit-runtime-key'})
        self.assertEqual(result,{'PATH':'fixture-path','LLAMA_API_KEY':'explicit-runtime-key'})
    def test_run_deadline_cancel_and_budget_are_independent(self):
        flag=threading.Event();control=RunControl(10,flag,1);token=CURRENT.set(control)
        try:
            reserve('brave')
            with self.assertRaisesRegex(ValueError,'request limit'):reserve('brave')
            reserve('serper');flag.set()
            with self.assertRaisesRegex(ValueError,'cancelled'):timeout()
            flag.clear();control.deadline=time.monotonic()-1
            with self.assertRaisesRegex(ValueError,'deadline'):timeout()
        finally:CURRENT.reset(token)

class EvaluationTests(unittest.TestCase):
    def key(self):return {'accounts':[{'id':'seed','role':'seed','canonical_url':'https://github.com/seedfixture','ownership':'confirmed','public_visibility':'public','public_verified_on':date.today().isoformat()},{'id':'found','role':'withheld','canonical_url':'https://www.instagram.com/linkedfixture','ownership':'confirmed','public_visibility':'public','public_verified_on':date.today().isoformat()},{'id':'wrong','role':'negative','canonical_url':'https://github.com/wrongfixture','ownership':'rejected'}]}
    def report(self):return {'status':'complete','case':{'names':['Fixture Person']},'records':[{'id':'R1','reference':'https://github.com/seedfixture'},{'id':'R2','reference':'https://www.instagram.com/linkedfixture/'},{'id':'R3','reference':'https://github.com/wrongfixture'},{'id':'R4','reference':'https://github.com/unknownfixture'}]}
    def test_key_preflight_rejects_accidental_missing_url(self):
        key=self.key();key['accounts'][1].pop('canonical_url')
        with self.assertRaisesRegex(ValueError,'missing profile URL'):validate_key(key)
        key['accounts'][1]['exclude_reason']='Unavailable URL; intentionally excluded';self.assertTrue(validate_key(key)['warnings'])
    def test_seeds_wrong_and_unresolved_are_separate(self):
        result=evaluate(self.report(),self.key())
        self.assertEqual(result['new_known_list_matches'],['found']);self.assertEqual(result['seed_rediscoveries'],['seed'])
        self.assertEqual(result['negative_matches'],['wrong']);self.assertEqual(result['public_account_recall'],1)
        self.assertEqual(result['resolved_candidate_precision'],.5);self.assertEqual(result['unresolved_candidate_profiles'],1)
    def test_unverified_key_never_invents_recall(self):
        key=self.key();key['accounts'][1].pop('public_verified_on')
        self.assertIsNone(evaluate(self.report(),key)['public_account_recall'])
    def test_scoring_requires_sealed_reports_and_marks_condition_changes(self):
        run=self.report();run['status']='running'
        with self.assertRaises(ValueError):evaluate(run,self.key())
        first=self.report();second=copy.deepcopy(first);second['case']['names']=['Different Fixture']
        self.assertFalse(compare_conditions([('A',first),('B',second)],self.key())['same_starting_clues'])

class WorkflowTests(unittest.TestCase):
    setUp=fixtures.EngineTests.setUp
    tearDown=fixtures.EngineTests.tearDown
    make=fixtures.EngineTests.make
    run_case=fixtures.EngineTests.run_case
    research=fixtures.EngineTests.research
    context=fixtures.EngineTests.context
    def test_report_preserves_rank_manifest_and_request_roles(self):
        self.service.configuration=lambda:{'search':{'provider':'brave'},'contract_version':2}
        self.service.research=lambda k,v:{'results':[{'provider':'Fixture','status':'ok','rows':[{'title':'Example Person example','detail':'Public fixture biography','reference':'https://www.instagram.com/example/','index_rank':4}]}],'links':[]}
        run=self.run_case(self.make(urls=['https://www.instagram.com/example/'],investigation={'enabled':True,'allow_maigret':False}))
        self.assertEqual(run['records'][0]['retrieval']['rank'],4)
        self.assertEqual(run['research_configuration']['search']['provider'],'brave')
        self.assertEqual(run['records'][0]['discovery_role'],'seed');self.assertEqual(run['summary']['new_candidate_accounts'],0)
        self.assertNotIn('records',self.service.progress(run['id']));self.assertNotIn('records',self.service.runs(run['case_id'],True)[0])
    def test_reused_pid_with_wrong_creation_identity_is_interrupted(self):
        import os
        case=self.make();key='d'*24
        with self.service.database() as db:db.execute('INSERT INTO case_runs VALUES (?,?,?)',(key,case['id'],json.dumps({'id':key,'case_id':case['id'],'owner_pid':os.getpid(),'owner_birth':'wrong-creation-time','status':'running','records':[]})))
        self.service.initialize();self.assertEqual(self.service.run(key)['status'],'interrupted')

class PersistenceTests(unittest.TestCase):
    def test_brave_saved_connection_restores_without_queries(self):
        import os
        if os.name!='nt':self.skipTest('Windows DPAPI')
        with tempfile.TemporaryDirectory() as temp:
            web=WebSearch();setup=AutomationSetup(temp,web,MagicMock(),MagicMock(),MagicMock())
            setup.search({'provider':'brave','key':'synthetic-brave-key','enabled':True,'remember':True})
            self.assertNotIn(b'synthetic-brave-key',Path(temp,'credentials.dpapi').read_bytes())
            restored=WebSearch();other=AutomationSetup(temp,restored,MagicMock(),MagicMock(),MagicMock());other.choices['mwmbl']=True
            with patch('web_search.build_opener') as network:other._start();network.assert_not_called()
            self.assertEqual(restored.provider,'brave');self.assertTrue(restored.enabled)
            other.search({'provider':'mwmbl','enabled':True,'remember':False});self.assertEqual(other.search_status()['next_start_provider'],'brave')
    def test_checker_pair_must_share_fingerprint(self):
        with tempfile.TemporaryDirectory() as temp:
            client=MagicMock();client.quarantined_sites={'GitHub':'held'}
            def response(outcome,fingerprint):return {'results':[{'checks':[{'site':'GitHub','outcome':outcome,'diagnostics':{'checker_sha256':fingerprint,'maigret_version':'fixture'}}]}]}
            client.maigret.side_effect=[response('candidate','A'),response('absent','B'),response('candidate','B')]
            health=CheckerHealth(temp,client);p={'site':'GitHub','username':'fixture','expected':'candidate','public_verified_on':date.today().isoformat(),'public_verified':True,'consent':True}
            health.run(p);self.assertNotEqual(health.run({**p,'expected':'absent'})['state'],'passed');self.assertIn('GitHub',client.quarantined_sites)
            self.assertEqual(health.run(p)['state'],'passed');self.assertNotIn('GitHub',client.quarantined_sites)

class RouteGuardTests(unittest.TestCase):
    def test_active_report_blocks_configuration_mutations(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        client=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));base='http://127.0.0.1:'+str(server.server_port)
        try:
            client.open(base+'/').read()
            with patch.object(app,'CASES',types.SimpleNamespace(active='fixture',lock=threading.RLock())),patch.object(app.AUTOMATION,'search') as mutation:
                for route in ['search-connection','collectors','connectors','local-ai/settings']:
                    request=urllib.request.Request(base+'/api/'+route,data=b'{}',headers={'Content-Type':'application/json'})
                    with self.assertRaises(urllib.error.HTTPError) as error:client.open(request)
                    self.assertEqual(error.exception.code,409)
                mutation.assert_not_called()
        finally:server.shutdown();server.server_close();thread.join(3)
