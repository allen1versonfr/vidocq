import json
import unittest
from unittest.mock import patch
from discovery_tools import public_url,crawl,import_links,aliases,query_plan,fetch_public
from local_drafts import LocalDrafts
from tests import test_discovery_review as review_fixtures


class DiscoveryToolsTests(unittest.TestCase):
    def test_imports_preserve_distinct_provenance(self):
        photon=import_links({'mode':'photon','reference':'https://example.org','data':{'external':['https://github.com/example','mail@example.org'],'intel':['contact@example.org']}})
        self.assertEqual(len(photon['edges']),1);self.assertEqual(photon['edges'][0]['relation'],'photon-aggregate-lead')
        browser=import_links({'mode':'browser','data':{'schema':'vidocq-browser-v1','reference':'https://example.org','title':'Public bio','excerpt':'Links I reviewed','links':['https://github.com/example','javascript:bad']}})
        self.assertEqual(browser['edges'][0]['relation'],'browser-captured-link');self.assertEqual(browser['excerpt'],'Links I reviewed')
    def test_crawl_respects_robots_host_depth_and_no_actions(self):
        calls=[]
        def fetch(url):
            calls.append(url)
            if url.endswith('robots.txt'):return 'User-agent: *\nDisallow: /private'
            return '<a href="/next">Next</a><a href="/private">No</a><a href="https://elsewhere.org/x">External</a><a href="/logout">Action</a>'
        result=crawl({'consent':True,'url':'https://example.org','pages':5,'depth':2},fetch,lambda n:None)
        self.assertEqual(calls,['https://example.org/robots.txt','https://example.org/','https://example.org/next'])
        self.assertTrue(any(x['target']=='https://elsewhere.org/x' for x in result['edges']))
        self.assertTrue(result['errors']);self.assertEqual(len(result['pages']),2)
    def test_crawl_stops_without_permission_or_robots(self):
        with self.assertRaises(ValueError):crawl({'url':'https://example.org'})
        with self.assertRaises(ValueError):crawl({'url':'https://example.org','consent':True},lambda u:(_ for _ in ()).throw(ValueError('HTTP 404')),lambda n:None)
    def test_private_urls_and_dns_rebinding_are_blocked(self):
        for value in ['https://127.0.0.1','https://[::1]','https://user:pass@example.org','https://example.org:443','file:///etc/passwd','http://example.org','https://localhost.local']:
            with self.assertRaises(ValueError,msg=value):public_url(value)
        with patch('socket.getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]),patch('discovery_tools.PinnedHTTPS') as connection:
            with self.assertRaises(ValueError):fetch_public('https://example.org')
            connection.assert_not_called()
    def test_historical_alias_validation_and_query_provenance(self):
        old=aliases([{'handle':'oldname','platform':'Example','first_seen':'2020-01-01','last_seen':'2021-01-01','stable_id':'123'}])
        plan=query_plan({'names':['Ada Byron Lovelace'],'locations':['London'],'aliases':old,'urls':['https://example.org/bio']})
        self.assertIn(['Ada Lovelace'],[x['terms'] for x in plan]);self.assertTrue(any('historical' in x['reason'] for x in plan))
        with self.assertRaises(ValueError):aliases([{'handle':'oldname','first_seen':'2022-01-01','last_seen':'2021-01-01'}])


class LinkCaseTests(unittest.TestCase):
    setUp=review_fixtures.ReviewCaseTests.setUp
    tearDown=review_fixtures.ReviewCaseTests.tearDown
    make=review_fixtures.ReviewCaseTests.make
    run_case=review_fixtures.ReviewCaseTests.run_case
    research=review_fixtures.ReviewCaseTests.research
    context=review_fixtures.ReviewCaseTests.context
    def test_malformed_user_capture_cannot_break_a_report(self):
        case=self.make()
        for value in [[],{'edges':[{},'invalid',{'source':'javascript:bad','target':'x','relation':'made-up','observed_at':'now'}]}]:
            self.notebook.save_finding({'title':'Malformed supplied link capture','case_ids':[case['id']],'capture':{'origin':'public-links','reference':'https://example.org','excerpt':json.dumps(value)}})
        run=self.run_case(case)
        self.assertEqual(run['status'],'complete');self.assertEqual(run['link_evidence'],[])
    def test_link_import_is_auto_attached_without_automatic_pivots(self):
        case=self.make(aliases=[{'handle':'oldalias','last_seen':'2020-01-01'}])
        data=import_links({'mode':'photon','reference':'https://example.org','data':{'external':['https://unrelated.org/a']}})
        self.service.link_capture(case['id'],data,self.notebook.save_finding)
        run=self.run_case(case)
        self.assertEqual(run['link_evidence'][0]['relation'],'photon-aggregate-lead')
        self.assertNotIn(('domain','unrelated.org'),self.calls)
        self.assertIn(['oldalias'],self.contexts)
        updated=self.service.update(case['id'],{**case,'title':'Edited'})
        self.assertEqual(updated['aliases'][0]['handle'],'oldalias')


class DraftTests(unittest.TestCase):
    def setUp(self):
        self.client=LocalDrafts();self.client.configure({'enabled':True,'port':8080,'model':'local'})
        self.case={'names':['Ada Lovelace']};self.run={'records':[{'id':'R1','detail':'A published public source excerpt.','reference':'https://example.org'}]}
    def generate(self,result,mode='summary'):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n):return json.dumps({'choices':[{'message':{'content':json.dumps(result)}}]}).encode()
        with patch('local_drafts.build_opener') as opener:
            opener.return_value.open.return_value=Response()
            output=self.client.generate(self.case,self.run,mode,True)
            request=opener.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url,'http://127.0.0.1:8080/v1/chat/completions')
            self.assertNotIn('tools',json.loads(request.data))
            return output
    def test_validated_extracts_and_queries(self):
        self.assertTrue(self.generate({'claims':[{'citation':'R1','quote':'published public source'}]})['draft'])
        self.assertEqual(self.generate({'indexes':[0]},'queries')['queries'][0]['terms'],['Ada Lovelace'])
    def test_fabricated_citations_quotes_and_identifiers_rejected(self):
        for output in [{'claims':[{'citation':[],'quote':'published public source'}]},{'claims':[{'citation':'R2','quote':'published public source'}]},{'claims':[{'citation':'R1','quote':'invented ownership assertion'}]}]:
            with self.assertRaises(ValueError):self.generate(output)
        with self.assertRaises(ValueError):self.generate({'indexes':[999]},'queries')
    def test_disabled_or_unapproved_model_never_called(self):
        with patch('local_drafts.build_opener') as opener:
            with self.assertRaises(ValueError):self.client.generate(self.case,self.run,'queries',False)
            self.client.enabled=False
            with self.assertRaises(ValueError):self.client.generate(self.case,self.run,'queries',True)
            opener.assert_not_called()
