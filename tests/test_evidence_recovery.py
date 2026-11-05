import copy,json,threading,unittest
from unittest.mock import patch,MagicMock
from urllib.parse import urlparse,parse_qs
from web_search import WebSearch
from run_control import CURRENT,RunControl
from evidence_quality import evidence_excerpt,evidence_gate
from profile_leads import indexed_profile_links,historical_edges
from profile_registry import supplied_profiles
from discovery_tools import query_plan,import_links
from profile_evidence import capture_profile,reviewed_profile
from assisted_investigation import options,synthesis
from benchmark_diagnostics import diagnose_misses
from benchmark_evaluation import evaluate,compare_conditions
from tests import test_automation as fixtures
from research_workflow import review_plan

class RecoveryTests(unittest.TestCase):
    def test_case_depth_and_extra_snippets_are_isolated_from_saved_connection(self):
        web=WebSearch();web.configure({'provider':'brave','key':'synthetic-key','enabled':True})
        data={'query':{},'web':{'results':[{'title':'Fixture','url':'https://instagram.com/publicfixture','description':'Public fixture biography','extra_snippets':['Explicit link https://tiktok.com/@otherfixture']}]}}
        response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps(data).encode()
        token=CURRENT.set(RunControl(60,threading.Event(),5,20,True))
        try:
            with patch('web_search.build_opener') as opener:
                opener.return_value.open.return_value=response;result=web.search('publicfixture')
                params=parse_qs(urlparse(opener.return_value.open.call_args.args[0].full_url).query)
            self.assertEqual(params['count'],['20']);self.assertEqual(params['extra_snippets'],['true'])
            self.assertIn('otherfixture',result[1][0]['detail']);self.assertEqual(result.diagnostics['result_limit'],20)
        finally:CURRENT.reset(token)
        self.assertEqual(web.brave_result_limit,10)
        with patch('web_search.build_opener') as opener:
            opener.return_value.open.return_value=response;shallow=web.search('publicfixture')
            self.assertEqual(opener.return_value.open.call_count,1)
        self.assertNotIn('otherfixture',shallow[1][0]['detail'])
    def test_case_search_options_fail_closed(self):
        self.assertEqual(options({})['index_depth'],0)
        for payload in [{'index_depth':True},{'index_depth':30},{'extra_snippets':'yes'},{'follow_indexed_links':1}]:
            with self.assertRaises(ValueError):options(payload)
    def test_long_evidence_window_keeps_late_identifiers_verbatim(self):
        text='Unrelated introduction. '*150+'Alex Fixture has a public biography and explicit profile links. '+'Source ending. '*150
        window=evidence_excerpt({'detail':text},{'names':['Alex Fixture']})
        self.assertGreater(window['start'],0);self.assertIn('Alex Fixture',window['text'])
        self.assertEqual(window['text'],text[window['start']:window['end']]);self.assertLessEqual(len(window['text']),1500)
    def test_index_links_require_a_supplied_identifier_profile_and_explicit_urls(self):
        case={'urls':['https://instagram.com/publicfixture']}
        row={'id':'R1','reference':'https://www.instagram.com/publicfixture/','detail':'Public bio links https://tiktok.com/@otherfixture and https://tiktok.com/@otherfixture?lang=en; https://tiktok.com.evil.example/@wrong','title':'Public fixture'}
        edges=indexed_profile_links(case,row);self.assertEqual(len(edges),1);self.assertEqual(edges[0]['relation'],'indexed-snippet-link');self.assertFalse(edges[0]['ownership_verified'])
        self.assertFalse(indexed_profile_links({},row));self.assertFalse(indexed_profile_links(case,dict(row,analyst_status='Rejected')))
    def test_historical_queries_and_edges_use_only_supplied_evidence(self):
        alias={'handle':'oldfixture','platform':'Instagram','reference':'https://example.org/dated-note','successor':'https://instagram.com/newfixture','first_seen':'2020-01-01','last_seen':'2021-01-01'}
        case={'aliases':[alias]};terms=[q['terms'] for q in query_plan(case)]
        self.assertIn([alias['reference']],terms);self.assertIn([alias['successor']],terms)
        edge=historical_edges([alias])[0];self.assertEqual(edge['last_seen'],'2021-01-01');self.assertEqual(edge['evidence_reference'],alias['reference']);self.assertFalse(edge['ownership_verified'])
        self.assertFalse(historical_edges([dict(alias,successor='https://tiktok.com/@newfixture')]))
        self.assertEqual(supplied_profiles(case),{'https://instagram.com/oldfixture','https://instagram.com/newfixture'})
    def test_supplied_successor_cannot_be_counted_as_a_new_candidate(self):
        case={'aliases':[{'handle':'oldfixture','platform':'Instagram','successor':'https://instagram.com/newfixture'}]}
        row={'id':'R1','title':'New fixture','reference':'https://instagram.com/newfixture','detail':'Public account','relevance':{'matched_identifiers':[]}}
        result=synthesis({'case':case,'records':[row]})
        self.assertEqual(row['discovery_role'],'seed');self.assertEqual(result['counts']['new_candidate_accounts'],0)
        self.assertFalse(evidence_gate(dict(row,assertion_only=True),case)['eligible'])
        self.assertFalse(evidence_gate(dict(row,origin='explicit-linked-profile'),case)['eligible'])
    def test_bio_link_punctuation_does_not_change_the_account_url(self):
        capture=reviewed_profile({'consent':True,'public_reviewed':True,'reference':'https://instagram.com/publicfixture','biography':'Public profile (https://tiktok.com/@linkedfixture).','links':[]})
        self.assertEqual(capture['edges'][0]['target'],'https://tiktok.com/@linkedfixture')
    def test_structured_sameas_links_require_a_matching_person_reference(self):
        ref='https://example.org/profile'
        graph={'@graph':[{'@type':'Person','url':ref,'description':'Alex Fixture public biography.','sameAs':['https://instagram.com/publicfixture']},{'@type':'Person','url':'https://example.org/elsewhere','sameAs':['https://tiktok.com/@unrelatedfixture']},{'@type':'Organization','url':ref,'sameAs':['https://github.com/footerfixture']}]}
        body='<title>Public profile</title><script type="application/ld+json">'+json.dumps(graph)+'</script><a href="https://github.com/footerfixture">Footer</a>'
        result=capture_profile({'consent':True,'reference':ref},lambda url:'User-agent: *\nAllow: /' if url.endswith('robots.txt') else body)
        self.assertEqual(result['profile']['links'],['https://instagram.com/publicfixture'])
        self.assertFalse(any(e['target']=='https://tiktok.com/@unrelatedfixture' for e in result['edges']))
        self.assertEqual(next(e for e in result['edges'] if 'instagram' in e['target'])['link_origin'],'structured-person-sameAs')
    def test_review_plan_keeps_scoped_and_unscoped_history_distinct(self):
        case={'id':'fixture','names':['Alex Fixture'],'usernames':['publicfixture']}
        run={'id':'old','search_log':[{'kind':'context','value':['publicfixture'],'site':'instagram.com','status':'completed'}]}
        queries=review_plan(case,run)['queries']
        self.assertTrue(next(q for q in queries if q.get('site')=='instagram.com' and q['terms']==['publicfixture'])['previously_attempted'])
        self.assertFalse(next(q for q in queries if not q.get('site') and q['terms']==['publicfixture'])['previously_attempted'])
    def test_alias_successors_and_note_urls_cannot_receive_withheld_credit(self):
        key={'accounts':[{'id':'A1','role':'withheld','canonical_url':'https://instagram.com/newfixture'}]}
        for case in [{'aliases':[{'handle':'oldfixture','platform':'Instagram','successor':'https://instagram.com/newfixture'}]},{'notes':'Starting clue https://instagram.com/newfixture'}]:
            report={'status':'complete','case':case,'records':[{'id':'R1','reference':'https://instagram.com/newfixture'}]}
            score=evaluate(report,key);self.assertFalse(score['blind_score_valid']);self.assertEqual(score['new_known_list_matches'],[])
            self.assertEqual(diagnose_misses(report,key)['accounts'][0]['stage'],'key-starting-clue-conflict')
        from datetime import date
        key['accounts'].append({'id':'A2','role':'withheld','canonical_url':'https://instagram.com/otherfixture','ownership':'confirmed','public_visibility':'public','public_verified_on':date.today().isoformat()})
        report['records'].append({'id':'R2','reference':'https://instagram.com/otherfixture'})
        self.assertIsNone(evaluate(report,key)['public_account_recall'])
    def test_changed_reviewed_evidence_is_a_different_comparison_condition(self):
        key={'accounts':[{'id':'A1','role':'withheld','canonical_url':'https://instagram.com/newfixture'}]}
        first={'status':'complete','case':{},'records':[],'supplied_findings':[]};second=dict(first,supplied_findings=[{'id':'F1','notes':'Reviewed public bio'}])
        result=compare_conditions([('A',first),('B',second)],key);self.assertTrue(result['same_starting_clues']);self.assertFalse(result['same_supplied_evidence'])

class DiagnosticTests(unittest.TestCase):
    def key(self):return {'accounts':[{'id':'A1','platform':'Instagram','role':'withheld','canonical_url':'https://instagram.com/missingfixture'}]}
    def report(self):return {'status':'complete','case':{},'records':[],'coverage':[],'link_evidence':[]}
    def test_unfinished_report_rejects_answer_key(self):
        with self.assertRaises(ValueError):diagnose_misses(dict(self.report(),status='running'),self.key())
    def test_original_adapter_loss_is_distinct_from_missing_index_evidence(self):
        report=self.report();report['coverage']=[{'returned_references':[{'reference':'https://instagram.com/missingfixture'}]}];original=copy.deepcopy(report)
        result=diagnose_misses(report,self.key());self.assertEqual(result['accounts'][0]['stage'],'adapter-row-missing-from-report')
        self.assertEqual(report,original);self.assertEqual(result['network_requests'],0);self.assertFalse(result['discovery_score_changed'])
    def test_answer_targeted_control_does_not_prove_blind_pipeline_loss(self):
        report=self.report();report['coverage']=[{'source':'https://api.search.brave.com/res/v1/web/search?q=original'}]
        control={'results':[{'provider':'Brave web index','status':'ok','source':'https://api.search.brave.com/res/v1/web/search?q=missingfixture','rows':[{'reference':'https://instagram.com/missingfixture'}]}]}
        result=diagnose_misses(report,self.key(),{'A1':control})
        self.assertEqual(result['accounts'][0]['stage'],'post-test-control-only');self.assertFalse(result['accounts'][0]['same_original_query'])
    def test_cited_link_and_linked_review_record_remain_distinct(self):
        report=self.report();report['link_evidence']=[{'target':'https://instagram.com/missingfixture','citation':'R1'}]
        self.assertEqual(diagnose_misses(report,self.key())['accounts'][0]['stage'],'explicit-link-not-materialized')
        report['records']=[{'id':'R2','reference':'https://instagram.com/missingfixture','origin':'explicit-linked-profile','lead_only':True}]
        self.assertEqual(diagnose_misses(report,self.key())['accounts'][0]['stage'],'returned-linked-review-lead')
    def test_deeper_control_rank_is_not_counted_as_a_blind_discovery(self):
        source='https://api.search.brave.com/res/v1/web/search?q=original'
        report=self.report();report['coverage']=[{'source':source,'retrieval_diagnostics':{'result_limit':10}}]
        control={'results':[{'provider':'Brave web index','source':source+'&count=20','status':'ok','rows':[{'reference':'https://instagram.com/missingfixture','index_rank':15}]}]}
        result=diagnose_misses(report,self.key(),{'A1':control})
        self.assertEqual(result['accounts'][0]['stage'],'post-test-deeper-result');self.assertFalse(result['discovery_score_changed'])
    def test_exact_url_diagnosis_can_cover_unregistered_profile_pages(self):
        sheet={'accounts':[{'id':'A1','role':'withheld','canonical_url':'https://example.org/athlete/profile'}]}
        report=self.report();report['records']=[{'id':'R1','reference':'https://example.org/athlete/profile'}]
        result=diagnose_misses(report,sheet)['accounts'][0]
        self.assertEqual(result['stage'],'returned-in-blind-report');self.assertFalse(result['profile_registry_supported'])
    def test_unregistered_query_ids_cannot_be_collapsed_into_a_false_match(self):
        sheet={'accounts':[{'id':'A1','role':'withheld','canonical_url':'https://example.org/profile?user=ExpectedID'}]}
        report=self.report();report['records']=[{'id':'R1','reference':'https://example.org/profile?user=OtherID'}]
        self.assertEqual(diagnose_misses(report,sheet)['accounts'][0]['stage'],'unresolved-no-control')
    def test_cli_checks_external_seal_and_never_changes_inputs(self):
        import contextlib,hashlib,io,tempfile,sys
        from pathlib import Path
        from scripts.diagnose_benchmark import main
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);raw=json.dumps(self.report()).encode();(root/'report.json').write_bytes(raw)
            (root/'key.json').write_text(json.dumps(self.key()));(root/'seal.json').write_text(json.dumps({'sha256':hashlib.sha256(raw).hexdigest()}))
            args=['diagnose_benchmark','--report',str(root/'report.json'),'--key',str(root/'key.json'),'--seal',str(root/'seal.json'),'--output',str(root/'diagnosis.json')]
            with patch.object(sys,'argv',args),contextlib.redirect_stdout(io.StringIO()):main()
            result=json.loads((root/'diagnosis.json').read_text());self.assertTrue(result['external_seal_verified']);self.assertEqual((root/'report.json').read_bytes(),raw)
            import os
            os.link(root/'report.json',root/'alias.json')
            with patch.object(sys,'argv',args[:-1]+[str(root/'alias.json')]),self.assertRaisesRegex(ValueError,'sealed input'):main()
            self.assertEqual((root/'report.json').read_bytes(),raw)
            (root/'report.json').write_bytes(raw+b' ')
            with patch.object(sys,'argv',args),self.assertRaisesRegex(ValueError,'hash mismatch'):main()

class DiagnosticAPITests(unittest.TestCase):
    def test_endpoint_is_read_only_and_makes_no_provider_or_key_writes(self):
        import app,http.cookiejar,urllib.request
        from http.server import ThreadingHTTPServer
        server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        client=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));base='http://127.0.0.1:'+str(server.server_port)
        report=DiagnosticTests().report();original=copy.deepcopy(report)
        try:
            client.open(base+'/').close()
            with patch.object(app.CASES,'run',return_value=report),patch.object(app.WEB_SEARCH,'search') as provider,patch.object(app.AUTOMATION.vault,'save_search') as persistence:
                request=urllib.request.Request(base+'/api/benchmark-diagnosis',data=json.dumps({'run_id':'fixture','answer_sheet':DiagnosticTests().key()}).encode(),headers={'Content-Type':'application/json'})
                with client.open(request) as response:result=json.load(response)
                self.assertEqual(result['network_requests'],0);provider.assert_not_called();persistence.assert_not_called()
            self.assertEqual(report,original)
        finally:server.shutdown();server.server_close();worker.join(3)

class EngineRecoveryTests(unittest.TestCase):
    setUp=fixtures.EngineTests.setUp
    tearDown=fixtures.EngineTests.tearDown
    research=fixtures.EngineTests.research
    context=fixtures.EngineTests.context
    make=fixtures.EngineTests.make
    run_case=fixtures.EngineTests.run_case
    def test_reviewed_link_survives_an_empty_followup_and_zero_followup_budget(self):
        case=self.make(investigation={'enabled':True,'allow_maigret':False,'follow_published_links':True,'max_followups':0})
        capture=import_links({'mode':'browser','data':{'schema':'vidocq-browser-v1','reference':'https://github.com/publicfixture','title':'Reviewed bio','excerpt':'Public biography','links':['https://tiktok.com/@linkedfixture']}})
        self.service.link_capture(case['id'],capture,self.notebook.save_finding)
        run=self.run_case(case);lead=next(r for r in run['records'] if r.get('origin')=='explicit-linked-profile')
        self.assertTrue(lead['lead_only']);self.assertTrue(lead['parent_citations']);self.assertEqual(lead['reference'],'https://tiktok.com/@linkedfixture')
        self.assertNotIn(('tiktok','linkedfixture'),self.calls);self.assertEqual(run['analysis']['counts']['explicit_linked_profile_leads'],1)
    def test_index_snippet_links_respect_opt_in_and_followup_caps(self):
        def research(kind,value):
            self.calls.append((kind,value));return {'results':[{'provider':'Brave web index','status':'ok','rows':[{'reference':'https://instagram.com/publicfixture','title':'Public fixture','detail':'Public bio https://tiktok.com/@linkedfixture','observations':{'index_only':True}}]}],'links':[]}
        self.service.research=research
        base={'enabled':True,'allow_maigret':False,'max_followups':1,'max_searches':6}
        first=self.run_case(self.make(urls=['https://instagram.com/publicfixture'],investigation=base))
        self.assertFalse(any(r.get('origin')=='explicit-linked-profile' for r in first['records']));self.assertNotIn(('tiktok','linkedfixture'),self.calls)
        self.calls.clear();second=self.run_case(self.make(urls=['https://instagram.com/publicfixture'],investigation=dict(base,follow_indexed_links=True)))
        self.assertEqual(self.calls.count(('tiktok','linkedfixture')),1);self.assertTrue(any(e['relation']=='indexed-snippet-link' for e in second['link_evidence']))
        self.assertLessEqual(second['completed'],6)
