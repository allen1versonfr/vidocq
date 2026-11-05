import json,unittest
from unittest.mock import patch
from tests import test_automation as engine_fixtures
from tests import test_discovery_tools as draft_fixtures
from profile_evidence import reviewed_profile,capture_profile,profile_graph
from research_workflow import variations,review_plan

class ProfileEvidenceTests(unittest.TestCase):
    def payload(self):return {'consent':True,'public_reviewed':True,'reference':'https://github.com/oldfixture','biography':'Public profile bio links https://gitlab.com/newfixture','display_name':'Example Person','handle':'oldfixture','stable_id':'1234','links':['https://gitlab.com/newfixture']}
    def test_reviewed_bio_preserves_link_evidence_without_claiming_ownership(self):
        result=reviewed_profile(self.payload());self.assertEqual(len(result['edges']),1);self.assertEqual(result['profile']['stable_id'],'1234');self.assertEqual(result['edges'][0]['relation'],'browser-captured-link')
        with self.assertRaises(ValueError):reviewed_profile({**self.payload(),'public_reviewed':False})
    def test_direct_profile_refuses_actions_private_hosts_and_queries_before_fetch(self):
        for ref in ['https://127.0.0.1/bio','https://example.org/','https://example.org/login','https://example.org/bio?action=follow']:
            fetch=unittest.mock.MagicMock()
            with self.assertRaises(ValueError):capture_profile({'consent':True,'reference':ref},fetch)
            fetch.assert_not_called()
    def test_direct_capture_respects_robots_and_does_not_call_footer_a_bio_link(self):
        def fetch(url):return 'User-agent: *\nAllow: /' if url.endswith('/robots.txt') else '<title>Example public profile</title><meta name="description" content="Public example biography"><a href="https://elsewhere.example/footer">Footer</a>'
        result=capture_profile({'consent':True,'reference':'https://example.org/bio'},fetch)
        self.assertEqual(result['profile']['links'],[]);self.assertEqual(result['edges'][0]['relation'],'published-link')
        with self.assertRaises(ValueError):capture_profile({'consent':True,'reference':'https://example.org/bio'},lambda url:'User-agent: *\nDisallow: /')
    def test_stable_ids_are_platform_scoped_and_rejected_sources_are_excluded(self):
        def record(cid,ref,stable,status='Unverified'):return {'id':cid,'reference':ref,'analyst_status':status,'observations':{'profile':{'stable_id':stable,'biography':'Public example bio','links':[]}}}
        graph=profile_graph([record('R1','https://github.com/oldfixture','1234'),record('R2','https://github.com/newfixture','1234'),record('R3','https://gitlab.com/otherfixture','1234'),record('R4','https://github.com/rejectedfixture','1234','Rejected')])
        self.assertEqual(len(graph['edges']),1);self.assertEqual(graph['edges'][0]['relation'],'same-platform-id-observed');self.assertFalse(graph['edges'][0]['ownership_verified']);self.assertEqual(len(graph['nodes']),3)

class WorkflowEngineTests(unittest.TestCase):
    setUp=engine_fixtures.EngineTests.setUp
    tearDown=engine_fixtures.EngineTests.tearDown
    make=engine_fixtures.EngineTests.make
    run_case=engine_fixtures.EngineTests.run_case
    research=engine_fixtures.EngineTests.research
    context=engine_fixtures.EngineTests.context
    def test_discovery_pages_only_trigger_variations_without_counting_as_accounts(self):
        def noisy(terms):return {'results':[{'provider':'Brave web index','status':'ok','rows':[{'title':'Example Person example','detail':'Example Person example in a name list','reference':'https://www.tiktok.com/discover/example'}]}],'links':[]}
        self.service.context_search=noisy;self.service.research=lambda k,v:noisy([v])
        case=self.make(investigation={'enabled':True,'allow_maigret':False,'adaptive_queries':True,'adaptive_searches':2,'max_searches':6})
        run=self.run_case(case)
        self.assertTrue(run['query_variations']);self.assertTrue(all(v['trigger_reason']=='discovery-pages-only' for v in run['query_variations']))
        self.assertEqual(run['analysis']['counts']['candidate_accounts'],0);self.assertLessEqual(run['completed'],6)
    def test_empty_index_variations_run_within_cap_using_supplied_identifiers_only(self):
        def empty(terms):self.contexts.append(terms);return {'results':[{'provider':'Mwmbl free web index','status':'empty','rows':[]}],'links':[]}
        self.service.context_search=empty;self.service.research=lambda k,v:empty([v])
        case=self.make(investigation={'enabled':True,'allow_maigret':False,'adaptive_queries':True,'adaptive_searches':2,'max_searches':6},locations=['Example City'])
        run=self.run_case(case);self.assertEqual(len(run['query_variations']),2);self.assertLessEqual(run['completed'],6)
        self.assertTrue(any(t['origin']=='empty-result-query-variation' for t in run['search_log']))
        self.assertTrue(all(term in ['Example Person','example','Example City','Example','Person'] for v in run['query_variations'] for term in v['terms']))
    def test_reviewed_profile_new_report_preserves_original_snapshot_and_provenance(self):
        case=self.make(investigation={'enabled':True,'allow_maigret':False,'follow_published_links':True,'follow_clues':True,'depth':1,'max_followups':2,'max_searches':10})
        first=self.run_case(case);old=json.dumps(first,sort_keys=True)
        capture=reviewed_profile(ProfileEvidenceTests().payload());self.service.link_capture(case['id'],capture,self.notebook.save_finding)
        run=self.service.start(case['id'],True,continued_from=first['id'])
        import time
        deadline=time.monotonic()+3
        while self.service.active and time.monotonic()<deadline:time.sleep(.01)
        second=self.service.run(run['id']);self.assertEqual(second['continued_from'],first['id']);self.assertEqual(json.dumps(self.service.run(first['id']),sort_keys=True),old)
        self.assertTrue(second['profile_graph']['nodes']);self.assertTrue(second['link_evidence']);self.assertTrue(any(t['origin']=='approved-published-link' for t in second['search_log']))
        other=self.make()
        with self.assertRaises(ValueError):self.service.start(other['id'],True,continued_from=first['id'])
        self.assertEqual(review_plan(case,first)['previous_run'],first['id'])

class AssessmentTests(unittest.TestCase):
    setUp=draft_fixtures.DraftTests.setUp
    generate=draft_fixtures.DraftTests.generate
    def test_comparisons_require_two_cited_quotes_and_known_next_steps(self):
        self.run['records'].append({'id':'R2','detail':'A different public source has a different display name.','reference':'https://example.org/other','analyst_status':'Confirmed'})
        comparison={'type':'difference','citations':['R1','R2'],'quotes':['published public source','different display name'],'explanation':'The cited excerpts describe different public source text.'}
        result=self.generate({'comparisons':[comparison],'next_step_indexes':[0]},'assessment');self.assertEqual(len(result['comparisons']),1);self.assertTrue(result['next_steps'])
        for bad in [{**comparison,'citations':['R1','R1']},{**comparison,'quotes':['invented passage','different display name']},{**comparison,'explanation':'There are 9999 publications.'}]:
            result=self.generate({'comparisons':[bad],'next_step_indexes':[0]},'assessment')
            self.assertEqual(result['comparisons'],[]);self.assertEqual(len(result['rejected_items']),1);self.assertTrue(result['next_steps'])
        with self.assertRaises(ValueError):self.generate({'comparisons':[],'next_step_indexes':[999]},'assessment')
    def test_generic_ownership_warning_does_not_count_as_substantive_synthesis(self):
        self.run['records'][0]['detail']='Public username check only. A matching handle is not proof of account ownership or common identity.'
        result=self.generate({'claims':[{'citation':'R1','quote':'A matching handle is not proof of account ownership or common identity.','text':'Ownership is not established.'}]},'synthesis')
        self.assertEqual(result['claims'],[])


class ProfileURLPlanningTests(unittest.TestCase):
    def test_url_only_seed_has_cross_platform_handle_queries(self):
        from research_workflow import platform_plan
        plan=platform_plan({'urls':['https://www.instagram.com/fixture_handle/']})
        self.assertTrue(plan)
        self.assertTrue(all(q['terms']==['fixture_handle'] for q in plan))
        self.assertIn('tiktok.com',[q['site'] for q in plan])
        self.assertNotIn('instagram.com',[q['site'] for q in plan])

    def test_content_navigation_and_opaque_ids_are_not_handle_seeds(self):
        from research_workflow import platform_plan
        for url in ['https://instagram.com/p/abcdef/', 'https://twitch.tv/directory',
                    'https://open.spotify.com/user/abc123', 'https://hudl.com/profile/123',
                    'https://linkedin.com/in/example-person-123']:
            self.assertEqual(platform_plan({'urls':[url]}),[],url)

    def test_url_and_explicit_handle_are_deduplicated(self):
        from research_workflow import platform_plan
        a={'usernames':['Fixture_Handle'],'urls':['https://instagram.com/fixture_handle/']}
        plan=platform_plan(a)
        self.assertEqual(len(plan),3)
        self.assertTrue(all(q['terms']==['Fixture_Handle'] for q in plan))
