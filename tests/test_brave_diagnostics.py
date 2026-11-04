import json,unittest
from unittest.mock import patch,MagicMock
from urllib.error import HTTPError
import app
from web_search import WebSearch,SearchLimit
from retrieval_diagnostics import diagnose_control
from research_workflow import variations


class BraveDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.client=WebSearch();self.client.configure({'provider':'brave','key':'fixture-secret','enabled':True,'session_limit':1})
    def opener(self,items):
        opener=MagicMock();opener.open.return_value.__enter__.return_value.read.return_value=json.dumps({'query':{},'web':{'results':items}}).encode();return opener
    def test_cache_is_copy_safe_and_does_not_spend_budget(self):
        network=self.opener([{'url':'https://example.org/profile','title':'Original'}])
        with patch('web_search.build_opener',return_value=network):
            first=self.client.search('fixture');first[1][0]['title']='Edited';first.diagnostics['excluded']['malformed']=900
            second=self.client.search('fixture')
            self.assertEqual(second[1][0]['title'],'Original');self.assertEqual(second.diagnostics['excluded']['malformed'],0)
            self.assertTrue(second.diagnostics['cache_hit']);self.assertEqual(network.open.call_count,1);self.assertEqual(self.client.requests,1)
            with self.assertRaises(SearchLimit):self.client.search('other')
    def test_provider_and_adapter_counts_preserve_original_rank(self):
        network=self.opener([{'url':'https://elsewhere.example/'},{'url':'javascript:alert(1)'},None,{'url':'https://www.instagram.com/fixture/'},{'url':'https://www.instagram.com/fixture/'}])
        with patch('web_search.build_opener',return_value=network):
            result=app.run_adapter('Brave web index',lambda _:self.client.search('fixture',site='instagram.com'),'fixture')
        d=result['retrieval_diagnostics'];self.assertEqual(d['provider_rows'],5);self.assertEqual(d['retained_rows'],1)
        self.assertEqual(d['excluded'],{'outside_scope':1,'unsafe_url':1,'malformed':1,'duplicate':1});self.assertEqual(result['rows'][0]['index_rank'],4)
        self.assertNotIn('fixture-secret',json.dumps(result))
    def test_filtered_rows_are_not_diagnosed_as_empty_provider(self):
        network=self.opener([{'url':'https://elsewhere.example/'}])
        with patch('web_search.build_opener',return_value=network):
            result=app.run_adapter('Brave web index',lambda _:self.client.search('fixture',site='instagram.com'),'fixture')
        self.assertEqual(diagnose_control('https://www.instagram.com/fixture/',{'results':[result]})['stage'],'all_rows_filtered_by_adapter')
    def test_quota_cooldown_never_retries_network(self):
        self.client.session_limit=5;network=MagicMock();network.open.side_effect=HTTPError('https://api.search.brave.com',429,'rate',{},None)
        with patch('web_search.build_opener',return_value=network):
            with self.assertRaises(SearchLimit):self.client.search('fixture')
            with self.assertRaises(SearchLimit):self.client.search('other')
        self.assertEqual(network.open.call_count,1);self.assertEqual(self.client.requests,1)
    def test_name_token_relaxation_precedes_more_constrained_variants(self):
        qs=variations({'names':['Example Middle Person'],'usernames':['fixture'],'locations':['Example City']})
        self.assertEqual(qs[0]['terms'],['Example','Person'])
