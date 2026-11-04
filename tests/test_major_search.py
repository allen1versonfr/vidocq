import json,unittest
from unittest.mock import patch
from urllib.error import HTTPError
from web_search import WebSearch,SearchLimit

class MajorSearchTests(unittest.TestCase):
    def response(self,value):
        response=unittest.mock.MagicMock();response.__enter__.return_value.read.return_value=json.dumps(value).encode();return response
    def test_fixed_endpoints_key_redaction_scope_and_cached_request_budget(self):
        for provider,payload in [('serper',{'organic':[{'title':'Profile','link':'https://www.instagram.com/example/','snippet':'Public snippet'},{'title':'Outside','link':'https://elsewhere.example','snippet':'Other'}]}),('serpapi',{'organic_results':[{'title':'Profile','link':'https://www.instagram.com/example/','snippet':'Public snippet'}]})]:
            client=WebSearch();client.configure({'provider':provider,'key':'synthetic-search-secret','enabled':True,'session_limit':2})
            with patch('web_search.build_opener') as opener:
                opener.return_value.open.return_value=self.response(payload)
                source,rows=client.search('example',site='instagram.com');client.search('example',site='instagram.com')
                self.assertEqual(opener.return_value.open.call_count,1);self.assertEqual(client.requests,1)
                req=opener.return_value.open.call_args.args[0]
                self.assertTrue(req.full_url.startswith('https://google.serper.dev/search' if provider=='serper' else 'https://serpapi.com/search.json'))
                if provider=='serper':self.assertEqual(req.get_header('X-api-key'),'synthetic-search-secret');self.assertEqual(req.get_method(),'POST')
                else:self.assertIn('api_key=synthetic-search-secret',req.full_url)
                self.assertNotIn('synthetic-search-secret',source+json.dumps(rows)+json.dumps(client.status()));self.assertEqual(len(rows),1)
                client.search('another');self.assertEqual(client.requests,2)
                with self.assertRaises(SearchLimit):client.search('third')
    def test_quota_and_malformed_responses_are_never_empty_success(self):
        client=WebSearch();client.configure({'provider':'serper','key':'synthetic-secret','enabled':True})
        with patch('web_search.build_opener') as opener:
            opener.return_value.open.side_effect=HTTPError('https://google.serper.dev/search',429,'rate',{},None)
            with self.assertRaises(SearchLimit):client.search('example')
            with self.assertRaises(SearchLimit):client.search('again')
            self.assertEqual(opener.return_value.open.call_count,1)
        for payload in [{},{'error':'No credit'},{'organic':'bad'},{'search_information':None}]:
            client=WebSearch();client.configure({'provider':'serpapi','key':'synthetic-secret','enabled':True})
            with patch('web_search.build_opener') as opener:
                opener.return_value.open.return_value=self.response(payload)
                with self.assertRaises(ValueError):client.search('example')
