"""GPL-3.0-only Photon runner with Vidocq's bounded public HTTPS transport."""
import contextlib,io,json,os,runpy,sys,tempfile,time
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from discovery_tools import public_url,fetch_public,Links,now

def collect(p,fetch=fetch_public):
    if p.get('consent') is not True:raise ValueError('Approve direct public-site requests first.')
    root=public_url(p.get('url',''));host=urlparse(root).hostname;pages=p.get('pages',1);depth=p.get('depth',0)
    if type(pages) is not int or not 1<=pages<=5 or type(depth) is not int or not 0<=depth<=2 or urlparse(root).query:raise ValueError('Use a query-free HTTPS root, 1–5 pages, depth 0–2.')
    robots_url='https://'+host+'/robots.txt';robots_body=fetch(robots_url);robots=RobotFileParser();robots.parse(robots_body.splitlines())
    delay=max(1,robots.crawl_delay('*') or 1)
    if delay>10:raise ValueError('Robots crawl delay is too long for this bounded job.')
    import requests,hashlib,re
    responses={robots_url:robots_body};edges=[];captures=[];gaps=[];attempted=set();started=time.monotonic();last=0
    def guarded(session,method,url,**kwargs):
        nonlocal last
        response=requests.Response();response.status_code=200;response.headers['content-type']='text/html';response.url=url
        try:
            url=public_url(url)
            if method.upper()!='GET' or urlparse(url).hostname!=host or urlparse(url).query or re.search(r'(?i)(logout|login|signout|delete|subscribe|follow|checkout|cart)',urlparse(url).path):raise ValueError('Outside approved public information scope.')
            if url in responses:body=responses[url]
            else:
                if len(attempted)>=pages or time.monotonic()-started>60:raise ValueError('Page/runtime budget reached.')
                if not robots.can_fetch('Vidocq-PublicLinks',url):raise ValueError('Disallowed by robots.txt.')
                attempted.add(url);time.sleep(max(0,delay-(time.monotonic()-last)));last=time.monotonic();body=fetch(url);responses[url]=body
                stamp=now();digest=hashlib.sha256(body.encode()).hexdigest();captures.append({'reference':url,'retrieved_at':stamp,'sha256':digest})
                parser=Links(url);parser.feed(body)
                for target in parser.links:
                    edge={'source':url,'target':target,'observed_at':stamp,'relation':'published-link','source_sha256':digest}
                    if len(edges)<100 and len(json.dumps(edges))+len(json.dumps(edge))<55000:edges.append(edge)
            response._content=body.encode();response.encoding='utf-8'
        except Exception as e:
            gaps.append({'url':str(url)[:2000],'reason':str(e)[:200]});response.status_code=404;response._content=b''
        return response
    old=requests.sessions.Session.request;argv=sys.argv[:];path=sys.path[:]
    photon=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]/'.test-data/photon-source'))/'photon'
    if not photon.exists():photon=Path(__file__).resolve().parents[1]/'.test-data/photon-source'
    patches=[]
    try:
        requests.sessions.Session.request=guarded;sys.path.insert(0,str(photon))
        import core.utils,core.zap
        for module,name in [(core.utils,'writer'),(core.zap,'zap')]:patches.append((module,name,getattr(module,name)));setattr(module,name,lambda *a,**kw:None)
        # Retain only returned observations: no raw Photon exports/temp folders.
        sys.argv=[str(photon/'photon.py'),'-u',root,'--only-urls','-l',str(depth+1),'-t','1','-d','1','-o',os.getcwd()]
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            try:runpy.run_path(str(photon/'photon.py'),run_name='__main__')
            except (SystemExit,Exception):gaps.append({'url':root,'reason':'Photon stopped; any retained bounded observations are preserved.'})
    finally:
        for module,name,value in patches:setattr(module,name,value)
        requests.sessions.Session.request=old;sys.argv=argv;sys.path[:]=path
    return {'schema':'vidocq-links-v1','origin':'Photon bounded public capture','reference':root,'edges':edges,'pages':captures,'errors':[{'url':x['url'][:250],'reason':x['reason']} for x in gaps[:20]],'link_limit':100,'notice':'Bounded observations; large inventories/gap lists are limited. Actual page links use pinned public HTTPS transport; linkage is not ownership evidence.'}

if __name__=='__main__':
    from scripts.collector_http import serve
    def handle(path,p):
        if path!='/api/crawl':raise ValueError('Unsupported route.')
        return collect(p)
    serve('photon',handle)
