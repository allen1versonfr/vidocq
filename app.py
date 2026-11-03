"""Vidocq Desktop. Local UI; allowlisted third-party indexes only."""
import argparse
import concurrent.futures
from contextlib import closing
import html
import ipaddress
import json
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone
from version import VERSION
from updater import UpdateManager
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, HTTPRedirectHandler, build_opener

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
DATA = Path(os.environ.get('VIDOCQ_DATA') or os.environ.get('ALL_SEEING_EYES_DATA') or os.environ.get('OSINT_DESK_DATA') or (Path(os.environ.get('LOCALAPPDATA', Path.home()/'.local/share')) / 'Vidocq'))
EXIT_EVENT = threading.Event()
UPDATES = UpdateManager(DATA)
NETWORK_HOSTS = frozenset({'archive.org', 'crt.sh', 'en.wikipedia.org', 'rdap.arin.net', 'rdap.db.ripe.net', 'rdap.apnic.net', 'rdap.lacnic.net', 'rdap.afrinic.net', 'openlibrary.org'})
LINK_HOSTS = NETWORK_HOSTS | {'www.google.com', 'www.bing.com', 'lookup.icann.org', 'stat.ripe.net', 'duckduckgo.com', 'scholar.google.com', 'pubmed.ncbi.nlm.nih.gov', 'patents.google.com'}
COOKIE = secrets.token_urlsafe(32)
HEADERS = {'User-Agent': 'Vidocq/2.4.0 (public-index research; local desktop app)', 'Accept': 'application/json'}


def check_provider_url(url, hosts=NETWORK_HOSTS):
    p = urlparse(url)
    if p.scheme != 'https' or p.hostname not in hosts or p.username or p.password or p.port not in (None,443):
        raise ValueError('Destination is outside the reviewed provider allowlist.')
    return url


class ProviderRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_provider_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def get_json(url):
    check_provider_url(url)
    with build_opener(ProviderRedirect).open(Request(url, headers=HEADERS), timeout=12) as response:
        raw = response.read(2_000_001)
        if len(raw)>2_000_000:
            raise ValueError('Provider response exceeded the 2 MB limit. Narrow the query.')
        return json.loads(raw)


def normalize(kind, value):
    if not isinstance(value,str) or not value.strip() or len(value)>240:
        raise ValueError('Enter between 1 and 240 characters.')
    value=value.strip()
    if any(ord(c)<32 for c in value):
        raise ValueError('Control characters are not allowed.')
    if kind=='auto':
        try:
            ipaddress.ip_address(value)
            kind='ip'
        except ValueError:
            kind='email' if '@' in value and ' ' not in value else ('domain' if '.' in value and ' ' not in value else 'username')
    if kind=='domain':
        value=value.removeprefix('https://').removeprefix('http://').rstrip('/')
        try:
            value=value.encode('idna').decode('ascii').lower()
        except UnicodeError:
            raise ValueError('Enter a valid domain.')
        if len(value)>253 or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}',value):
            raise ValueError('Use a domain such as example.com, without a path or port.')
    elif kind=='ip':
        try:
            address=ipaddress.ip_address(value)
            if not address.is_global:
                raise ValueError()
            value=str(address)
        except ValueError:
            raise ValueError('Enter a public IPv4 or IPv6 address.')
    elif kind=='email':
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value):
            raise ValueError('Enter a valid email address.')
    elif kind not in ('username','topic'):
        raise ValueError('Unsupported input type.')
    return kind,value


def link(title, url, note):
    check_provider_url(url, LINK_HOSTS)
    return {'title':title,'url':url,'note':note}


def prepared_links(kind,value):
    exact='"'+value.replace('"','')+'"'
    links=[link('Google indexed mentions','https://www.google.com/search?'+urlencode({'q':exact}),'Search results only. Opening an original result can contact that website.'),link('Bing indexed mentions','https://www.bing.com/search?'+urlencode({'q':exact}),'Search this independent index; the provider receives the query.')]
    if kind=='username':
        for site,name in [('github.com','GitHub'),('reddit.com','Reddit'),('instagram.com','Instagram'),('tiktok.com','TikTok')]:
            links.append(link(name+' indexed mentions','https://www.google.com/search?'+urlencode({'q':f'site:{site} {exact}'}),'Search-engine index only; no account existence or login checks.'))
    elif kind=='domain':
        links.extend([link('Certificate Transparency index','https://crt.sh/?'+urlencode({'q':value}),'Existing certificate records, no live domain scan.'),link('ICANN registration lookup','https://lookup.icann.org/en/lookup?'+urlencode({'name':value}),'Third-party registration records; data may be redacted.'),link('Indexed pages','https://www.google.com/search?'+urlencode({'q':'site:'+value}),'Search index only; original pages are not retrieved by this app.')])
    elif kind=='ip':
        links.append(link('RIPE public network records','https://stat.ripe.net/'+quote(value,safe=''),'Registry information; no scan of this address.'))
    elif kind=='topic':
        links.append(link('Wikipedia search','https://en.wikipedia.org/w/index.php?'+urlencode({'search':value}),'Public encyclopedia index.'))
    links.append(link('DuckDuckGo indexed mentions','https://duckduckgo.com/?'+urlencode({'q':exact}),'Independent search index; opens only after a click.'))
    if kind=='topic':
        for title,base,key in [('Google Scholar','https://scholar.google.com/scholar','q'),('PubMed','https://pubmed.ncbi.nlm.nih.gov/','term'),('Open Library','https://openlibrary.org/search','q'),('Google Patents','https://patents.google.com/','q')]:
            links.append(link(title,base+'?'+urlencode({key:value}),'Search this public index in your browser; no original source is opened by Vidocq.'))
    return links


def archive(value):
    url='https://archive.org/wayback/available?'+urlencode({'url':'https://'+value})
    data=get_json(url)
    snap=data.get('archived_snapshots',{}).get('closest')
    # Display metadata only. Replaying archived pages can load resources; no replay link.
    rows=[] if not snap else [{'title':'Archived snapshot metadata','detail':f"Capture: {snap.get('timestamp','unknown')} · HTTP status: {snap.get('status','unknown')} · Available: {snap.get('available',False)}"}]
    return url,rows


def certificates(value):
    url='https://crt.sh/?'+urlencode({'q':value,'output':'json'})
    data=get_json(url)
    if not isinstance(data,list):
        raise ValueError('Unexpected certificate index response.')
    rows=[]
    seen=set()
    for row in data:
        for name in str(row.get('name_value','')).splitlines():
            if name in seen:continue
            seen.add(name)
            rows.append({'title':name,'detail':f"Issuer: {row.get('issuer_name','Unknown')} · Valid from: {row.get('not_before','Unknown')}"})
            if len(rows)>=100:return url,rows
    return url,rows


def encyclopedia(value):
    url='https://en.wikipedia.org/w/rest.php/v1/search/page?'+urlencode({'q':value,'limit':8})
    data=get_json(url)
    return url,[{'title':p.get('title','Untitled'),'detail':html.unescape(re.sub('<[^>]+>','',p.get('description') or p.get('excerpt') or 'No description.'))} for p in data.get('pages',[])]


def books(value):
    url='https://openlibrary.org/search.json?'+urlencode({'q':value,'limit':8,'fields':'title,author_name,first_publish_year,key'})
    data=get_json(url)
    if not isinstance(data,dict) or not isinstance(data.get('docs'),list):raise ValueError('Unexpected Open Library response.')
    rows=[]
    for item in data['docs'][:8]:
        if not isinstance(item,dict):continue
        authors=item.get('author_name') or []
        rows.append({'title':str(item.get('title') or 'Untitled')[:500], 'detail':'Authors: '+', '.join(map(str,authors[:5]))+' · First published: '+str(item.get('first_publish_year') or 'Unknown')})
    return url,rows


def network_registry(value):
    url='https://rdap.arin.net/registry/ip/'+quote(value,safe=':')
    d=get_json(url)
    rows=[{'title':d.get('name') or d.get('handle') or 'Network allocation','detail':f"Range: {d.get('startAddress','?')} – {d.get('endAddress','?')} · Country: {d.get('country','not listed')} · Registry status: {', '.join(d.get('status',[])) or 'not listed'}"}]
    return url,rows


ADAPTERS={'domain':[('Internet Archive index',archive),('Certificate Transparency index',certificates)],'ip':[('Regional Internet Registry',network_registry)],'topic':[('Wikipedia index',encyclopedia),('Open Library catalog',books)]}


def run_adapter(name,fn,value):
    started=time.monotonic()
    try:
        url,rows=fn(value)
        return {'provider':name,'status':'ok' if rows else 'empty','rows':rows,'source':url,'elapsed':round(time.monotonic()-started,1)}
    except Exception as error:
        message='Provider unavailable or request timed out.'
        if isinstance(error,HTTPError):message=f'Provider returned HTTP {error.code}. It may be rate-limited or require access.'
        elif isinstance(error,ValueError):message=str(error)
        return {'provider':name,'status':'error','rows':[],'message':message,'elapsed':round(time.monotonic()-started,1)}


def research(kind,value):
    kind,value=normalize(kind,value)
    adapters=ADAPTERS.get(kind,[])
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda pair:run_adapter(pair[0],pair[1],value),adapters))
    return {'kind':kind,'query':value,'searched_at':datetime.now(timezone.utc).isoformat(),'results':results,'links':prepared_links(kind,value),'mode':'Third-party indexes only','notice':'No target-owned website, profile, DNS server, or IP is queried directly. Providers may log requests. There is no guarantee of anonymity or absence of notification.'}


class NotebookConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def db():
    DATA.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DATA/'workspace.sqlite3',timeout=5,factory=NotebookConnection)
    c.execute('CREATE TABLE IF NOT EXISTS findings (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
    return c


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass  # Do not persist queries in server logs.

    def authorized(self):
        host=self.headers.get('Host','')
        if host!=f'127.0.0.1:{self.server.server_port}':return False
        origin=self.headers.get('Origin')
        if origin and origin!=f'http://{host}':return False
        if self.command=='POST' and self.headers.get('Content-Type')!='application/json':return False
        cookies=SimpleCookie()
        try:cookies.load(self.headers.get('Cookie',''))
        except Exception:return False
        return cookies.get('desk') is not None and secrets.compare_digest(cookies['desk'].value,COOKIE)

    def send(self,code,data,mime='application/json',cookie=False):
        raw=json.dumps(data).encode() if mime=='application/json' else data
        self.send_response(code)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; connect-src 'self'; img-src 'self' blob:; style-src 'self'; script-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if cookie:self.send_header('Set-Cookie',f'desk={COOKIE}; HttpOnly; SameSite=Strict; Path=/')
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        host=f'127.0.0.1:{self.server.server_port}'
        if self.headers.get('Host')!=host:return self.send(403,{'error':'Localhost only.'})
        if self.path=='/':return self.send(200,(ROOT/'ui/index.html').read_bytes(),'text/html; charset=utf-8',cookie=True)
        if not self.authorized():return self.send(403,{'error':'Open the local app window first.'})
        if urlparse(self.path).path=='/api/catalog':
            from catalog import query_catalog
            try:return self.send(200,query_catalog({k:v[0] for k,v in parse_qs(urlparse(self.path).query).items()}))
            except ValueError as e:return self.send(400,{'error':str(e)})
        if self.path=='/api/updates':return self.send(200,UPDATES.status())
        if self.path=='/api/findings':
            with db() as c:rows=c.execute('SELECT data FROM findings ORDER BY rowid DESC').fetchall()
            return self.send(200,[json.loads(row[0]) for row in rows])
        if self.path in ('/app.js','/style.css'):
            mime='application/javascript; charset=utf-8' if self.path.endswith('.js') else 'text/css; charset=utf-8'
            return self.send(200,(ROOT/'ui'/self.path[1:]).read_bytes(),mime)
        self.send(404,{'error':'Not found.'})

    def do_POST(self):
        if not self.authorized():return self.send(403,{'error':'Invalid local session or origin.'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<1 or size>(7_100_000 if self.path=='/api/image-search' else 200_000):raise ValueError('Invalid request size.')
            p=json.loads(self.rfile.read(size))
            if not isinstance(p,dict):raise ValueError('Invalid request.')
            if self.path=='/api/catalog/search':
                from catalog import indexed_source_url
                url=indexed_source_url(p.get('id'),p.get('query'))
                webbrowser.open(url)
                return self.send(200,{'opened':True,'mode':'search-index-only'})
            if self.path=='/api/quit':
                self.send(200,{'closing':True})
                EXIT_EVENT.set()
                window=getattr(self.server,'native_window',None)
                if window:window.destroy()
                return
            if self.path=='/api/updates/check':
                UPDATES.check(p.get('token'))
                return self.send(202,UPDATES.status())
            if self.path=='/api/updates/download':
                UPDATES.download()
                return self.send(202,UPDATES.status())
            if self.path=='/api/updates/install':
                UPDATES.install()
                self.send(202,UPDATES.status())
                threading.Timer(1.5,lambda: os._exit(0)).start()
                return
            if self.path=='/api/image-search':
                from image_search import search_image
                return self.send(200,search_image(p))
            if self.path=='/api/research':return self.send(200,research(p.get('kind','auto'),p.get('value','')))
            if self.path=='/api/save':
                if not isinstance(p.get('title'),str) or not p['title'].strip():raise ValueError('A title is required.')
                item={'id':secrets.token_hex(12),'title':p['title'][:500],'notes':str(p.get('notes',''))[:10000],'source':str(p.get('source',''))[:2000],'status':p.get('status') if p.get('status') in ('Unverified lead','Corroborated','Rejected') else 'Unverified lead','date':datetime.now(timezone.utc).isoformat()}
                with db() as c:c.execute('INSERT INTO findings VALUES (?,?)',(item['id'],json.dumps(item)))
                return self.send(200,item)
            if self.path=='/api/open':
                url=check_provider_url(str(p.get('url','')),LINK_HOSTS)
                # Only pre-reviewed search/index URL patterns, never arbitrary target links.
                parsed=urlparse(url)
                if not allowed_external(url):raise ValueError('Only index search links can be opened.')
                webbrowser.open(url)
                return self.send(200,{'opened':True})
            self.send(404,{'error':'Unknown operation.'})
        except (ValueError,TypeError,json.JSONDecodeError) as e:self.send(400,{'error':str(e)})
        except Exception:self.send(500,{'error':'The request could not complete. Your saved findings are unchanged.'})


def allowed_external(url):
    try:check_provider_url(url,LINK_HOSTS)
    except ValueError:return False
    p=urlparse(url)
    return ((p.hostname in ('www.google.com','www.bing.com') and p.path=='/search') or (p.hostname=='crt.sh' and p.path=='/') or (p.hostname=='lookup.icann.org' and p.path=='/en/lookup') or (p.hostname=='stat.ripe.net' and p.path.count('/')==1) or (p.hostname=='en.wikipedia.org' and p.path=='/w/index.php') or (p.hostname=='duckduckgo.com' and p.path=='/') or (p.hostname=='scholar.google.com' and p.path=='/scholar') or (p.hostname=='pubmed.ncbi.nlm.nih.gov' and p.path=='/') or (p.hostname=='openlibrary.org' and p.path=='/search') or (p.hostname=='patents.google.com' and p.path=='/'))


def migrate_legacy_data(destination=None, base=None):
    """Copy an earlier notebook once; never remove or overwrite user data."""
    destination=Path(destination) if destination is not None else DATA
    base=Path(base) if base is not None else Path(os.environ.get('LOCALAPPDATA',Path.home()/'.local/share'))
    if (destination/'workspace.sqlite3').exists():return
    # Historical folder names exist only for backward compatibility.
    for old_name in ('AllSeeingEyes','OSINTDesk'):
        legacy=base/old_name/'workspace.sqlite3'
        if legacy.exists():
            destination.mkdir(parents=True,exist_ok=True)
            with closing(sqlite3.connect(legacy)) as old, closing(sqlite3.connect(destination/'workspace.sqlite3')) as new:old.backup(new)
            return


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--update-ready',type=Path)
    parser.add_argument('--smoke-test',type=Path,help='Validate frozen imports, UI and database; write result and exit')
    parser.add_argument('--self-test',action='store_true',help='Validate packaged imports and local database, then exit')
    parser.add_argument('--browser',action='store_true',help='Open in default browser instead of native window')
    parser.add_argument('--serve-only',action='store_true',help='Start local server for diagnostics')
    parser.add_argument('--port',type=int,default=0)
    args=parser.parse_args()
    migrate_legacy_data()
    if args.self_test or args.smoke_test:
        import image_search
        from PIL import Image
        with db() as connection:connection.execute('SELECT count(*) FROM findings').fetchone()
        import updater, webview
        from catalog import catalog
        assert catalog()['summary']['entries'] == len(catalog()['entries'])
        assert (ROOT/'ui/index.html').is_file() and (ROOT/'ui/app.js').is_file()
        if args.smoke_test:args.smoke_test.write_text(json.dumps({'version':VERSION,'ok':True}),encoding='utf-8')
        if args.update_ready:args.update_ready.write_text(VERSION,encoding='utf-8')
        print('Vidocq self-test passed.',flush=True)
        return
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    server.daemon_threads=True
    url=f'http://127.0.0.1:{server.server_port}'
    print('Vidocq is running at '+url,flush=True)
    print('Close the app window or press Ctrl+C here to stop.',flush=True)
    if args.serve_only:
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:server.server_close()
        return
    threading.Thread(target=server.serve_forever,daemon=True).start()
    UPDATES.check()
    def mark_ready():
        if args.update_ready:args.update_ready.write_text(VERSION,encoding='utf-8')
    try:
        if not args.browser:
            try:import webview
            except ImportError:
                print('Native window component is not installed. Opening browser mode.')
                args.browser=True
        if args.browser:
            webbrowser.open(url)
            mark_ready()
            EXIT_EVENT.wait()
        else:
            webview.settings['ALLOW_DOWNLOADS'] = True
            server.native_window=webview.create_window('Vidocq',url,width=1140,height=800,min_size=(680,580))
            server.native_window.events.loaded += mark_ready
            try:
                webview.start(gui='edgechromium' if os.name=='nt' else None)
            except Exception as error:
                print('Native window could not start: '+str(error))
                print('Opening browser mode. Install Microsoft WebView2 Runtime for the native window.')
                webbrowser.open(url)
                mark_ready()
                EXIT_EVENT.wait()
    except KeyboardInterrupt:pass
    finally:server.shutdown();server.server_close()


if __name__=='__main__':main()
