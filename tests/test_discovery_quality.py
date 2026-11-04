import unittest
from unittest.mock import patch
from evidence_quality import evidence_gate,ranked_ai_records,source_quality
from profile_registry import account_identity,content_account_reference,canonical_reference
from search_queries import query_key,render_query
from research_workflow import platform_plan
from local_drafts import LocalDrafts
from tests import test_automation as engine_fixtures

class EvidenceTests(unittest.TestCase):
    def row(self,reference='https://example.org/bio',title='Alex Fixture',detail='Public biography.'):
        return {'id':'R1','reference':reference,'title':title,'detail':detail}
    def test_directories_and_property_sources_cannot_be_model_evidence(self):
        for host in ['www.whitepages.com','people.veripages.com','www.magicbricks.com','www.redfin.com']:
            row=self.row('https://'+host+'/profile');row['analyst_status']='Confirmed'
            self.assertFalse(evidence_gate(row,{'names':['Alex Fixture']})['eligible'])
        self.assertTrue(source_quality(self.row('https://whitepages.com.example.org/bio'))['usable_for_ai'])
    def test_unmatched_profile_is_not_sent_to_model(self):
        row=self.row('https://instagram.com/unrelatedfixture','Someone Else','A public account.')
        self.assertFalse(evidence_gate(row,{'names':['Alex Fixture']})['eligible'])
        row['analyst_status']='Confirmed';self.assertTrue(evidence_gate(row,{'names':['Alex Fixture']})['eligible'])
    def test_supplied_profile_is_usable_without_a_name_in_its_bio(self):
        row=self.row('https://www.instagram.com/publicfixture/','publicfixture','A public account bio.')
        self.assertEqual(evidence_gate(row,{'urls':['https://instagram.com/publicfixture']})['strength'],3)
    def test_name_only_remains_ambiguous_and_firstname_alone_is_filtered(self):
        gate=evidence_gate(self.row(),{'names':['Alex Fixture']})
        self.assertIn('namesake',gate['reason'])
        self.assertFalse(evidence_gate(self.row(title='Alex Another'),{'names':['Alex Fixture']})['eligible'])
    def test_exact_reference_ranks_before_name_only_and_richer_copy_wins(self):
        a=self.row();b=self.row('https://instagram.com/publicfixture','publicfixture');c=dict(b,id='R3',detail='A longer public biography with useful source text.')
        ranked=ranked_ai_records([a,b,c],{'names':['Alex Fixture'],'usernames':['publicfixture']})
        self.assertEqual([r['id'] for r in ranked],['R3','R1'])
    def test_no_relevant_evidence_abstains_without_model_network(self):
        client=LocalDrafts();client.configure({'enabled':True})
        run={'records':[self.row(title='Someone Else') ]}
        with patch('local_drafts.build_opener') as network:result=client.generate({'names':['Alex Fixture']},run,'synthesis',True)
        network.assert_not_called();self.assertEqual(result['claims'],[])
        self.assertEqual(run['ai']['phases'][0]['context_filter']['eligible_records'],0)
    def test_syndicated_identical_excerpts_do_not_fill_model_context(self):
        text='Alex Fixture appears in this public news excerpt, copied to a second news publisher.'
        first=self.row(detail=text);second=self.row('https://example.net/copy',detail=text)
        self.assertEqual(len(ranked_ai_records([first,second],{'names':['Alex Fixture']})),1)
    def test_name_only_model_quote_carries_namesake_warning(self):
        import json
        from unittest.mock import MagicMock
        client=LocalDrafts();client.configure({'enabled':True});row=self.row();run={'records':[row]}
        response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps({'choices':[{'message':{'content':json.dumps({'selection_ids':['R1-S1']})}}]}).encode()
        with patch('local_drafts.build_opener') as network:
            network.return_value.open.return_value=response;result=client.generate({'names':['Alex Fixture']},run,'synthesis',True)
        self.assertEqual(result['claims'][0]['evidence_strength'],'name-only');self.assertIn('namesake',result['claims'][0]['relevance_note'])

class ReferenceTests(unittest.TestCase):
    def test_linkedin_and_hudl_profiles_are_distinct_from_posts_or_teams(self):
        for url,canonical in [('https://www.linkedin.com/in/alex-fixture/?trk=public','https://linkedin.com/in/alex-fixture'),('https://www.hudl.com/profile/123456/Alex-Fixture','https://hudl.com/profile/123456')]:
            profile=account_identity(url);self.assertEqual(profile['reference'],canonical);self.assertEqual(profile['lookup_kind'],'reference');self.assertFalse(profile['ownership_verified'])
        for url in ['https://linkedin.com/company/fixture','https://hudl.com/team/123456','https://linkedin.com/in/alex-fixture/details/experience','https://hudl.com.evil.example/profile/123456']:self.assertIsNone(account_identity(url))
    def test_content_author_is_explicit_and_content_identity_is_preserved(self):
        content='https://www.tiktok.com/@publicfixture/video/123456'
        self.assertIsNone(account_identity(content));self.assertIn('/video/123456',canonical_reference(content))
        self.assertEqual(content_account_reference(content)['reference'],'https://tiktok.com/@publicfixture')
        self.assertEqual(content_account_reference('https://twitter.com/publicfixture/status/123456')['reference'],'https://x.com/publicfixture')
        for url in ['https://tiktok.com/@publicfixture/video/not-an-id','https://tiktok.com.evil.example/@publicfixture/video/123','https://instagram.com/p/123','https://x.com/search/status/123']:self.assertIsNone(content_account_reference(url))
    def test_query_keys_match_effective_provider_queries_but_keep_scopes(self):
        self.assertEqual(query_key([' Alex  Fixture ']),query_key(['Alex Fixture']))
        self.assertEqual(query_key(['Alex "Fixture"']),query_key(['Alex Fixture']))
        self.assertNotEqual(query_key(['publicfixture']),query_key(['publicfixture'],'instagram.com'))
        self.assertEqual(render_query(['Alex Fixture'],'tiktok.com'),'site:tiktok.com "Alex Fixture"')
        with self.assertRaises(ValueError):render_query(['publicfixture'],'evil.example')
    def test_platform_plan_uses_supplied_terms_and_skips_seed_platform(self):
        plan=platform_plan({'names':['Alex Fixture'],'usernames':['publicfixture'],'instagram':['publicfixture']})
        self.assertNotIn('instagram.com',{q['site'] for q in plan})
        self.assertTrue(all(t in ('Alex','Fixture','publicfixture') for q in plan for t in q['terms']))
        self.assertIn(['publicfixture'],[q['terms'] for q in plan[:4]]);self.assertIn(['Alex','Fixture'],[q['terms'] for q in plan[:4]])

class EngineQualityTests(unittest.TestCase):
    setUp=engine_fixtures.EngineTests.setUp
    tearDown=engine_fixtures.EngineTests.tearDown
    research=engine_fixtures.EngineTests.research
    context=engine_fixtures.EngineTests.context
    make=engine_fixtures.EngineTests.make
    run_case=engine_fixtures.EngineTests.run_case
    def test_ai_duplicate_full_name_does_not_consume_a_search_task(self):
        class Model:
            def generate(self,case,run,mode,consent):return {'queries':[{'terms':['Example Person'],'reason':'supplied name'}]} if mode=='planning' else {}
        self.service.llm=Model()
        run=self.run_case(self.make(investigation={'enabled':True,'ai_assisted':True,'allow_maigret':False}))
        self.assertEqual(run['ai']['executed_queries'],0)
        self.assertTrue(run['query_diagnostics']['duplicate_context_queries'])
    def test_platform_queries_run_after_baseline_even_if_results_are_nonempty(self):
        calls=[]
        def site(terms,domain):
            calls.append((terms,domain));return {'results':[{'provider':'Fixture index','status':'ok','rows':[{'title':'Example Person','detail':'Public account','reference':'https://www.tiktok.com/@otherfixture'}]}],'links':[]}
        self.service.site_search=site
        run=self.run_case(self.make(investigation={'enabled':True,'adaptive_queries':True,'allow_maigret':False,'max_searches':5,'platform_searches':2}))
        self.assertEqual(len(calls),2);self.assertLessEqual(run['completed'],5)
        self.assertEqual(len(run['query_diagnostics']['platform_queries']),2)
        self.assertTrue(any(r['reference']=='https://www.tiktok.com/@otherfixture' for r in run['records']))
        self.assertTrue(all(t.get('site') for t in run['search_log'] if t['origin']=='platform-index-coverage'))
    def test_zero_platform_cap_prevents_extra_requests(self):
        self.service.site_search=lambda *args:self.fail('Platform query ran with a zero limit')
        run=self.run_case(self.make(investigation={'enabled':True,'adaptive_queries':True,'allow_maigret':False,'platform_searches':0}))
        self.assertFalse(run['query_diagnostics']['platform_queries'])
    def test_indexed_content_adds_only_an_unverified_author_lead(self):
        content='https://www.tiktok.com/@contentfixture/video/123456'
        self.service.research=lambda k,v:{'results':[{'provider':'Fixture index','status':'ok','rows':[{'title':'Example Person','detail':'Example Person public clip','reference':content}]}],'links':[]}
        run=self.run_case(self.make(investigation={'enabled':True,'allow_maigret':False,'follow_clues':False}))
        original=next(r for r in run['records'] if r['reference']==content)
        lead=next(r for r in run['records'] if r['origin']=='derived-public-content')
        self.assertTrue(lead['lead_only']);self.assertEqual(lead['content_parent_citation'],original['id']);self.assertNotEqual(lead.get('analyst_status'),'Confirmed')
        self.assertNotIn('/video/',lead['reference']);self.assertFalse(lead['relevance']['can_expand'])
