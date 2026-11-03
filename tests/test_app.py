import importlib.util,json,tempfile,threading,unittest,urllib.error,urllib.request
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('desk',Path(__file__).parents[1]/'app.py');app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
class PolicyTests(unittest.TestCase):
 def test_normalization(self):
  self.assertEqual(app.normalize('auto','example.com'),('domain','example.com'))
  self.assertEqual(app.normalize('auto','sample@example.com')[0],'email')
  self.assertEqual(app.normalize('auto','8.8.8.8')[0],'ip')
  for k,v in [('ip','127.0.0.1'),('ip','192.168.0.1'),('domain','example.com/path'),('domain','example.com@evil.test'),('domain','example.com:443'),('email','a@b')]:
   with self.assertRaises(ValueError):app.normalize(k,v)
 def test_network_allowlist_and_redirect(self):
  for u in ['https://example.com','https://crt.sh.evil.test','http://crt.sh','https://u:p@crt.sh','https://crt.sh:8443','file:///etc/passwd']:
   with self.assertRaises(ValueError):app.check_provider_url(u)
  with self.assertRaises(ValueError):app.ProviderRedirect().redirect_request(None,None,302,'',{},'https://example.com')
 def test_username_email_no_enumeration(self):
  with patch.object(app,'get_json') as request:
   for k,v in [('username','sample'),('email','sample@example.com')]:
    r=app.research(k,v);self.assertEqual(r['results'],[]);self.assertTrue(all(app.allowed_external(x['url']) for x in r['links']))
   request.assert_not_called()
 def test_archive_metadata_only(self):
  with patch.object(app,'get_json',return_value={'archived_snapshots':{'closest':{'url':'https://web.archive.org/web/1/https://example.com','timestamp':'20200101','available':True,'status':'200'}}}) as request:
   _,rows=app.archive('example.com');self.assertEqual(request.call_count,1);self.assertEqual(app.urlparse(request.call_args.args[0]).hostname,'archive.org');self.assertNotIn('url',rows[0])
 def test_domain_queries_only_indices(self):
  def response(u):
   self.assertIn(app.urlparse(u).hostname,('archive.org','crt.sh'));return [] if 'crt.sh' in u else {'archived_snapshots':{}}
  with patch.object(app,'get_json',side_effect=response):
   r=app.research('domain','example.com');self.assertEqual(len(r['results']),2);self.assertTrue(all(x['status']=='empty' for x in r['results']))
 def test_failure_is_explicit(self):
  with patch.object(app,'get_json',side_effect=TimeoutError()):self.assertTrue(all(x['status']=='error' for x in app.research('domain','example.com')['results']))
 def test_no_live_links(self):
  for u in ['https://example.com','https://web.archive.org/web/1/https://example.com','https://archive.org/save/https://example.com','https://en.wikipedia.org/wiki/Example','https://www.google.com/url?q=https://example.com','https://crt.sh/scan']:
   self.assertFalse(app.allowed_external(u))
 def test_certificate_dedup(self):
  with patch.object(app,'get_json',return_value=[{'name_value':'example.com\nwww.example.com'},{'name_value':'example.com'}]):self.assertEqual(len(app.certificates('example.com')[1]),2)
class ServerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.old=app.DATA;app.DATA=Path(cls.temp.name);cls.server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);threading.Thread(target=cls.server.serve_forever,daemon=True).start();cls.base='http://127.0.0.1:'+str(cls.server.server_port)
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();app.DATA=cls.old;cls.temp.cleanup()
 def req(self,path,data=None,headers=None):
  h={'Cookie':'desk='+app.COOKIE};h.update({'Content-Type':'application/json'} if data is not None else {});h.update(headers or {});return urllib.request.urlopen(urllib.request.Request(self.base+path,data=None if data is None else json.dumps(data).encode(),headers=h))
 def test_persistence(self):
  with self.req('/api/save',{'title':'Test finding','notes':'Evidence'}) as r:self.assertEqual(r.status,200)
  with self.req('/api/findings') as r:self.assertTrue(any(x['title']=='Test finding' for x in json.load(r)))
 def test_csrf_and_host(self):
  for h in [{'Origin':'https://evil.test'},{'Cookie':''},{'Host':'evil.test'}]:
   with self.assertRaises(urllib.error.HTTPError) as e:self.req('/api/save',{'title':'Blocked'},h)
   self.assertEqual(e.exception.code,403)
 def test_ui_csp(self):
  with self.req('/') as r:self.assertIn("connect-src 'self'",r.headers['Content-Security-Policy']);self.assertIn('HttpOnly',r.headers['Set-Cookie'])
 def test_invalid_input(self):
  with self.assertRaises(urllib.error.HTTPError) as e:self.req('/api/research',{'kind':'domain','value':'127.0.0.1'})
  self.assertEqual(e.exception.code,400)
 def test_block_external(self):
  with patch.object(app.webbrowser,'open') as browser:
   with self.assertRaises(urllib.error.HTTPError):self.req('/api/open',{'url':'https://example.com'})
   browser.assert_not_called()
if __name__=='__main__':unittest.main()
