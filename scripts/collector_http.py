"""MIT licensed authenticated loopback server for single-job collector companions."""
import argparse,hmac,json,os,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

def serve(service,handler):
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,required=True);parser.add_argument('--data',required=True);args=parser.parse_args()
    key=os.environ.get('VIDOCQ_COMPANION_KEY','');lock=threading.Lock()
    if len(key)<20:raise ValueError('Missing companion authentication.')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*a):pass
        def reply(self,status,value):
            body=json.dumps(value,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def allowed(self):return self.headers.get('Host')=='127.0.0.1:'+str(self.server.server_port) and hmac.compare_digest(self.headers.get('X-Vidocq-Key',''),key)
        def do_GET(self):
            if not self.allowed():return self.reply(401,{'error':'Authentication required.'})
            if self.path=='/api/about':return self.reply(200,{'service':'vidocq-'+service,'protocol':1,**({'repository':'https://github.com/Datalux/Osintgram'} if service=='osintgram' else {})})
            self.reply(404,{'error':'Unknown route.'})
        def do_POST(self):
            if not self.allowed():return self.reply(401,{'error':'Authentication required.'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 1<=size<=200000:raise ValueError('Invalid request size.')
                payload=json.loads(self.rfile.read(size))
                if not isinstance(payload,dict):raise ValueError('Invalid request.')
                if self.path=='/api/cancel':return self.reply(200,handler(self.path,payload))
                if not lock.acquire(blocking=False):return self.reply(409,{'error':'A collector job is already running.'})
                try:result=handler(self.path,payload)
                finally:lock.release()
                self.reply(200,result)
            except ValueError as e:self.reply(400,{'error':str(e)[:300]})
            except Exception:self.reply(502,{'error':'Collector failed. Check credentials, access and quota. No raw provider response was logged.'})
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler);server.daemon_threads=True;server.serve_forever()
