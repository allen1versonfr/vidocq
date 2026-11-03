import json
from pathlib import Path
import sqlite3
import tempfile
import time
import types
import unittest
from unittest.mock import MagicMock,patch

import app
from case_reports import CaseService,report_html,report_markdown
from discovery_review import profile_handle,canonical_reference
from assisted_investigation import extract_clues
from investigation import InvestigationService
from scripts.maigret_bridge import Bridge
from additional_collectors import AdditionalCollectors

class ProfileTests(unittest.TestCase):
    def test_profile_links_produce_handles_not_shared_domains(self):
        for url,handle in [('https://www.twitch.tv/example','example'),('https://github.com/example','example'),('https://reddit.com/user/example','example'),('https://youtube.com/@example','example')]:
            self.assertEqual(profile_handle(url),handle)
            clues=extract_clues(url,app.normalize);self.assertEqual(clues,[{'kind':'username','value':handle}])
            self.assertEqual(app.normalize('auto',url),('username',handle))
    def test_navigation_and_malformed_links_are_not_accounts(self):
        for url in ['https://twitch.tv/directory','https://twitch.tv/example/videos','https://github.com/explore','https://github.com/example/repository','https://user:pass@twitch.tv/example','https://twitch.tv:bad/example']:
            self.assertIsNone(profile_handle(url))
        self.assertFalse(extract_clues('https://twitch.tv/directory',app.normalize))
        self.assertEqual(extract_clues('https://example.org/a',app.normalize),[{'kind':'domain','value':'example.org'}])
    def test_equivalent_profile_references_share_decision_key(self):
        self.assertEqual(canonical_reference('http://www.steamcommunity.com/id/Example/?tracking=1#bio'),'https://steamcommunity.com/id/example')
        for value in ['javascript:alert(1)','https://user:pass@example.org/a','https://example.org:443/a']:
            with self.assertRaises(ValueError):canonical_reference(value)

class ReviewCaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();path=Path(self.temp.name)/'workspace.sqlite3'
        def database():
            db=sqlite3.connect(path,factory=app.NotebookConnection);db.execute('CREATE TABLE IF NOT EXISTS findings (id TEXT PRIMARY KEY,data TEXT NOT NULL)');return db
        self.collectors=MagicMock();self.collectors.status.return_value={}
        self.collectors.maigret.return_value={'results':[{'provider':'Maigret','status':'ok','source':'http://127.0.0.1:8001/api/search','rows':[{'title':'Candidate','reference':'https://steamcommunity.com/id/example','detail':'example','lead_only':True}],'checks':[{'site':'Steam','outcome':'candidate','reason':'Ownership unverified.'}]}],'links':[]}
        self.calls=[];self.contexts=[]
        self.service=CaseService(database,app.normalize,lambda k,v:self.research(k,v),lambda q:None,context_search=lambda terms:self.context(terms),collectors=self.collectors)
        self.service.initialize();self.notebook=InvestigationService(database);self.notebook.initialize()
    def tearDown(self):
        deadline=time.monotonic()+5
        while self.service.active and time.monotonic()<deadline:time.sleep(.01)
        self.temp.cleanup()
    def research(self,kind,value):self.calls.append((kind,value));return {'results':[],'links':[]}
    def context(self,terms):self.contexts.append(terms);return {'results':[],'links':[]}
    def make(self,**extra):return self.service.create(dict({'title':'Reviewed investigation','names':['Example Person'],'usernames':['example'],'investigation':{'enabled':True,'allow_maigret':True}},**extra))
    def run_case(self,case):
        run=self.service.start(case['id'],True);deadline=time.monotonic()+5
        while self.service.active and time.monotonic()<deadline:time.sleep(.01)
        return self.service.run(run['id'])
    def test_locations_are_alternatives_not_one_literal_phrase(self):
        case=self.make(location='City One, State; City Two, State');run=self.run_case(case)
        self.assertEqual(self.contexts,[['Example Person','City One, State'],['Example Person','City Two, State']])
        self.assertEqual(run['status'],'complete')
    def test_profile_reference_does_not_research_platform_domain(self):
        self.run_case(self.make(urls=['https://twitch.tv/example']))
        self.assertNotIn(('domain','twitch.tv'),self.calls);self.assertEqual(self.calls.count(('username','example')),1)
    def test_rejected_account_survives_case_edit_and_excludes_checker(self):
        case=self.make();self.service.account_decision(case['id'],{'reference':'https://steamcommunity.com/id/example/','status':'Rejected','reason':'Subject confirmed this is someone else.'})
        updated=self.service.update(case['id'],{**case,'title':'Edited case'})
        self.assertEqual(updated['account_decisions'][0]['status'],'Rejected')
        run=self.run_case(updated)
        self.assertNotIn('Steam',self.collectors.maigret.call_args.args[2])
        self.assertTrue(any(x['outcome']=='rejected' for c in run['coverage'] for x in c.get('checks',[])))
    def test_immutable_capture_and_saved_decision_history(self):
        case=self.make();first=self.run_case(case);self.assertEqual(first['analysis']['counts']['analyst_confirmed_accounts'],0)
        p={'reference':'https://steamcommunity.com/id/example','status':'Confirmed','reason':'Subject confirms ownership.'}
        self.service.account_decision(case['id'],p);second=self.run_case(case)
        self.assertEqual(second['analysis']['counts']['analyst_confirmed_accounts'],1)
        self.assertIn('Subject confirms ownership.',report_html(second))
        self.assertIn('Subject confirms ownership.',report_markdown(second))
        self.assertEqual(self.service.run(first['id'])['analysis']['counts']['analyst_confirmed_accounts'],0)
        p.update(status='Rejected',reason='Correction by subject.');decision=self.service.account_decision(case['id'],p)
        self.assertEqual(decision['history'][0]['status'],'Confirmed')
    def test_browser_capture_is_attached_user_supplied_and_cited(self):
        case=self.make();finding=self.service.browser_capture(case['id'],{'title':'Public linked profile','reference':'http://www.example.org/About?source=review#section','excerpt':'Example Person lists example as a handle.','query':'Example Person','consent':True},self.notebook.save_finding)
        run=self.run_case(case);record=next(r for r in run['records'] if r['provider']=='User-selected notebook finding')
        self.assertEqual(record['origin'],'user-supplied');self.assertIn('Example Person',record['detail']);self.assertEqual(finding['capture']['origin'],'browser-capture')
        self.assertIn('http://www.example.org/About?source=review#section',report_html(run));self.assertIn('http://www.example.org/About?source=review#section',report_markdown(run))
    def test_capture_consent_and_invalid_decisions_rejected(self):
        case=self.make()
        with self.assertRaises(ValueError):self.service.browser_capture(case['id'],{'reference':'https://example.org'},self.notebook.save_finding)
        for p in [{'reference':'https://example.org','status':'Automatic proof','reason':'x'},{'reference':'https://example.org','status':'Rejected','reason':''}]:
            with self.assertRaises(ValueError):self.service.account_decision(case['id'],p)
    def test_unlinked_records_are_not_successful_discovery(self):
        self.service.research=lambda k,v:{'results':[{'provider':'Index','status':'ok','rows':[{'title':'Unrelated page','detail':'Unrelated material'}]}],'links':[]}
        case=self.make(investigation={'enabled':True,'allow_maigret':False});run=self.run_case(case)
        self.assertEqual(run['search_outcome'],'no-relevant-leads');self.assertEqual(run['analysis']['counts']['candidate_records'],0)
        self.assertGreater(run['analysis']['counts']['unlinked_records'],0)

class DiagnosticTests(unittest.TestCase):
    def test_bridge_distinguishes_blocked_unsupported_absent_and_candidate(self):
        async def fake(**kwargs):
            return {'GitHub':{'status':types.SimpleNamespace(status='Claimed',error=None),'url_user':'https://github.com/example'},'Reddit':{'status':types.SimpleNamespace(status='Unknown',error=types.SimpleNamespace(type='Captcha'))},'Steam':{'status':types.SimpleNamespace(status='Available',error=None)}}
        selected={s:object() for s in ('GitHub','Reddit','Steam')}
        with patch.dict('sys.modules',{'maigret':types.SimpleNamespace(search=fake)}),patch('scripts.maigret_bridge.site_selection',return_value=(selected,{s:s for s in selected})):
            result=Bridge().search({'username':'example','run_id':'a'*24,'sites':['GitHub','Reddit','Steam','Twitch']})
        self.assertEqual([x['outcome'] for x in result['results']],['candidate','blocked','absent','unsupported'])
    def test_adapter_preserves_every_selected_site_outcome(self):
        client=AdditionalCollectors();client.configure({'maigret_enabled':True,'maigret_key':'synthetic-companion-key'})
        data={'username':'example','results':[{'site':'GitHub','status':'Unknown','outcome':'blocked'},{'site':'Steam','status':'Available','outcome':'absent'}]}
        with patch('additional_collectors.transport',side_effect=[{'service':'vidocq-maigret-bridge','protocol':1},data]):report=client.maigret('example','owner',['GitHub','Steam','Reddit'])
        checks=report['results'][0]['checks'];self.assertEqual({c['site'] for c in checks},{'GitHub','Steam','Reddit'});self.assertEqual(report['results'][0]['status'],'partial')
