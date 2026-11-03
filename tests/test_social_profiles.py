import json,tempfile,unittest
from pathlib import Path
from urllib.parse import parse_qs,urlparse
from unittest.mock import patch,MagicMock
import app
from social_profiles import PLATFORMS,normalize_profile,profile_reference
from web_search import WebSearch
from scripts.build_icon import build
from PIL import Image

class SocialTests(unittest.TestCase):
 def test_handle_url_and_tracking_normalization(self):
  for platform,url in [('instagram','https://www.instagram.com/Example.Name/?igsh=tracking#bio'),('tiktok','https://www.tiktok.com/@Example.Name?lang=en')]:
   self.assertEqual(normalize_profile(platform,'@Example.Name'),'example.name')
   self.assertEqual(normalize_profile(platform,url),'example.name')
   self.assertNotIn('tracking',profile_reference(platform,'example.name'))
 def test_auto_profile_url_is_not_domain(self):
  for platform,url in [('instagram','instagram.com/example/'),('tiktok','https://www.tiktok.com/@example')]:self.assertEqual(app.normalize('auto',url),(platform,'example'))
  self.assertEqual(app.normalize('auto','instagram.com'),('domain','instagram.com'))
  self.assertEqual(app.normalize('auto','@example'),('username','@example'))
 def test_reject_posts_short_links_wrong_hosts_and_injection(self):
  for platform,value in [('instagram','https://instagram.com/p/123'),('instagram','https://instagram.com/reel/123'),('instagram','https://instagram.com.evil.test/example'),('instagram','https://u:p@instagram.com/example'),('instagram','https://instagram.com:443/example'),('instagram','https://instagram.com/%65xample'),('instagram','Display Name'),('instagram','x\nsite:evil.test'),('tiktok','https://vm.tiktok.com/short/'),('tiktok','https://www.tiktok.com/@example/video/123'),('tiktok','https://instagram.com/example'),('tiktok','../example')]:
   with self.subTest(value=value):
    with self.assertRaises(ValueError):normalize_profile(platform,value)
 def test_prepared_queries_scoped_and_never_original_pages(self):
  for platform in PLATFORMS:
   links=app.prepared_links(platform,'example');self.assertEqual(len(links),3)
   for link in links:
    self.assertTrue(app.allowed_external(link['url']));self.assertEqual(parse_qs(urlparse(link['url']).query)['q'],['site:'+PLATFORMS[platform]['host']+' "example"'])
   self.assertFalse(app.allowed_external(profile_reference(platform,'example')))
 def test_unconnected_social_research_does_not_request(self):
  with patch.dict('os.environ',{},clear=True):client=WebSearch()
  with patch.object(app,'WEB_SEARCH',client),patch.object(app,'get_json') as request,patch('web_search.build_opener') as brave:
   result=app.research('tiktok','https://www.tiktok.com/@example')
   request.assert_not_called();brave.assert_not_called()
  self.assertEqual(result['search_outcome'],'not-searched');self.assertEqual(result['social_profile']['handle'],'example')
 def test_connected_research_supplies_platform_scope(self):
  with patch.object(app.WEB_SEARCH,'search',return_value=('https://api.search.brave.com', [{'title':'Indexed mention','detail':'Unverified','reference':'https://www.instagram.com/example/'}])) as search:
   result=app.research('instagram','@Example')
  search.assert_called_once_with('example',site='instagram.com');self.assertEqual(result['search_outcome'],'records-found')
 def test_scoped_brave_query_and_reference_filter(self):
  client=WebSearch();client.configure({'key':'test-key','enabled':True})
  rows=[{'title':'Example','url':url,'description':'Unverified'} for url in ('https://www.tiktok.com/@example','https://tiktok.com.evil.test/','https://other.example/')]
  opener=MagicMock();opener.open.return_value.__enter__.return_value.read.return_value=json.dumps({'query':{},'web':{'results':rows}}).encode()
  with patch('web_search.build_opener',return_value=opener):source,results=client.search('example',site='tiktok.com')
  self.assertEqual(parse_qs(urlparse(source).query)['q'],['site:tiktok.com "example"']);self.assertEqual(len(results),1);self.assertEqual(opener.open.call_count,1)
 def test_arbitrary_search_scope_rejected_without_network(self):
  client=WebSearch()
  with patch('web_search.build_opener') as request:
   with self.assertRaises(ValueError):client.search('example',site='evil.example')
   request.assert_not_called()
 def test_icon_contains_windows_sizes_and_transparency(self):
  with tempfile.TemporaryDirectory() as root:
   path=build(root)
   with Image.open(path) as icon:
    self.assertTrue({(16,16),(32,32),(48,48),(256,256)}.issubset(icon.ico.sizes()))
    self.assertEqual(icon.convert('RGBA').getpixel((0,0))[3],0)

class VSCOTests(unittest.TestCase):
 def test_vsco_gallery_url_and_dash_handle(self):
  self.assertEqual(normalize_profile('vsco','https://vsco.co/Example-Name/gallery?source=share'),'example-name')
  self.assertEqual(profile_reference('vsco','@Example-Name'),'https://vsco.co/example-name/')
  self.assertEqual(app.normalize('auto','vsco.co/example-name/gallery'),('vsco','example-name'))
 def test_vsco_reject_non_profile_and_invalid_handles(self):
  for value in ('ab','example_name','example.name','https://vs.co/short','https://vsco.co/example/media/123','https://vsco.co/search','https://vsco.co.evil.test/example'):
   with self.subTest(value=value):
    with self.assertRaises(ValueError):normalize_profile('vsco',value)
 def test_vsco_scope_sent_to_index_only(self):
  with patch.object(app.WEB_SEARCH,'search',return_value=('https://api.search.brave.com',[])) as search:
   result=app.research('vsco','https://vsco.co/example/gallery')
  search.assert_called_once_with('example',site='vsco.co');self.assertEqual(result['social_profile']['reference'],'https://vsco.co/example/')
