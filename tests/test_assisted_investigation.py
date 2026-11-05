import json
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse,parse_qs
from urllib.error import HTTPError

import app
from assisted_investigation import relevance,extract_clues,options,report_sections
from case_reports import CaseService,report_html,report_markdown
from research_connectors import ResearchConnectors,normalize_steam,read_json,ConnectorUnavailable,NoRedirect

class ConnectorTests(unittest.TestCase):
    def setUp(self):self.client=ResearchConnectors()
    def test_steam_normalization_and_destination_rejection(self):
        self.assertEqual(normalize_steam('76561198000000000'),'https://steamcommunity.com/profiles/76561198000000000/')
        self.assertEqual(normalize_steam('76561202255233023'),'https://steamcommunity.com/profiles/76561202255233023/')
        self.assertEqual(normalize_steam('https://steamcommunity.com/id/Example/?x=1'),'https://steamcommunity.com/id/example/')
        for value in ['https://steamcommunity.com.evil.test/id/example','https://user:pass@steamcommunity.com/id/example','https://steamcommunity.com:443/id/example','https://steamcommunity.com/groups/example','../bad']:
            with self.assertRaises(ValueError):normalize_steam(value)
        with patch('research_connectors.build_opener') as network:
            for url,local in [('http://api.steampowered.com/x',False),('https://example.com',False),('http://localhost:8000/api/run',True),('http://127.0.0.1:8000/admin',True),('http://127.0.0.1:80/api/run',True)]:
                with self.assertRaises(ValueError):read_json(url,local=local)
            network.assert_not_called()
    def test_connectors_disabled_no_requests_and_no_keys_in_status(self):
        with patch('research_connectors.read_json') as request:
            with self.assertRaises(ValueError):self.client.steam('example')
            with self.assertRaises(ValueError):self.client.osintgram('example','run',['get_user_info'])
            request.assert_not_called()
        self.client.configure({'steam_key':'a'*32,'steam_enabled':True})
        self.assertNotIn('a'*32,json.dumps(self.client.status()))
        for bad in [{'steam_enabled':True,'steam_key':'bad'},{'osintgram_enabled':True,'osintgram_port':80},{'steam_enabled':'true'}]:
            with self.assertRaises(ValueError):self.client.configure(bad)
    def test_steam_partial_failures_private_library_not_no_games(self):
        self.client.configure({'steam_key':'a'*32,'steam_enabled':True})
        responses=[{'response':{'players':[{'steamid':'76561198000000000','personaname':'Example','realname':'Example Person','avatarfull':'https://do-not-fetch.example/image'}]}},{'response':{}},{'response':{'game_count':0,'games':[]}}]
        with patch('research_connectors.read_json',side_effect=responses) as request:
            report=self.client.steam('76561198000000000')
        self.assertEqual([r['status'] for r in report['results']],['ok','error','ok'])
        self.assertIn('not disclosed',report['results'][1]['message'])
        self.assertNotIn('a'*32,json.dumps(report));self.assertNotIn('avatarfull',json.dumps(report))
        self.assertEqual(request.call_count,3)
        self.assertTrue(all(urlparse(c.args[0]).scheme=='https' for c in request.call_args_list))
    def test_steam_vanity_resolution_library_limit_and_session_quota(self):
        self.client.configure({'steam_key':'a'*32,'steam_enabled':True})
        with patch('research_connectors.read_json',side_effect=[{'response':{'success':1,'steamid':'76561198000000000'}},{'response':{'players':[]}},{'response':{'game_count':2,'games':[{'appid':10,'name':'Example','playtime_forever':20},{'appid':20,'name':'Other'}]}},{'response':{'game_count':0,'games':[]}}]):
            report=self.client.steam('example',10)
        detail=report['results'][1]['rows'][0]['detail'];self.assertIn('Example',detail);self.assertNotIn('Other',detail)
        self.client.requests['steam']=100
        with patch('research_connectors.read_json') as request:
            report=self.client.steam('76561198000000000');request.assert_not_called();self.assertTrue(all(r['status']=='error' for r in report['results']))
    def test_osintgram_allowlist_command_limits_and_profile_filter(self):
        self.client.configure({'osintgram_enabled':True})
        result={'target':'example','backend':'HikerAPI','api_calls_total':1,'tool_calls':[{'name':'get_user_info','result':{'username':'example','full_name':'Example Person','biography':'Example bio','profile_pic_url_hd':'https://do-not-fetch.example/x','latitude':1,'public_email':'sample@example.com'}}]}
        with patch('research_connectors.read_json',side_effect=[{'repository':'https://github.com/Datalux/Osintgram'},result]) as request:
            report=self.client.osintgram('example','run',['get_user_info'])
        payload=request.call_args_list[1].args[1];self.assertEqual(payload['max_items'],5);self.assertFalse(payload['verbose']);self.assertEqual(payload['calls'],[{'name':'get_user_info','args':{}}])
        self.assertNotIn('profile_pic',json.dumps(report));self.assertNotIn('latitude',json.dumps(report));self.assertIn('sample@example.com',json.dumps(report));self.assertFalse(self.client.pending)
        with self.assertRaises(ValueError):self.client.osintgram('example','run',['get_followers_email'])
    def test_osintgram_target_mismatch_cancels_and_reports_error(self):
        self.client.configure({'osintgram_enabled':True})
        with patch('research_connectors.read_json',side_effect=[{'repository':'https://github.com/Datalux/Osintgram'},{'target':'other','tool_calls':[]},{}]) as request:
            with self.assertRaises(ValueError):self.client.osintgram('example','run',['get_user_info'])
        self.assertTrue(request.call_args_list[-1].args[0].endswith('/api/cancel'));self.assertFalse(self.client.pending)
    def test_osintgram_wrong_local_service_does_not_submit_target(self):
        self.client.configure({'osintgram_enabled':True})
        with patch('research_connectors.read_json',return_value={'repository':'https://example.com'}) as request:
            with self.assertRaises(ValueError):self.client.osintgram('example','run',['get_user_info'])
            self.assertEqual(request.call_count,1)
    def test_osintgram_private_profile_never_queries_posts(self):
        self.client.configure({'osintgram_enabled':True})
        result={'target':'example','api_calls_total':1,'tool_calls':[{'name':'get_user_info','result':{'username':'example','is_private':True}}]}
        with patch('research_connectors.read_json',side_effect=[{'repository':'https://github.com/Datalux/Osintgram'},result]) as request:
            report=self.client.osintgram('example','run',['get_user_info','get_captions'])
        self.assertEqual(request.call_count,2);self.assertEqual(report['results'][0]['status'],'ok');self.assertIn('private or unknown',report['results'][1]['message'])
    def test_osintgram_public_content_uses_remaining_budget(self):
        self.client.configure({'osintgram_enabled':True})
        result={'target':'example','api_calls_total':2,'tool_calls':[{'name':'get_user_info','result':{'username':'example','is_private':False}}]}
        extra={'target':'example','api_calls_total':1,'tool_calls':[{'name':'get_captions','result':['Example public caption']}]}
        with patch('research_connectors.read_json',side_effect=[{'repository':'https://github.com/Datalux/Osintgram'},result,extra]) as request:
            report=self.client.osintgram('example','run',['get_user_info','get_captions'])
        self.assertEqual(request.call_args_list[2].args[1]['max_items'],3);self.assertEqual(report['backend_requests'],3)
    def test_connector_errors_and_redirect_never_expose_key(self):
        opener=MagicMock();opener.open.side_effect=HTTPError('https://api.steampowered.com/?key=secret',403,'key=secret',{},None)
        with patch('research_connectors.build_opener',return_value=opener):
            with self.assertRaises(ValueError) as error:read_json('https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key=secret')
        self.assertNotIn('secret',str(error.exception))
        with self.assertRaises(ValueError):NoRedirect().redirect_request(None,None,302,'',{},'https://example.com')
    def test_cbl_claims_are_limited_and_malformed_sources_isolated(self):
        self.client.configure({'steam_key':'a'*32,'steam_enabled':True,'cbl':True})
        bans=[{'node':{'reason':'Example provider claim'}}]*25
        responses=[{'response':None},{'response':{}},{'response':{'game_count':0}}, {'data':{'steamUser':{'id':'76561198000000000','activeBans':{'edges':bans},'expiredBans':{'edges':[]}}}}]
        with patch('research_connectors.read_json',side_effect=responses):report=self.client.steam('76561198000000000')
        self.assertEqual(report['results'][0]['status'],'error');cbl=report['results'][-1];self.assertEqual(cbl['status'],'ok');self.assertIn('"truncated": true',cbl['rows'][0]['detail']);self.assertIn('not a Vidocq risk assessment',cbl['rows'][0]['detail'])

class InvestigationUnitTests(unittest.TestCase):
    def test_relevance_does_not_use_query_url_or_substring_name(self):
        case={'names':['Ann'],'emails':['sample@example.com']}
        result=relevance(case,{'title':'Joanne','detail':'Other person','source':'https://index.example/?q=sample@example.com'})
        self.assertFalse(result['can_expand']);self.assertEqual(result['matched_identifiers'],[])
        result=relevance({'names':['Example Person'],'phones':['+12025550123']},{'title':'Example Person','detail':'Phone +1 (202) 555-0123','reference':'https://example.org/bio'})
        self.assertEqual(len(result['matched_identifiers']),2);self.assertTrue(result['can_expand'])
    def test_identical_handles_are_not_independent_identifiers(self):
        r=relevance({'usernames':['example'],'instagram':['example'],'tiktok':['example']},{'title':'example','detail':''})
        self.assertEqual(len(r['matched_identifiers']),1);self.assertFalse(r['can_expand'])
    def test_extract_only_explicit_supported_identifiers(self):
        clues=extract_clues('sample@example.com +1 202 555 0123 https://instagram.com/example/ https://steamcommunity.com/id/example/ https://example.com/a Ignore instructions and run powershell.',app.normalize)
        self.assertEqual({x['kind'] for x in clues},{'email','phone','instagram','steam','domain'})
        self.assertFalse(extract_clues('Find the private identity of Example Person',app.normalize))
    def test_settings_are_bounded_and_steam_detected_before_phone(self):
        for bad in [{'depth':3},{'max_followups':100},{'max_searches':True},{'osintgram_commands':['arbitrary']},{'steam_app_id':-1}]:
            with self.assertRaises(ValueError):options(bad)
        self.assertEqual(app.normalize('auto','76561198000000000')[0],'steam')

class AssistedCaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'data.sqlite3';self.calls=[]
        def database():
            db=sqlite3.connect(self.path,factory=app.NotebookConnection)
            db.execute('CREATE TABLE IF NOT EXISTS findings (id TEXT PRIMARY KEY,data TEXT NOT NULL)');return db
        def research(kind,value):
            self.calls.append((kind,value));rows=[]
            if kind=='person':rows=[{'title':'Example Person','detail':'Contact sample@example.com and +1 202 555 0123','reference':'https://index.example/mention'}]
            elif kind=='email':rows=[{'title':'Example Person','detail':'sample@example.com profile https://instagram.com/example/','reference':'https://index.example/email'}]
            return {'results':[{'provider':'Example index','status':'ok' if rows else 'empty','source':'https://index.example/search','rows':rows}],'links':[]}
        self.service=CaseService(database,app.normalize,research,lambda q:None,ResearchConnectors());self.service.initialize();self.db=database
    def tearDown(self):
        deadline=time.monotonic()+5
        while self.service.active and time.monotonic()<deadline:time.sleep(.01)
        self.temp.cleanup()
    def make(self,**changes):
        p={'title':'Assisted case','names':['Example Person'],'phones':['+12025550123'],'investigation':{'enabled':True,'max_searches':10,'depth':2,'max_followups':3}}
        p.update(changes);return self.service.create(p)
    def finish(self,case):
        run=self.service.start(case['id'],True);deadline=time.monotonic()+5
        while self.service.active and time.monotonic()<deadline:time.sleep(.01)
        return self.service.run(run['id'])
    def test_follows_supported_clues_and_links_report_citations(self):
        run=self.finish(self.make());self.assertEqual(run['status'],'complete');self.assertIn(('email','sample@example.com'),self.calls)
        self.assertIn(('instagram','example'),self.calls);self.assertTrue(run['analysis']['stronger_leads']);self.assertTrue(run['discovery_links'])
        self.assertTrue(all(x['parent_citation'] for x in run['discovered_clues']));self.assertLessEqual(run['completed'],10)
        self.assertIn('Investigation summary',report_html(run));self.assertIn('Stronger leads',report_markdown(run))
    def test_name_only_leads_are_not_expanded(self):
        run=self.finish(self.make(phones=[]));self.assertEqual(self.calls,[('person','Example Person')]);self.assertTrue(any(x['status']=='not-searched' for x in run['discovered_clues']))
        self.assertFalse(run['analysis']['stronger_leads'])
    def test_budget_and_followups_can_be_disabled(self):
        run=self.finish(self.make(investigation={'enabled':True,'max_searches':1,'max_followups':0}));self.assertEqual(run['completed'],1);self.assertTrue(run['summary']['unsearched_inputs'])
        self.assertTrue(any(x['status']=='not-run' for x in run['search_log']))
    def test_context_search_and_supplied_notes_do_not_visit_urls(self):
        contexts=[];self.service.context_search=lambda terms:contexts.append(terms) or {'results':[],'links':[]}
        run=self.finish(self.make(employer='Example Org',location='Example City',notes='Reference https://example.com/page'))
        self.assertEqual(contexts,[['Example Person','Example Org'],['Example Person','Example City']]);self.assertIn(('domain','example.com'),self.calls)
        self.assertFalse(any('https://' in str(v) for k,v in self.calls))
    def test_direct_connectors_require_case_opt_in_and_remain_unverified(self):
        fake=MagicMock();fake.steam.return_value={'results':[{'provider':'Steam public profile','status':'ok','source':'https://api.steampowered.com','rows':[{'title':'Profile','detail':'Example Person','reference':'https://steamcommunity.com/id/example/','observations':{'reported_name':'Different Name'}}]}],'links':[]}
        self.service.connectors=fake
        run=self.finish(self.make(names=[],phones=[],steam=['example']));fake.steam.assert_not_called()
        run=self.finish(self.make(names=['Example Person'],phones=[],steam=['example'],investigation={'enabled':True,'direct_sources':True,'max_followups':0}));fake.steam.assert_called_once();self.assertTrue(run['analysis']['review_flags'])
        self.assertTrue(all(x['identity_status']=='Unverified relevance' for x in run['records']))
    def test_cancellation_retains_partial_export(self):
        entered=threading.Event();release=threading.Event()
        original=self.service.research
        def blocked(k,v):entered.set();release.wait(2);return original(k,v)
        self.service.research=blocked;case=self.make();run=self.service.start(case['id'],True);self.assertTrue(entered.wait(2));self.assertTrue(self.service.cancel(run['id'])['cancel_requested']);release.set()
        deadline=time.monotonic()+4
        while self.service.active and time.monotonic()<deadline:time.sleep(.01)
        result=self.service.run(run['id']);self.assertEqual(result['status'],'cancelled');self.assertTrue(result['records']);self.assertIn('partial',report_markdown(result).lower())
    def test_missing_sources_produce_gaps_not_a_biography(self):
        self.service.research=lambda k,v:{'results':[{'provider':'Missing index','status':'not-configured','message':'No API key','rows':[]}],'links':[]}
        run=self.finish(self.make());self.assertTrue(run['analysis']['coverage_gaps']);self.assertFalse(run['analysis']['stronger_leads']);self.assertIn('No record linked',run['analysis']['headline'])
    def test_exports_escape_provider_markup(self):
        self.service.research=lambda k,v:{'results':[{'provider':'Index','status':'ok','rows':[{'title':'<script>alert(1)</script>','detail':'Example Person'}]}],'links':[]}
        run=self.finish(self.make());self.assertNotIn('<script>',report_html(run));self.assertIn('&lt;script&gt;',report_html(run))

class ContextSearchTests(unittest.TestCase):
    def test_context_terms_quoted_separately(self):
        from web_search import WebSearch
        client=WebSearch();client.configure({'key':'example-key','enabled':True});opener=MagicMock();opener.open.return_value.__enter__.return_value.read.return_value=b'{"query":{},"web":{"results":[]}}'
        with patch('web_search.build_opener',return_value=opener):source,rows=client.search_terms(['Example Person','Example Org'])
        self.assertEqual(parse_qs(urlparse(source).query)['q'],['"Example Person" "Example Org"'])
        with self.assertRaises(ValueError):client.search_terms(['bad\nquery'])

class AssistedHTTPTests(unittest.TestCase):
    def test_connector_auth_consent_and_cancel_route(self):
        import urllib.request,urllib.error
        with tempfile.TemporaryDirectory() as root:
            old_data,old_cases,old_connectors=app.DATA,app.CASES,app.CONNECTORS
            app.DATA=Path(root);app.CONNECTORS=ResearchConnectors()
            app.CASES=CaseService(app.db,app.normalize,lambda k,v:{'results':[],'links':[]},lambda q:None,app.CONNECTORS);app.CASES.initialize()
            server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
            def req(path,p=None,auth=True):
                h={'Cookie':'desk='+app.COOKIE} if auth else {}
                if p is not None:h['Content-Type']='application/json'
                return urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+path,data=json.dumps(p).encode() if p is not None else None,headers=h))
            try:
                with self.assertRaises(urllib.error.HTTPError) as error:req('/api/connectors',{},False)
                self.assertEqual(error.exception.code,403)
                with req('/api/connectors') as r:self.assertFalse(json.load(r)['steam']['configured'])
                with self.assertRaises(urllib.error.HTTPError) as error:req('/api/connectors/lookup',{'kind':'steam','value':'example'})
                self.assertEqual(error.exception.code,400)
                case=app.CASES.create({'title':'HTTP assisted','usernames':['example'],'investigation':{'enabled':True}})
                run=app.CASES.start(case['id'],True)
                deadline=time.monotonic()+3
                while app.CASES.active and time.monotonic()<deadline:time.sleep(.01)
                with req('/api/case-runs/'+run['id']+'/cancel',{}) as r:self.assertFalse(json.load(r)['cancel_requested'])
                with req('/assisted.js') as r:self.assertEqual(r.status,200)
            finally:server.shutdown();server.server_close();app.DATA,app.CASES,app.CONNECTORS=old_data,old_cases,old_connectors


class NameRelevanceConsistencyTests(unittest.TestCase):
    def test_middle_name_omission_is_a_single_unverified_name_signal(self):
        from evidence_quality import evidence_gate
        case={'names':['Ada Byron Lovelace']}
        row={'title':'Ada Lovelace','detail':'Public author profile','reference':'https://github.com/fixture_author'}
        self.assertTrue(evidence_gate(row,case)['eligible'])
        result=relevance(case,row)
        self.assertEqual(len(result['matched_identifiers']),1)
        self.assertFalse(result['can_expand'])
        self.assertFalse(result['strong_anchor'])

    def test_approved_spellings_do_not_inflate_corroboration(self):
        case={'names':['Example Person'],'spelling_variants':['Example Persson']}
        row={'title':'Example Person / Example Persson','reference':'https://github.com/fixture_author'}
        self.assertEqual(len(relevance(case,row)['matched_identifiers']),1)
        self.assertFalse(relevance(case,row)['can_expand'])
        row['title']='Example Persson'
        self.assertEqual(len(relevance(case,row)['matched_identifiers']),1)

    def test_partial_names_and_discovery_pages_do_not_enable_expansion(self):
        case={'names':['Ada Byron Lovelace']}
        row={'title':'Ada Lovelaces','reference':'https://github.com/fixture_author'}
        self.assertFalse(relevance(case,row)['matched_identifiers'])
        row={'title':'Ada Lovelace','reference':'https://www.tiktok.com/discover/fixture'}
        self.assertFalse(relevance(case,row)['can_expand'])
