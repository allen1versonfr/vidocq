"""Authenticated loopback companion for a separately installed Maigret 0.6.6.

Uses the library on explicitly selected mainstream sites. No recursion, extraction,
enrichment, cookies, proxies, auto-updates, activation or challenge bypass.
"""
import argparse
import asyncio
import copy
import hmac
import importlib.metadata
import importlib.resources
import json
import logging
import os
from pathlib import Path
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from collector_policy import MAIGRET_SITES,selected

def site_selection(names):
    from maigret.sites import MaigretDatabase
    # A bundled local database, never a URL or a caller-supplied database file.
    resource=importlib.resources.files('maigret').joinpath('resources/data.json')
    with importlib.resources.as_file(resource) as path:db=MaigretDatabase().load_from_path(str(path))
    all_sites=db.ranked_sites_dict(top=100000,disabled=False,id_type='username')
    chosen={};aliases={}
    for canonical in names:
        match=next(((name,site) for name,site in all_sites.items() if name.casefold()==canonical.casefold()),None)
        if not match:continue
        name,site=match;site=copy.deepcopy(site)
        urls=[getattr(site,'url_main',''),getattr(site,'url',''),getattr(site,'url_probe','')]
        if any(url and (urlparse(url).scheme not in ('https','http') or urlparse(url).hostname not in MAIGRET_SITES[canonical]) for url in urls):continue
        site.activation={}
        chosen[name]=site;aliases[name]=canonical
    return chosen,aliases

class Bridge:
    def __init__(self):self.lock=threading.RLock();self.jobs={};self.cancelled=set()
    def about(self):
        import maigret
        return {'service':'vidocq-maigret-bridge','protocol':1,'maigret_version':importlib.metadata.version('maigret'),'sites':list(MAIGRET_SITES),'public_checks_only':True}
    def cancel(self,run_id):
        if not isinstance(run_id,str) or not re.fullmatch('[0-9a-f]{24}',run_id):raise ValueError('Invalid run ID.')
        with self.lock:
            self.cancelled.add(run_id);job=self.jobs.get(run_id)
        if job:
            loop,task=job
            try:loop.call_soon_threadsafe(task.cancel)
            except RuntimeError:pass
        return {'cancel_requested':bool(job)}
    def search(self,p):
        username=p.get('username');run_id=p.get('run_id');names=selected(p.get('sites'),MAIGRET_SITES,10)
        if not isinstance(username,str) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}',username):raise ValueError('Invalid username.')
        if not isinstance(run_id,str) or not re.fullmatch('[0-9a-f]{24}',run_id):raise ValueError('Invalid run ID.')
        with self.lock:
            if self.jobs:raise ValueError('A Maigret job is already running.')
            self.jobs[run_id]=None
        partial={};cancelled=False;loop=asyncio.new_event_loop();task=None;aliases={}
        try:
            import maigret
            chosen,aliases=site_selection(names)
            logger=logging.getLogger('vidocq-maigret');logger.setLevel(logging.CRITICAL)
            async def collect():
                return await maigret.search(username=username,site_dict=chosen,logger=logger,
                    timeout=8,max_connections=3,retries=0,no_progressbar=True,debug=False,
                    proxy=None,tor_proxy=None,i2p_proxy=None,cookies=None,check_domains=False,
                    is_parsing_enabled=False,is_enrich_enabled=False,cloudflare_bypass=None,
                    dns_resolver='threaded',output_container=partial)
            task=loop.create_task(collect())
            with self.lock:
                self.jobs[run_id]=(loop,task)
                if run_id in self.cancelled:task.cancel()
            try:result=loop.run_until_complete(asyncio.wait_for(task,timeout=60))
            except (asyncio.CancelledError,asyncio.TimeoutError):result=partial;cancelled=True
            rows=[]
            for requested in names:
                actual=next((name for name,canonical in aliases.items() if canonical==requested),None)
                item=result.get(actual,{}) if isinstance(result,dict) else {}
                status=item.get('status');state=str(getattr(status,'status','Unknown'))
                if state not in ('Claimed','Available','Unknown','Illegal'):state='Unknown'
                url=item.get('url_user','') if isinstance(item,dict) else ''
                if url and (urlparse(url).scheme not in ('http','https') or urlparse(url).hostname not in MAIGRET_SITES[requested]):state='Unknown';url=''
                rows.append({'site':requested,'status':state,'url':url,'username':username})
            return {'username':username,'results':rows,'cancelled':cancelled,'protocol':1}
        finally:
            if task and not task.done():task.cancel();loop.run_until_complete(asyncio.gather(task,return_exceptions=True))
            loop.run_until_complete(loop.shutdown_asyncgens());loop.close()
            with self.lock:self.jobs.pop(run_id,None);self.cancelled.discard(run_id)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def authorized(self):
        host='127.0.0.1:'+str(self.server.server_port)
        return self.headers.get('Host')==host and self.headers.get('Origin') in (None,'http://'+host) and hmac.compare_digest(self.headers.get('X-Vidocq-Key',''),self.server.api_key)
    def send(self,status,data):
        raw=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if not self.authorized():return self.send(403,{'error':'Local API key required.'})
        if self.path!='/api/about':return self.send(404,{'error':'Unknown route.'})
        try:return self.send(200,self.server.bridge.about())
        except Exception:return self.send(503,{'error':'Install the supported Maigret dependency in this companion environment.'})
    def do_POST(self):
        if not self.authorized():return self.send(403,{'error':'Local API key required.'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if self.headers.get('Content-Type')!='application/json' or not 0<size<=64000:raise ValueError('Invalid request size/type.')
            p=json.loads(self.rfile.read(size))
            if not isinstance(p,dict):raise ValueError('Invalid request.')
            if self.path=='/api/search':return self.send(200,self.server.bridge.search(p))
            if self.path=='/api/cancel':return self.send(200,self.server.bridge.cancel(p.get('run_id')))
            return self.send(404,{'error':'Unknown route.'})
        except ValueError:return self.send(400,{'error':'Invalid or busy Maigret request.'})
        except Exception:return self.send(503,{'error':'Maigret could not complete this run. Check the companion installation.'})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8001);args=parser.parse_args()
    key=os.environ.get('VIDOCQ_MAIGRET_BRIDGE_KEY','')
    if not re.fullmatch('[A-Za-z0-9._~-]{16,256}',key):raise SystemExit('Set VIDOCQ_MAIGRET_BRIDGE_KEY to a private 16–256 character token before starting.')
    if not 1024<=args.port<=65535:raise SystemExit('Choose a loopback port from 1024 to 65535.')
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler);server.api_key=key;server.bridge=Bridge()
    print('Vidocq Maigret companion listening on 127.0.0.1:'+str(args.port),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
