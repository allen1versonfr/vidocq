import json,unittest
from unittest.mock import patch,MagicMock
from urllib.error import HTTPError
import app
from web_search import WebSearch,SearchNotConfigured,SearchLimit,NoRedirect,outcome

class SearchTests(unittest.TestCase):
 def setUp(self):
  with patch.dict('os.environ',{},clear=True):self.client=WebSearch()
 def response(self,data):
  opener=MagicMock();opener.open.return_value.__enter__.return_value.read.return_value=json.dumps(data).encode();return opener
 def test_disconnected_does_not_request(self):
  with patch('web_search.build_opener') as request:
   with self.assertRaises(SearchNotConfigured):self.client.search('Example Person')
   request.assert_not_called()
  self.assertFalse(self.client.status()['configured'])
 def test_index_snippets_without_result_page_fetch(self):
  self.client.configure({'key':'secret-key','enabled':True})
  opener=self.response({'query':{'original':'Example'},'web':{'results':[{'title':'<b>Example</b>','description':'A &amp; B','url':'https://example.org/page'},{'url':'javascript:alert(1)'}]}})
  with patch('web_search.build_opener',return_value=opener):source,rows=self.client.search('Example Person')
  self.assertEqual(opener.open.call_count,1);req=opener.open.call_args.args[0]
  self.assertTrue(req.full_url.startswith('https://api.search.brave.com/'));self.assertEqual(rows[0]['detail'],'A & B');self.assertEqual(len(rows),1)
  self.assertNotIn('secret-key',source+json.dumps(self.client.status())+json.dumps(rows))
 def test_malformed_is_failure_not_empty(self):
  self.client.configure({'key':'secret-key','enabled':True})
  for data in [{},{'error':{}},{'query':{},'web':{}},[]]:
   with patch('web_search.build_opener',return_value=self.response(data)):
    with self.assertRaises(ValueError):self.client.search('Example')
  with patch('web_search.build_opener',return_value=self.response({'query':{}})):self.assertEqual(self.client.search('Example')[1],[])
 def test_auth_rate_and_outage_are_errors(self):
  self.client.configure({'key':'secret-key','enabled':True})
  for code in (401,403,429,503):
   opener=MagicMock();opener.open.side_effect=HTTPError('https://api.search.brave.com',code,'error',{},None)
   with patch('web_search.build_opener',return_value=opener):
    with self.assertRaises(ValueError) as error:self.client.search('Example')
   self.assertNotIn('secret-key',str(error.exception))
 def test_limit_and_forget(self):
  self.client.configure({'key':'secret-key','enabled':True});self.client.requests=100
  with patch('web_search.build_opener') as request:
   with self.assertRaises(SearchLimit):self.client.search('Example')
   request.assert_not_called()
  self.client.configure({'key':'','enabled':False});self.assertFalse(self.client.status()['configured'])
 def test_no_redirect_or_header_injection(self):
  with self.assertRaises(ValueError):NoRedirect().redirect_request(None,None,None,None,None,'https://example.org')
  with self.assertRaises(ValueError):self.client.configure({'key':'bad\nkey','enabled':True})
 def test_full_name_auto_detection(self):self.assertEqual(app.normalize('auto','Ada Lovelace'),('person','Ada Lovelace'))
 def test_bad_index_response_not_empty(self):
  with patch.object(app,'get_json',return_value={}):
   for fn in (app.encyclopedia,app.network_registry):self.assertEqual(app.run_adapter('Index',fn,'Example')['status'],'error')
 def test_outcome_does_not_confuse_offline_with_search(self):
  self.assertEqual(outcome([{'provider':'Offline phone metadata','status':'ok'}],[{'origin':'offline-metadata'}])[0],'not-searched')
  self.assertEqual(outcome([{'status':'error'}],[])[0],'sources-unavailable')
  self.assertEqual(outcome([{'status':'empty'},{'status':'error'}],[])[0],'incomplete')
  self.assertEqual(outcome([{'status':'empty'}],[])[0],'no-matches-in-searched-sources')
  self.assertEqual(outcome([],[{'origin':'retrieved'}])[0],'records-found')
