import json
import unittest
from unittest.mock import patch,MagicMock
from urllib.error import HTTPError
from urllib.parse import parse_qs,urlparse

import app
from web_search import WebSearch,SearchNotConfigured,SearchLimit

class FreeSearchTests(unittest.TestCase):
    def setUp(self):
        with patch.dict('os.environ',{},clear=True):self.client=WebSearch()
    def response(self,query='"Example Person"',rows=None):
        if rows is None:rows=[{'title':'Example Person','content':'Public indexed snippet','url':'https://example.org/profile','engine':'mwmbl'}]
        return {'query':query,'number_of_results':len(rows),'results':rows}
    def opener(self,data):
        opener=MagicMock();opener.open.return_value.__enter__.return_value.read.return_value=json.dumps(data).encode();return opener
    def enable(self):self.client.configure({'provider':'mwmbl','enabled':True})
    def test_free_choice_requires_no_key_and_no_query_until_enabled(self):
        self.assertEqual(self.client.status()['provider'],'mwmbl');self.assertFalse(self.client.status()['requires_key'])
        with patch('web_search.build_opener') as network:
            with self.assertRaises(SearchNotConfigured):self.client.search('Example Person')
            network.assert_not_called()
        self.enable();self.assertTrue(self.client.status()['configured']);self.assertFalse(self.client.status()['key_configured'])
    def test_anonymous_results_and_no_paid_key_forwarding(self):
        self.client.configure({'key':'private-brave-key','enabled':True});self.enable()
        opener=self.opener(self.response())
        with patch('web_search.build_opener',return_value=opener):source,rows=self.client.search('Example Person')
        request=opener.open.call_args.args[0]
        self.assertEqual(urlparse(source).hostname,'api.mwmbl.org');self.assertEqual(urlparse(source).path,'/api/v2/search/')
        self.assertEqual(parse_qs(urlparse(source).query)['q'],['"Example Person"'])
        self.assertFalse(any('key' in k.lower() or 'token' in k.lower() for k in request.headers))
        self.assertEqual(rows[0]['reference'],'https://example.org/profile');self.assertNotIn('private-brave-key',source+json.dumps(rows)+json.dumps(self.client.status()))
        self.assertEqual(opener.open.call_count,1)
    def test_cache_avoids_duplicate_requests_and_cannot_be_mutated(self):
        self.enable();opener=self.opener(self.response())
        with patch('web_search.build_opener',return_value=opener):
            _,rows=self.client.search('Example Person');rows[0]['title']='Changed locally'
            _,again=self.client.search('Example Person')
        self.assertEqual(again[0]['title'],'Example Person');self.assertEqual(opener.open.call_count,1);self.assertEqual(self.client.requests,1)
    def test_rate_limit_stops_without_paid_fallback(self):
        self.enable();opener=MagicMock();opener.open.side_effect=HTTPError('https://api.mwmbl.org',429,'quota',{'Retry-After':'300'},None)
        with patch('web_search.build_opener',return_value=opener):
            with self.assertRaises(SearchLimit):self.client.search('Example Person')
            with self.assertRaises(SearchLimit):self.client.search('Different Person')
        self.assertEqual(opener.open.call_count,1);self.assertGreaterEqual(self.client.status()['free_cooldown_seconds'],299)
        self.assertEqual(self.client.provider,'mwmbl');self.assertFalse(self.client.key)
    def test_bad_response_is_not_empty(self):
        self.enable()
        for data in [{},[],{'query':'other','number_of_results':0,'results':[]},{'query':'"Example Person"','number_of_results':3,'results':[]},self.response(rows=[{'url':'https://example.org'}])]:
            self.client.next_free=0
            with patch('web_search.build_opener',return_value=self.opener(data)):
                with self.assertRaises(ValueError):self.client.search('Example Person')
    def test_successful_empty_response_is_distinct(self):
        self.enable()
        with patch('web_search.build_opener',return_value=self.opener(self.response(rows=[]))):self.assertEqual(self.client.search('Example Person')[1],[])
    def test_http_outages_and_html_challenges_are_errors(self):
        self.enable()
        for code in (401,403,500):
            self.client.next_free=0;opener=MagicMock();opener.open.side_effect=HTTPError('https://api.mwmbl.org',code,'error',{},None)
            with patch('web_search.build_opener',return_value=opener):
                with self.assertRaises(ValueError):self.client.search('Example Person')
        self.client.next_free=0;opener=MagicMock();opener.open.return_value.__enter__.return_value.read.return_value=b'<html>Challenge</html>'
        with patch('web_search.build_opener',return_value=opener):
            with self.assertRaises(ValueError):self.client.search('Example Person')
    def test_scoped_results_filter_other_hosts_and_invalid_urls(self):
        self.enable();urls=['https://www.instagram.com/example/','https://instagram.com.evil.test/example','https://user:pass@instagram.com/example','javascript:alert(1)']
        data=self.response('site:instagram.com "example"',[{'title':'Example','content':'Indexed','url':u} for u in urls])
        with patch('web_search.build_opener',return_value=self.opener(data)):
            _,rows=self.client.search('example',site='instagram.com')
        self.assertEqual([r['reference'] for r in rows],[urls[0]])
    def test_context_terms_and_html_are_handled_as_data(self):
        self.enable();data=self.response('"Example Person" "Example City"',[{'title':'<b>Example</b>','content':'A &amp; B','url':'https://example.org'}])
        with patch('web_search.build_opener',return_value=self.opener(data)):
            source,rows=self.client.search_terms(['Example Person','Example City'])
        self.assertEqual(rows[0]['title'],'Example');self.assertEqual(rows[0]['detail'],'A & B')
        self.assertEqual(parse_qs(urlparse(source).query)['q'],['"Example Person" "Example City"'])
    def test_free_session_cap_and_provider_validation(self):
        self.enable();self.client.requests=100
        with patch('web_search.build_opener') as network:
            with self.assertRaises(SearchLimit):self.client.search('Example Person')
            network.assert_not_called()
        with self.assertRaises(ValueError):self.client.configure({'provider':'https://unreviewed.example','enabled':True})
        self.assertEqual(self.client.provider,'mwmbl')
    def test_person_research_does_not_fill_missing_search_with_wikipedia_noise(self):
        with patch.object(app,'WEB_SEARCH',self.client),patch.object(app,'get_json') as wikipedia:
            result=app.research('person','Example Person')
        wikipedia.assert_not_called();self.assertEqual(result['search_outcome'],'not-searched');self.assertEqual(len(result['results']),1)
        self.assertEqual(result['results'][0]['provider'],'Mwmbl free web index')
    def test_brave_remains_explicit_optional_and_environment_compatible(self):
        with self.assertRaises(ValueError):self.client.configure({'provider':'brave','enabled':True})
        with patch.dict('os.environ',{'VIDOCQ_BRAVE_API_KEY':'existing-key'}):legacy=WebSearch()
        self.assertEqual(legacy.provider,'brave');self.assertTrue(legacy.enabled)
        legacy.configure({'provider':'mwmbl','enabled':True});self.assertFalse(legacy.status()['requires_key'])
