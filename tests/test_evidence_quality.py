import unittest
from evidence_quality import source_quality,ranked_ai_records
from assisted_investigation import relevance,synthesis
from retrieval_diagnostics import diagnose_control
from tests import test_discovery_tools as draft_fixtures


class QualityTests(unittest.TestCase):
    def row(self,url):return {'id':'R1','title':'Example Person fixture_handle','detail':'Example Person fixture_handle','reference':url}
    def test_discovery_pages_are_not_profiles_or_expansion_anchors(self):
        for url in ['https://www.tiktok.com/discover/fixture_handle','https://www.instagram.com/explore/tags/fixture_handle/']:
            row=self.row(url);row['relevance']=relevance({'names':['Example Person'],'usernames':['fixture_handle']},row)
            self.assertFalse(row['relevance']['can_expand']);self.assertFalse(source_quality(row)['account_candidate'])
            result=synthesis({'case':{},'records':[row]})
            self.assertEqual(result['counts']['candidate_records'],0);self.assertEqual(result['counts']['candidate_accounts'],0)
    def test_profile_content_and_discovery_have_distinct_types(self):
        for url in ['https://www.tiktok.com/@fixture_handle','https://www.instagram.com/fixture_handle/','https://github.com/fixture_handle']:
            self.assertTrue(source_quality(self.row(url))['account_candidate'])
        self.assertFalse(source_quality(self.row('https://www.tiktok.com/@fixture_handle/video/123'))['account_candidate'])
        self.assertFalse(source_quality(self.row('https://tiktok.com.evil.example/discover/example'))['account_candidate'])
    def test_ai_prioritizes_profile_evidence_before_context_limit(self):
        rows=[self.row('https://www.tiktok.com/discover/fixture') for _ in range(15)]
        target=self.row('https://www.instagram.com/fixture_handle/');target['observations']={'profile':{'biography':'Public fixture'}}
        self.assertEqual(ranked_ai_records(rows+[target]),[target])
        context=self.row('https://example.org/article')
        self.assertEqual(ranked_ai_records([context]*15+[target])[0],target)
    def test_offline_diagnosis_separates_empty_wrong_and_dropped(self):
        url='https://www.instagram.com/fixture_handle/'
        def report(rows,status='ok'):return {'results':[{'provider':'Brave web index','status':status,'rows':rows}]}
        self.assertEqual(diagnose_control(url,report([],'empty'))['stage'],'no_rows_returned')
        self.assertEqual(diagnose_control(url,report([self.row('https://www.tiktok.com/discover/fixture')]))['stage'],'target_not_in_returned_rows')
        self.assertEqual(diagnose_control(url,report([self.row(url)]),[])['stage'],'lost_after_retrieval')
        self.assertEqual(diagnose_control(url,report([self.row(url)]))['stage'],'exact_profile_returned')
        self.assertEqual(diagnose_control(url,report([],'error'))['stage'],'source_incomplete')


class DraftQualityTests(unittest.TestCase):
    setUp=draft_fixtures.DraftTests.setUp
    generate=draft_fixtures.DraftTests.generate
    def test_model_association_paraphrase_is_not_published_as_source_fact(self):
        self.run['records'][0]['detail']='Example Person and Other Person appear in a list.'
        result=self.generate({'claims':[{'citation':'R1','quote':'Example Person and Other Person','text':'Example Person is associated with Other Person.'}]},'synthesis')
        self.assertNotIn('associated',result['claims'][0]['text']);self.assertEqual(result['claims'][0]['quote'],'Example Person and Other Person')
    def test_discovery_page_cannot_be_cited_as_ai_evidence(self):
        self.run['records'][0]['reference']='https://www.tiktok.com/discover/fixture'
        with self.assertRaises(ValueError):self.generate({'claims':[{'citation':'R1','quote':'published public source'}]})
