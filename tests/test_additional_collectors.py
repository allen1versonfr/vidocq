import asyncio
import copy
import io
import json
import sqlite3
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
from urllib.error import HTTPError

import app
from additional_collectors import AdditionalCollectors,transport,ConnectorUnavailable
from case_reports import CaseService,report_html,report_markdown
from collector_policy import MAIGRET_SITES
from scripts.maigret_bridge import Bridge,Handler

class CollectorTests(unittest.TestCase):
    def setUp(self):self.client=AdditionalCollectors()
    def enable(self,kind):self.client.configure({kind+'_enabled':True,kind+'_key':'a'*32})
    def run_data(self,**changes):
        data={'run_id':'example-run','target':'example.com','sources':['crtsh'],'activities':['P0'],'status':'completed','evidence_status':'complete','results':[{'type':'email','value':'sample@example.com','sources':['crtsh']}],'source_executions':[{'status':'completed'}]}
        data.update(changes);return data
    def test_settings_default_off_and_keys_never_in_status(self):
        self.assertTrue(all(not self.client.status()[k]['enabled'] for k in ('hibp','harvester','maigret')))
        self.enable('hibp');self.assertNotIn('a'*32,json.dumps(self.client.status()))
        for p in [{'hibp_enabled':True,'hibp_key':'bad'},{'maigret_enabled':True},{'harvester_port':80},{'hibp_enabled':'true'}]:
            with self.assertRaises(ValueError):self.client.configure(p)
    def test_disabled_collectors_never_request(self):
        with patch('additional_collectors.transport') as request:
            for call in [lambda:self.client.hibp('sample@example.com'),lambda:self.client.harvester('example.com','run',['crtsh']),lambda:self.client.maigret('example','run',['GitHub'])]:
                with self.assertRaises(ValueError):call()
            request.assert_not_called()
    def test_hibp_metadata_only_cached_and_attributed(self):
        self.enable('hibp')
        breach={'Name':'Example','Title':'Example breach','BreachDate':'2020-01-01','DataClasses':['Email addresses'],'IsVerified':True,'Password':'must-not-copy','Description':'<script>bad</script>'}
        with patch('additional_collectors.transport',return_value=[breach]) as request:
            report=self.client.hibp('sample@example.com');again=self.client.hibp('sample@example.com')
            self.assertEqual(request.call_count,1);self.assertIn('truncateResponse=false',request.call_args.args[0]);self.assertEqual(report,again)
        self.assertNotIn('must-not-copy',json.dumps(report));self.assertNotIn('<script>',json.dumps(report));self.assertIn('CC BY 4.0',json.dumps(report));self.assertTrue(report['results'][0]['rows'][0]['lead_only'])
    def test_hibp_404_is_empty_not_safe_and_auth_failure_not_empty(self):
        opener=MagicMock();opener.open.side_effect=HTTPError('url',404,'',{},None)
        with patch('additional_collectors.build_opener',return_value=opener):self.assertEqual(transport('https://haveibeenpwned.com/api/v3/breachedaccount/sample%40example.com'),[])
        opener.open.side_effect=HTTPError('secret',401,'secret',{},None)
        with patch('additional_collectors.build_opener',return_value=opener):
            with self.assertRaises(ValueError) as error:transport('https://haveibeenpwned.com/api/v3/breachedaccount/sample%40example.com',key='secret')
        self.assertNotIn('secret',str(error.exception))
        self.enable('hibp')
        with patch('additional_collectors.transport',return_value=[]):report=self.client.hibp('sample@example.com')
        self.assertEqual(report['results'][0]['status'],'empty');self.assertIn('does not prove',report['results'][0]['message'])
    def test_hibp_reserved_key_and_rate_limit_cooldown(self):
        self.client.configure({'hibp_enabled':True,'hibp_key':'0'*32})
        with patch('additional_collectors.transport') as request:
            with self.assertRaises(ValueError):self.client.hibp('sample@example.com')
            request.assert_not_called()
        error=ConnectorUnavailable('rate limit');error.http_status=429;error.retry_after=120
        with patch('additional_collectors.transport',side_effect=error):
            with self.assertRaises(ValueError):self.client.hibp('account-exists@hibp-integration-tests.com')
        with patch('additional_collectors.transport') as request:
            with self.assertRaises(ValueError):self.client.hibp('multiple-breaches@hibp-integration-tests.com')
            request.assert_not_called()
    def test_hibp_sensitive_retired_records_filtered(self):
        self.enable('hibp')
        with patch('additional_collectors.transport',return_value=[{'Name':'Sensitive','IsSensitive':True},{'Name':'Retired','IsRetired':True}]):r=self.client.hibp('sample@example.com')
        self.assertEqual(r['results'][0]['rows'],[])
    def test_transport_fixed_paths_hosts_and_redirect_refusal(self):
        with patch('additional_collectors.build_opener') as network:
            for url,kind in [('http://haveibeenpwned.com/api/v3/breachedaccount/x','hibp'),('https://haveibeenpwned.com/api/v3/pasteAccount/x','hibp'),('http://localhost:5000/api/v1/runs','harvester'),('http://127.0.0.1:8001/admin','maigret')]:
                with self.assertRaises(ValueError):transport(url,service=kind)
            network.assert_not_called()
    def test_harvester_only_ready_passive_sources_submitted(self):
        self.enable('harvester');catalog={'sources':[{'name':'crtsh','activity':'P0','ready':True}]}
        with patch('additional_collectors.transport',side_effect=[catalog,self.run_data()]) as request:
            report=self.client.harvester('example.com','owner',['crtsh'])
        p=request.call_args_list[1].args[1];self.assertEqual(p['limit'],50);self.assertEqual(p['deadline_seconds'],60)
        self.assertFalse(any(p[f] for f in ('dns_resolve','dns_brute','dns_lookup','screenshot','takeover','api_scan','vhost','shodan')))
        self.assertEqual(report['results'][0]['status'],'ok');self.assertTrue(report['results'][0]['rows'][0]['lead_only'])
        with patch('additional_collectors.transport',return_value={'sources':[{'name':'crtsh','activity':'P2','ready':True}]}) as request:
            with self.assertRaises(ValueError):self.client.harvester('example.com','owner',['crtsh'])
            self.assertEqual(request.call_count,1)
    def test_harvester_partial_source_and_scope_errors(self):
        self.enable('harvester');catalog={'sources':[{'name':'crtsh','activity':'P0','ready':True}]}
        with patch('additional_collectors.transport',side_effect=[catalog,self.run_data(evidence_status='partial',source_executions=[{'status':'failed'}])]):r=self.client.harvester('example.com','owner',['crtsh'])
        self.assertEqual(r['results'][0]['status'],'partial');self.assertTrue(r['results'][0]['rows']);self.assertEqual(r['results'][1]['status'],'error')
        with patch('additional_collectors.transport',side_effect=[catalog,self.run_data(target='other.example'),{}]) as request:
            with self.assertRaises(ValueError):self.client.harvester('example.com','owner',['crtsh'])
        self.assertTrue(request.call_args.args[0].endswith('/cancel'));self.assertFalse(self.client.pending)
    def test_harvester_cancellation_retains_partial_evidence(self):
        self.enable('harvester');catalog={'sources':[{'name':'crtsh','activity':'P0','ready':True}]}
        def respond(url,*args,**kwargs):
            if url.endswith('/sources'):return catalog
            if url.endswith('/runs'):
                self.client.cancelled.add('owner');return self.run_data(status='running')
            if url.endswith('/cancel'):return self.run_data(status='cancelled')
            return self.run_data(status='cancelled',evidence_status='partial')
        with patch('additional_collectors.transport',side_effect=respond):r=self.client.harvester('example.com','owner',['crtsh'])
        self.assertEqual(r['results'][0]['status'],'partial');self.assertTrue(r['results'][0]['rows'])
    def test_maigret_candidates_partial_checks_and_target_validation(self):
        self.enable('maigret');about={'service':'vidocq-maigret-bridge','protocol':1}
        result={'username':'example','results':[{'site':'GitHub','status':'Claimed','url':'https://github.com/example'},{'site':'Reddit','status':'Unknown','url':''}]}
        with patch('additional_collectors.transport',side_effect=[about,result]):r=self.client.maigret('example','owner',['GitHub','Reddit'])
        self.assertEqual(r['results'][0]['status'],'partial');self.assertEqual(len(r['results'][0]['rows']),1);self.assertIn('not proof',r['results'][0]['rows'][0]['detail'])
        with patch('additional_collectors.transport',side_effect=[about,dict(result,username='other'),{}]) as request:
            with self.assertRaises(ValueError):self.client.maigret('example','owner',['GitHub'])
            self.assertTrue(request.call_args.args[0].endswith('/api/cancel'))
        with self.assertRaises(ValueError):self.client.maigret('--all-sites','owner',['GitHub'])
    def test_maigret_unknown_sites_and_wrong_service_rejected(self):
        self.enable('maigret')
        with patch('additional_collectors.transport') as request:
            with self.assertRaises(ValueError):self.client.maigret('example','owner',['https://example.com'])
            request.assert_not_called()
        with patch('additional_collectors.transport',return_value={'service':'other'}) as request:
            with self.assertRaises(ValueError):self.client.maigret('example','owner',['GitHub'])
            self.assertEqual(request.call_count,1)

class CompanionTests(unittest.TestCase):
    def test_library_flags_and_no_raw_page_storage(self):
        received={}
        async def fake(**kwargs):
            received.update(kwargs);return {'GitHub':{'status':types.SimpleNamespace(status='Claimed'),'url_user':'https://github.com/example','response_text':'Do not retain this page'}}
        bridge=Bridge()
        with patch.dict(sys.modules,{'maigret':types.SimpleNamespace(search=fake)}),patch('scripts.maigret_bridge.site_selection',return_value=({'GitHub':object()},{'GitHub':'GitHub'})):
            r=bridge.search({'username':'example','sites':['GitHub'],'run_id':'a'*24})
        self.assertFalse(received['is_parsing_enabled']);self.assertFalse(received['is_enrich_enabled']);self.assertIsNone(received['cloudflare_bypass']);self.assertIsNone(received['cookies']);self.assertEqual(received['retries'],0);self.assertEqual(received['max_connections'],3)
        self.assertEqual(r['results'][0]['status'],'Claimed');self.assertNotIn('Do not retain',json.dumps(r));self.assertFalse(bridge.jobs)
    def test_early_cancel_and_unknown_sites_remain_partial(self):
        async def fake(**kwargs):return {}
        bridge=Bridge();bridge.cancel('a'*24)
        with patch.dict(sys.modules,{'maigret':types.SimpleNamespace(search=fake)}),patch('scripts.maigret_bridge.site_selection',return_value=({},{})):
            r=bridge.search({'username':'example','sites':['GitHub'],'run_id':'a'*24})
        self.assertTrue(r['cancelled']);self.assertEqual(r['results'][0]['status'],'Unknown')
    def test_loopback_key_auth_and_no_open_proxy(self):
        from http.server import ThreadingHTTPServer
        import urllib.request,urllib.error
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.api_key='example-test-key-123456';server.bridge=MagicMock();server.bridge.about.return_value={'service':'vidocq-maigret-bridge','protocol':1}
        threading.Thread(target=server.serve_forever,daemon=True).start();base='http://127.0.0.1:'+str(server.server_port)
        try:
            with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(base+'/api/about')
            req=urllib.request.Request(base+'/api/about',headers={'X-Vidocq-Key':server.api_key})
            with urllib.request.urlopen(req) as r:self.assertEqual(json.load(r)['protocol'],1)
            req=urllib.request.Request(base+'/api/about',headers={'X-Vidocq-Key':server.api_key,'Origin':'https://evil.example'})
            with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(req)
        finally:server.shutdown();server.server_close()

class CollectorCaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'db.sqlite3'
        def db():
            c=sqlite3.connect(self.path,factory=app.NotebookConnection);c.execute('CREATE TABLE IF NOT EXISTS findings (id TEXT PRIMARY KEY,data TEXT NOT NULL)');return c
        self.collectors=MagicMock();self.collectors.status.return_value={}
        self.collectors.hibp.return_value={'results':[{'provider':'Have I Been Pwned','status':'ok','source':'https://haveibeenpwned.com/api/v3/breachedaccount/sample%40example.com','rows':[{'title':'Example exposure','detail':'sample@example.com','reference':'https://haveibeenpwned.com/','lead_only':True}]}],'links':[]}
        self.collectors.harvester.return_value={'results':[],'links':[]};self.collectors.maigret.return_value={'results':[],'links':[]}
        self.service=CaseService(db,app.normalize,lambda k,v:{'results':[],'links':[]},lambda q:None,collectors=self.collectors);self.service.initialize()
    def tearDown(self):
        deadline=time.monotonic()+3
        while self.service.active and time.monotonic()<deadline:time.sleep(.01)
        self.temp.cleanup()
    def finish(self,settings):
        case=self.service.create({'title':'Collector case','emails':['sample@example.com'],'domains':['example.com'],'usernames':['example'],'instagram':['example'],'investigation':dict(enabled=True,**settings)})
        run=self.service.start(case['id'],True)
        deadline=time.monotonic()+3
        while self.service.active and time.monotonic()<deadline:time.sleep(.01)
        return self.service.run(run['id'])
    def test_per_case_permissions_and_one_run_per_handle(self):
        self.finish({});self.collectors.hibp.assert_not_called();self.collectors.harvester.assert_not_called();self.collectors.maigret.assert_not_called()
        run=self.finish({'allow_hibp':True,'allow_harvester':True,'allow_maigret':True})
        self.assertEqual(run['status'],'complete');self.collectors.hibp.assert_called_once();self.collectors.harvester.assert_called_once();self.collectors.maigret.assert_called_once()
        self.assertFalse(run['analysis']['stronger_leads']);self.assertTrue(run['analysis']['needs_review'])
        self.assertIn('href="https://haveibeenpwned.com/"',report_html(run));self.assertIn('[Have I Been Pwned](https://haveibeenpwned.com/)',report_markdown(run));self.assertTrue(run['attributions'])
    def test_missing_collector_is_a_gap_not_job_failure(self):
        self.service.collectors=None;run=self.finish({'allow_hibp':True})
        self.assertEqual(run['status'],'complete');self.assertTrue(any(c['provider']=='Have I Been Pwned' and c['status']=='not-configured' for c in run['coverage']))
