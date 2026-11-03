import base64,io,json,unittest
from unittest.mock import patch,MagicMock
from urllib.error import HTTPError
import image_search as sauce
from PIL import Image

def example_image():
 out=io.BytesIO();im=Image.new('RGB',(24,24),'blue');exif=Image.Exif();exif[270]='private metadata';im.save(out,format='JPEG',exif=exif);return base64.b64encode(out.getvalue()).decode()

def payload(**kw):
 return dict({'image':example_image(),'api_key':'x'*40,'consent':True},**kw)

class ImageTests(unittest.TestCase):
 def test_metadata_stripped(self):
  with Image.open(io.BytesIO(sauce.prepare_image(example_image()))) as im:self.assertEqual(len(im.getexif()),0);self.assertNotIn('comment',im.info)
 def test_consent_required_no_network(self):
  with patch.object(sauce,'build_opener') as request:
   with self.assertRaises(ValueError):sauce.search_image(payload(consent=False))
   request.assert_not_called()
 def test_missing_key_no_network(self):
  with patch.object(sauce,'build_opener') as request:
   with self.assertRaises(ValueError):sauce.search_image(payload(api_key=''))
   request.assert_not_called()
 def test_invalid_image_no_network(self):
  with patch.object(sauce,'build_opener') as request:
   with self.assertRaises(ValueError):sauce.search_image(payload(image=base64.b64encode(b'not an image').decode()))
   request.assert_not_called()
 def test_remote_url_rejected(self):
  with self.assertRaises(ValueError):sauce.prepare_image('https://example.com/image.jpg')
 def test_oversize_encoded_image_rejected(self):
  with self.assertRaises(ValueError):sauce.prepare_image('a'*7_000_001)
 def test_redirect_never_forwarded(self):
  with self.assertRaises(ValueError):sauce.NoUploadRedirect().redirect_request(None,None,302,'',{},'https://evil.test')
 def test_request_only_saucenao_no_key_in_url(self):
  response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps({'header':{'status':0},'results':[]}).encode()
  opener=MagicMock();opener.open.return_value=response
  with patch.object(sauce,'build_opener',return_value=opener):
   d=sauce.search_image(payload());req=opener.open.call_args.args[0]
   self.assertEqual(req.full_url,'https://saucenao.com/search.php');self.assertEqual(req.method,'POST');self.assertIn(('x'*40).encode(),req.data);self.assertNotIn(b'private metadata',req.data);self.assertNotIn(b'name="url"',req.data);self.assertEqual(d['rows'],[])
 def test_no_remote_thumbnails_and_score_sorted(self):
  data={'header':{'status':0,'short_remaining':2,'long_remaining':50},'results':[{'header':{'similarity':'10','index_name':'a','thumbnail':'https://evil.test/track.png'},'data':{'title':'A','ext_urls':['javascript:bad','https://example.com/a']}},{'header':{'similarity':'90'},'data':{'title':'B'}}]}
  result=sauce.parse_response(data);self.assertEqual(result['rows'][0]['title'],'B');self.assertNotIn('https://evil.test/track.png',json.dumps(result));self.assertTrue(all('thumbnail' not in r for r in result['rows']));self.assertEqual(result['rows'][1]['sources'],['https://example.com/a'])
 def test_nan_clamped(self):
  r=sauce.parse_response({'header':{'status':0},'results':[{'header':{'similarity':'NaN'},'data':{}}]});self.assertEqual(r['rows'][0]['similarity'],0)
 def test_provider_message_not_echoed(self):
  with self.assertRaises(ValueError) as e:sauce.parse_response({'header':{'status':-1,'message':'secret API key'}})
  self.assertNotIn('secret',str(e.exception))
 def test_rate_limit_explicit(self):
  opener=MagicMock();opener.open.side_effect=HTTPError(sauce.ENDPOINT,429,'rate limited',{},None)
  with patch.object(sauce,'build_opener',return_value=opener):
   with self.assertRaisesRegex(ValueError,'rate limit'):sauce.search_image(payload())
if __name__=='__main__':unittest.main()
