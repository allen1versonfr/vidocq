import json
import sqlite3
import tempfile
import threading
import time
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import urlparse
import app
from case_reports import CaseService,clean_case,report_html,report_markdown,safe_reference
from phone_lookup import inspect_phone

class PhoneTests(unittest.TestCase):
    def test_international_and_national_normalization(self):
        self.assertEqual(inspect_phone('(202) 555-0123','US')['e164'],'+12025550123')
        self.assertEqual(inspect_phone('020 8366 1177','GB')['e164'],'+442083661177')
        self.assertEqual(inspect_phone('+442083661177','')['e164'],'+442083661177')
        self.assertIn('owned',inspect_phone('+442083661177')['notice'])
    def test_bad_phone_region_and_extension(self):
        for value,region in [('123','US'),('not a phone','US'),('2025550123 ext 3','US'),('2025550123','XX')]:
            with self.assertRaises(ValueError):inspect_phone(value,region)
    def test_phone_research_is_offline(self):
        with patch.object(app,'get_json') as get:
            result=app.research('phone','+12025550123');get.assert_not_called()
        self.assertEqual(result['kind'],'phone');self.assertEqual(result['results'][0]['status'],'ok')
        self.assertTrue(all(app.allowed_external(x['url']) for x in result['links']))
    def test_auto_detection_keeps_ip_and_phone_separate(self):
        self.assertEqual(app.normalize('auto','+1 (202) 555-0123'),('phone','+12025550123'))
        self.assertEqual(app.normalize('auto','8.8.8.8'),('ip','8.8.8.8'))

class CaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        def database():
            db=sqlite3.connect(self.root/'data.sqlite3',factory=app.NotebookConnection,timeout=5)
            db.execute('CREATE TABLE IF NOT EXISTS findings (id TEXT PRIMARY KEY,data TEXT NOT NULL)')
            return db
        self.db=database;self.calls=[]
        def research(kind,value):
            self.calls.append((kind,value))
            rows=[] if kind in ('email','username','phone') else [{'provider':'Example index','status':'ok','source':'https://index.example/search','rows':[{'title':'Shared record','detail':'Not identity proof','reference':'https://source.example/item'}]}]
            return {'results':rows,'links':[{'title':'Prepared search','url':'https://www.google.com/search?q=example','note':'Manual only'}]}
        self.service=CaseService(database,app.normalize,research,lambda q:None);self.service.initialize()
    def tearDown(self):
        deadline=time.monotonic()+5
        while self.service.active and time.monotonic()<deadline:time.sleep(.01)
        self.temp.cleanup()
    def make(self,**kw):
        data={'title':'Research case','names':['Example Person'],'phone_region':'US'};data.update(kw)
        return self.service.create(data)
    def finish(self,case):
        run=self.service.start(case['id'],True)
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            run=self.service.run(run['id'])
            if run['status'] not in ('queued','running'):return run
            time.sleep(.01)
        self.fail('Report did not finish')
    def test_input_validation_and_dedup(self):
        data=clean_case({'title':'Case','phones':['2025550123','+12025550123'],'domains':['example.com','EXAMPLE.COM']},app.normalize)
        self.assertEqual(len(data['phones']),1);self.assertEqual(len(data['domains']),1)
        for bad in [{'title':'Case','names':['Example'],'urls':['file:///etc/passwd']},{'title':'Case','names':['Example'],'notebook_ids':['bad']},{'title':'Case'},{'title':'Case','names':['A']*4}]:
            with self.assertRaises(ValueError):clean_case(bad,app.normalize)
    def test_save_update_and_persistence(self):
        case=self.make();self.service.update(case['id'],{'title':'Updated','usernames':['example']})
        other=CaseService(self.db,app.normalize,self.service.research,lambda q:None)
        self.assertEqual(other.get(case['id'])['title'],'Updated');self.assertEqual(len(other.list()),1)
    def test_consent_required(self):
        case=self.make()
        with self.assertRaises(ValueError):self.service.start(case['id'],False)
        self.assertEqual(self.calls,[])
    def test_multi_input_report_and_coverage(self):
        case=self.make(phones=['2025550123'],usernames=['example'],emails=['example@example.com'],domains=['example.com'],urls=['https://reference.example/profile'],notes='Supplied context only')
        run=self.finish(case);self.assertEqual(run['status'],'complete');self.assertEqual(run['completed'],5)
        self.assertEqual(len(run['phone_metadata']),1);self.assertTrue(any(x['status']=='not-run' for x in run['coverage']))
        self.assertTrue(all(x['executed'] is False for x in run['prepared_searches']))
        self.assertFalse(any('reference.example' in str(x) for x in self.calls))
        self.assertTrue(all(x['identity_status']=='Unverified relevance' for x in run['records']))
        self.assertEqual(run['summary']['retrieved_records'],1) # Same index record merged without claiming identity.
    def test_phone_index_results_are_not_discarded(self):
        self.service.research=lambda kind,value: {'results':[{'provider':'Brave web index','status':'ok','source':'https://api.search.brave.com/res/v1/web/search','rows':[{'title':'Indexed mention','detail':'Unverified','reference':'https://example.org/mention'}]}],'links':[]}
        run=self.finish(self.make(names=[],phones=['2025550123']))
        self.assertEqual(run['summary']['retrieved_records'],1)
        self.assertEqual(run['summary']['offline_records'],1)
        self.assertEqual(run['search_outcome'],'records-found')
    def test_unconnected_report_and_exports_explain_no_search(self):
        self.service.research=lambda kind,value: {'results':[{'provider':'Brave web index','status':'not-configured','rows':[],'message':'Connect search'}],'links':[]}
        run=self.finish(self.make(names=[],phones=['2025550123']))
        self.assertEqual(run['search_outcome'],'not-searched')
        self.assertIn('No online result search completed',report_html(run))
        self.assertIn('No online result search completed',report_markdown(run))
    def test_social_only_case_and_report_exports(self):
        case=self.make(names=[],instagram=['@Example','https://www.instagram.com/example/?igsh=test'],tiktok=['https://www.tiktok.com/@Example'],vsco=['https://vsco.co/example-name/gallery'])
        self.assertEqual(case['instagram'],['example']);self.assertEqual(case['tiktok'],['example'])
        run=self.finish(case)
        self.assertEqual(run['completed'],3);self.assertEqual(len(run['social_profiles']),3)
        self.assertIn(('instagram','example'),self.calls);self.assertIn(('tiktok','example'),self.calls);self.assertIn(('vsco','example-name'),self.calls)
        for exported in (report_html(run),report_markdown(run)):
            self.assertIn('https://www.instagram.com/example/',exported)
            self.assertIn('https://www.tiktok.com/@example/',exported);self.assertIn('https://vsco.co/example-name/',exported)
            self.assertIn('not visited or verified',exported)
    def test_old_cases_gain_empty_social_fields_without_changing_snapshots(self):
        case=self.make();old=dict(case);old.pop('instagram');old.pop('tiktok');old.pop('vsco')
        with self.db() as db:db.execute('UPDATE cases SET data=? WHERE id=?',(json.dumps(old),case['id']))
        loaded=self.service.get(case['id']);self.assertEqual(loaded['instagram'],[])
        run=self.finish(loaded);self.assertEqual(run['status'],'complete');self.assertEqual(run['social_profiles'],[])
    def test_social_limits_and_invalid_profiles(self):
        for data in [{'instagram':['example'+str(i) for i in range(6)]},{'tiktok':['https://www.tiktok.com/@example/video/123']},{'instagram':['https://evil.example/user']}]:
            with self.assertRaises(ValueError):self.make(**data)
    def test_report_snapshot_does_not_change_after_case_edit(self):
        case=self.make();run=self.finish(case)
        self.service.update(case['id'],{'title':'Different','names':['Another Person']})
        self.assertEqual(self.service.run(run['id'])['case']['title'],'Research case')
    def test_selected_notebook_evidence_only(self):
        finding={'id':'a'*24,'title':'Selected','notes':'Supplied finding','source':'User reference'}
        with self.db() as db:
            for key,title in [('a'*24,'Selected'),('b'*24,'Unrelated')]:
                item=dict(finding,id=key,title=title);db.execute('INSERT INTO findings VALUES (?,?)',(key,json.dumps(item)))
        run=self.finish(self.make(notebook_ids=['a'*24]))
        self.assertEqual(run['summary']['supplied_records'],1)
        self.assertNotIn('Unrelated',json.dumps(run))
    def test_failed_provider_is_retained(self):
        self.service.research=lambda kind,value: {'results':[{'provider':'Offline source','status':'error','message':'Timed out','rows':[]}],'links':[]}
        run=self.finish(self.make());self.assertEqual(run['status'],'complete');self.assertEqual(run['summary']['source_errors'],1)
        self.assertEqual(run['records'],[])
    def test_export_escapes_markup_and_is_self_contained(self):
        run=self.finish(self.make(title='<script>alert(1)</script>',notes='![tracking](https://bad.example/pixel)'))
        exported=report_html(run)
        self.assertNotIn('<script>',exported);self.assertNotIn('<img',exported);self.assertNotIn('<a ',exported)
        self.assertIn('&lt;script&gt;',exported);self.assertIn("default-src 'none'",exported)
        self.assertIn('## Source coverage',report_markdown(run));self.assertIn('## Evidence and citations',report_markdown(run))
    def test_interrupted_run_does_not_repeat_requests(self):
        case=self.make();run={'id':'c'*24,'case_id':case['id'],'status':'running','records':[]}
        with self.db() as db:db.execute('INSERT INTO case_runs VALUES (?,?,?)',(run['id'],case['id'],json.dumps(run)))
        self.service.initialize();self.assertEqual(self.service.run(run['id'])['status'],'interrupted');self.assertEqual(self.calls,[])
    def test_other_live_instance_is_not_marked_interrupted(self):
        import os
        case=self.make();run={'id':'d'*24,'case_id':case['id'],'status':'running','owner_pid':os.getpid(),'records':[]}
        with self.db() as db:db.execute('INSERT INTO case_runs VALUES (?,?,?)',(run['id'],case['id'],json.dumps(run)))
        self.service.initialize();self.assertEqual(self.service.run(run['id'])['status'],'running')
    def test_parallel_runs_are_rejected(self):
        case=self.make();self.service.active='busy'
        with self.assertRaises(ValueError):self.service.start(case['id'],True)
        self.service.active=None
    def test_reference_url_schemes(self):
        for url in ['javascript:alert(1)','https://u:p@example.com','file:///tmp/a']:self.assertEqual(safe_reference(url),'')

if __name__=='__main__':unittest.main()

class NewsTests(unittest.TestCase):
    def test_news_adapter_queries_index_only(self):
        payload={'articles':[{'title':'Example headline','url':'https://publisher.example/story','domain':'publisher.example','seendate':'20261101T000000Z','socialimage':'https://publisher.example/pixel'}]}
        with patch.object(app,'get_json',return_value=payload) as get,patch.object(app.time,'sleep'):
            source,rows=app.news_mentions('Example Person')
        self.assertEqual(urlparse(source).hostname,'api.gdeltproject.org');self.assertEqual(get.call_count,1)
        self.assertEqual(rows[0]['reference'],'https://publisher.example/story');self.assertNotIn('pixel',str(rows))
    def test_news_malformed_response_is_error(self):
        with patch.object(app,'get_json',return_value={'error':'limit'}),patch.object(app.time,'sleep'):
            with self.assertRaises(ValueError):app.news_mentions('Example Person')

class CaseHTTPTests(unittest.TestCase):
    def test_case_api_authentication_report_and_export(self):
        import urllib.request,urllib.error
        with tempfile.TemporaryDirectory() as t:
            old_data,old_cases=app.DATA,app.CASES
            app.DATA=Path(t)
            service=CaseService(app.db,app.normalize,lambda k,v:{'results':[],'links':[]},lambda q:None)
            service.initialize();app.CASES=service
            server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
            threading.Thread(target=server.serve_forever,daemon=True).start()
            base='http://127.0.0.1:'+str(server.server_port)
            def req(path,data=None,authenticated=True):
                headers={'Cookie':'desk='+app.COOKIE} if authenticated else {}
                if data is not None:headers['Content-Type']='application/json'
                return urllib.request.urlopen(urllib.request.Request(base+path,data=None if data is None else json.dumps(data).encode(),headers=headers))
            try:
                with self.assertRaises(urllib.error.HTTPError) as error:req('/api/cases',authenticated=False)
                self.assertEqual(error.exception.code,403)
                with req('/api/cases',{'title':'HTTP report','phones':['2025550123']}) as response:case=json.load(response)
                with req('/api/cases/'+case['id']+'/run',{'consent':True}) as response:run=json.load(response)
                deadline=time.monotonic()+5
                while service.active and time.monotonic()<deadline:time.sleep(.01)
                with req('/api/case-runs/'+run['id']+'?format=html') as response:
                    exported=response.read().decode();self.assertIn('HTTP report',exported);self.assertIn('Offline phone metadata',exported)
                with req('/api/cases/'+case['id']+'/runs') as response:self.assertEqual(json.load(response)[0]['status'],'complete')
            finally:
                server.shutdown();server.server_close();app.DATA,app.CASES=old_data,old_cases
