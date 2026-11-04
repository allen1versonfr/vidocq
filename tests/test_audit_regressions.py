"""Regression checks for account identity, evidence and retrieval integrity.
No live providers or subjects; run from repository root with unittest discover.
"""
import base64,json,os,sys,threading,types,unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
from urllib.error import HTTPError
from assisted_investigation import relevance,execute,synthesis
from discovery_review import canonical_reference
from evidence_quality import source_quality
from web_search import WebSearch,SearchLimit
from investigation import InvestigationService,TABLES
from tests import test_discovery_tools as fixtures


class AuditRegressions(unittest.TestCase):
    def test_profile_prefix_is_not_exact_account_anchor(self):
        row={'title':'Other','detail':'Public bio','reference':'https://www.instagram.com/fixture_other/'}
        self.assertFalse(relevance({'instagram':['fixture']},row)['strong_anchor'])
    def test_published_link_requires_whole_url_not_prefix(self):
        f=fixtures.DraftTests();f.setUp();f.run['records'][0]['detail']='Bio links https://www.instagram.com/fixture_other/'
        with self.assertRaises(ValueError):f.generate({'leads':[{'citation':'R1','url':'https://www.instagram.com/fixture'}]},'leads')
    def test_exact_supplied_url_can_anchor_review_without_name_match(self):
        ref='https://www.instagram.com/fixture/'
        self.assertTrue(relevance({'urls':[ref]},{'reference':ref,'title':'Nickname','detail':'Bio'})['strong_anchor'])
    def test_different_youtube_content_stays_distinct(self):
        self.assertNotEqual(canonical_reference('https://www.youtube.com/watch?v=AAA'),canonical_reference('https://www.youtube.com/watch?v=BBB'))
    def test_vsco_gallery_and_root_share_account_reference(self):
        self.assertEqual(canonical_reference('https://vsco.co/fixture'),canonical_reference('https://vsco.co/fixture/gallery'))
    def test_supported_profile_platforms_are_recognized(self):
        for ref in ['https://x.com/fixture','https://www.last.fm/user/fixture','https://open.spotify.com/user/fixture','https://www.pinterest.com/fixture/','https://medium.com/@fixture']:
            with self.subTest(ref=ref):self.assertTrue(source_quality({'reference':ref})['account_candidate'])
    def test_no_useful_model_claims_is_valid_empty_result(self):
        f=fixtures.DraftTests();f.setUp();self.assertEqual(f.generate({'claims':[]})['claims'],[])
    def test_same_url_citations_do_not_imply_independent_sources(self):
        f=fixtures.DraftTests();f.setUp();f.run['records'].append({'id':'R2','detail':'Another published public source excerpt.','reference':f.run['records'][0]['reference']})
        with self.assertRaisesRegex(ValueError,'eligible citations'):
            f.generate({'comparisons':[{'type':'agreement','citations':['R1','R2'],'quotes':['published public source','published public source'],'explanation':'Both excerpts mention a public source.'}],'next_step_indexes':[]},'assessment')
    def test_import_rejects_malformed_case_fields_before_commit(self):
        key='a'*24;tables={k:[] for k in TABLES};tables['cases']=[[key,json.dumps({'id':key,'title':'Fixture','notebook_ids':[],'names':123}),'2026-11-04']]
        raw=base64.b64encode(json.dumps({'format':'vidocq-workspace','schema':1,'tables':tables}).encode()).decode()
        with self.assertRaises(ValueError):InvestigationService(None)._bundle(raw,'')
    def test_invalid_profile_url_does_not_abort_report_synthesis(self):
        row={'id':'R001','reference':'https://steamcommunity.com:443/id/fixture','title':'Fixture','detail':'Bio','relevance':{'matched_identifiers':['usernames: fixture']}}
        result=synthesis({'case':{},'records':[row]});self.assertEqual(result['counts']['candidate_accounts'],0)
    def test_weak_first_occurrence_does_not_block_supported_followup(self):
        calls=[]
        weak={'title':'Other','detail':'https://www.instagram.com/linkedfixture/','reference':'https://example.org/weak'}
        strong={'title':'Example Person knownfixture','detail':weak['detail'],'reference':'https://example.org/strong'}
        def research(k,v):
            calls.append((k,v));return {'results':[{'provider':'Fixture','status':'ok','rows':[weak,strong] if k=='person' else []}],'links':[]}
        service=types.SimpleNamespace(cancel_flags={'fixture':threading.Event()},normalize=lambda k,v:(k,v),research=research,context_search=lambda v:{'results':[],'links':[]},collectors=None,connectors=None,llm=None,_save_run=lambda r:None)
        run={'id':'fixture','case':{'names':['Example Person'],'usernames':['knownfixture'],'investigation':{'enabled':True,'follow_clues':True,'max_searches':8,'max_followups':2,'depth':1}},'supplied_findings':[],'coverage':[],'prepared_searches':[]}
        execute(service,run);self.assertIn(('instagram','linkedfixture'),calls)
    def test_provider_cooldown_does_not_leak_to_other_provider(self):
        client=WebSearch();client.configure({'provider':'brave','key':'synthetic-key','enabled':True})
        network=MagicMock();network.open.side_effect=HTTPError('https://api.search.brave.com',429,'rate',{},None)
        with patch('web_search.build_opener',return_value=network):
            with self.assertRaises(ValueError):client.search('fixture')
            client.configure({'provider':'serper','key':'synthetic-second-key','enabled':True})
            try:client.search('other')
            except ValueError:pass
        self.assertEqual(network.open.call_count,2)
    def test_identical_concurrent_requests_share_one_network_attempt(self):
        client=WebSearch();client.configure({'provider':'brave','key':'synthetic-key','enabled':True})
        first=threading.Event();second=threading.Event();release=threading.Event();network=MagicMock();calls=[];errors=[]
        def response(req,timeout):
            calls.append(req);first.set()
            if len(calls)>1:second.set()
            release.wait(3);r=MagicMock();r.__enter__.return_value.read.return_value=b'{"query":{},"web":{"results":[]}}';return r
        network.open.side_effect=response
        def search():
            try:client.search('identical')
            except Exception as e:errors.append(type(e).__name__)
        with patch('web_search.build_opener',return_value=network):
            a=threading.Thread(target=search);b=threading.Thread(target=search);a.start();first.wait(2);b.start();second.wait(2);release.set();a.join(4);b.join(4)
        self.assertEqual(errors,[]);self.assertEqual(len(calls),1)


if __name__=='__main__':unittest.main()
