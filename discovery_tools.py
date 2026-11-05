"""Reviewed public-link imports, bounded fetching and deterministic query plans."""
from datetime import datetime, timezone
from html.parser import HTMLParser
import hashlib
import http.client
import ipaddress
import json
import re
import socket
import ssl
import time
from urllib.parse import urlparse, urljoin, urlunparse
from urllib.robotparser import RobotFileParser


def now(): return datetime.now(timezone.utc).isoformat()


def public_url(value):
    if not isinstance(value, str) or len(value)>2000: raise ValueError('Invalid public URL.')
    p=urlparse(value)
    if p.scheme!='https' or not p.hostname or p.username or p.password or p.port is not None or any(ord(c)<33 for c in value):
        raise ValueError('Use a public HTTPS URL without credentials or a port.')
    host=p.hostname.encode('idna').decode('ascii').lower()
    if '.' not in host or host.endswith(('.local','.localhost','.internal')): raise ValueError('Public hosts only.')
    try:address=ipaddress.ip_address(host)
    except ValueError:address=None
    if address is not None or re.fullmatch(r'[\d.:]+',host):raise ValueError('Use a public hostname, not an IP literal.')
    return urlunparse(('https',host,p.path or '/',p.params,p.query,''))


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self,host,address):
        super().__init__(host,timeout=8,context=ssl.create_default_context());self.address=address
    def connect(self):
        sock=socket.create_connection((self.address,443),timeout=self.timeout)
        self.sock=self._context.wrap_socket(sock,server_hostname=self.host)


def fetch_public(url):
    """Pin validated DNS answers; no cookies, proxy, redirects or authentication."""
    url=public_url(url);p=urlparse(url)
    addresses={x[4][0] for x in socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM)}
    if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses): raise ValueError('Destination resolved to a non-public address.')
    connection=PinnedHTTPS(p.hostname,sorted(addresses)[0])
    try:
        connection.request('GET',p.path+(';' + p.params if p.params else '')+('?' + p.query if p.query else ''),headers={'User-Agent':'Vidocq-PublicLinks/1.0','Accept':'text/html,text/plain'})
        r=connection.getresponse()
        if r.status!=200: raise ValueError('Source returned HTTP '+str(r.status)+'; redirects and access challenges are not followed.')
        if r.getheader('Content-Type','').split(';')[0] not in ('text/html','text/plain','application/xhtml+xml'): raise ValueError('Source is not public HTML/text.')
        raw=r.read(1_000_001)
        if len(raw)>1_000_000: raise ValueError('Page exceeds 1 MB.')
        return raw.decode('utf-8',errors='replace')
    finally: connection.close()


class Links(HTMLParser):
    def __init__(self,source): super().__init__();self.source=source;self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag!='a':return
        value=dict(attrs).get('href','')
        try: url=public_url(urljoin(self.source,value))
        except ValueError:return
        if url not in self.links and len(self.links)<200:self.links.append(url)


def crawl(payload,fetch=fetch_public,sleep=time.sleep):
    if payload.get('consent') is not True: raise ValueError('Explicitly approve direct public-site requests. Sites may log or alert on visits.')
    root=public_url(payload.get('url',''));p=urlparse(root)
    pages=payload.get('pages',1);depth=payload.get('depth',0)
    if type(pages) is not int or not 1<=pages<=5 or type(depth) is not int or not 0<=depth<=2: raise ValueError('Choose 1–5 pages and depth 0–2.')
    if p.query:raise ValueError('Start from a URL without query parameters.')
    if re.search(r'(?i)(logout|login|signout|delete|subscribe|follow|checkout|cart)',p.path):raise ValueError('Choose a public information page, not an account/action URL.')
    robots_url='https://'+p.netloc+'/robots.txt'
    try:
        robot=RobotFileParser();robot.parse(fetch(robots_url).splitlines())
    except Exception:raise ValueError('Could not verify robots.txt; direct fetch stopped. Use a reviewed browser capture instead.') from None
    delay=robot.crawl_delay('Vidocq-PublicLinks') or robot.crawl_delay('*') or 1
    if delay>10:raise ValueError('Site requires a longer crawl delay; use browser capture.')
    queue=[(root,0)];seen=set();edges=[];errors=[];captures=[];started=time.monotonic();truncated=False
    while queue and len(seen)<pages and time.monotonic()-started<60:
        url,level=queue.pop(0)
        if url in seen:continue
        seen.add(url)
        if not robot.can_fetch('Vidocq-PublicLinks',url):errors.append({'url':url,'reason':'Disallowed by robots.txt'});continue
        sleep(max(1,delay))
        try: body=fetch(url)
        except Exception as e:errors.append({'url':url,'reason':str(e)[:200]});continue
        parser=Links(url);parser.feed(body);stamp=now();digest=hashlib.sha256(body.encode()).hexdigest()
        captures.append({'reference':url,'retrieved_at':stamp,'sha256':digest})
        for target in parser.links:
            edge={'source':url,'target':target,'observed_at':stamp,'relation':'published-link','source_sha256':digest}
            if len(edges)>=100 or len(json.dumps(edges))+len(json.dumps(edge))>85000:truncated=True;continue
            edges.append(edge)
            t=urlparse(target)
            if level<depth and t.hostname==p.hostname and not t.query and not re.search(r'(?i)(logout|login|signout|delete|subscribe|follow|checkout|cart)',t.path) and target not in seen and len(queue)<200:queue.append((target,level+1))
    return {'schema':'vidocq-links-v1','origin':'direct-public-fetch','edges':edges,'pages':captures,'errors':errors,'scope':p.hostname,'remaining_pages':len(queue),'link_limit':100,'links_truncated':truncated}


def import_links(payload):
    data=payload.get('data');mode=payload.get('mode')
    if not isinstance(data,dict) or len(json.dumps(data))>150000:raise ValueError('Import must be a JSON object under 150 KB.')
    stamp=now();edges=[]
    if mode=='photon':
        # Photon JSON is aggregate sets, not per-page link evidence.
        root=public_url(payload.get('reference',''))
        for category in ('internal','external','intel','scripts','files','endpoints'):
            values=data.get(category,[])
            if not isinstance(values,list) or len(values)>1000:raise ValueError('Invalid Photon '+category+' dataset.')
            for value in values:
                if category=='intel' and isinstance(value,str) and re.search(r':[A-Z_]+:',value):continue
                try:target=public_url(value)
                except (ValueError,TypeError):continue
                edges.append({'source':root,'target':target,'observed_at':stamp,'relation':'photon-aggregate-lead','category':category})
    elif mode=='browser':
        if data.get('schema')!='vidocq-browser-v1':raise ValueError('Choose a Vidocq browser capture JSON.')
        root=public_url(data.get('reference',''))
        excerpt=data.get('excerpt','');title=data.get('title','')
        if not isinstance(excerpt,str) or not 0<len(excerpt)<=12000 or not isinstance(title,str) or not title.strip() or len(title)>500:raise ValueError('Invalid browser excerpt/title.')
        values=data.get('links',[])
        if not isinstance(values,list) or len(values)>200:raise ValueError('Too many captured links.')
        for value in values:
            try:target=public_url(value)
            except (ValueError,TypeError):continue
            edges.append({'source':root,'target':target,'observed_at':stamp,'relation':'browser-captured-link'})
        return {'schema':'vidocq-links-v1','origin':'user-browser-import','edges':edges,'reference':root,'title':title,'excerpt':excerpt,'captured_at':str(data.get('captured_at',''))[:100]}
    else:raise ValueError('Choose Photon or browser import.')
    if not edges:raise ValueError('No supported public URL leads in this Photon export.')
    if len(edges)>300:raise ValueError('Import at most 300 public URL leads at a time.')
    return {'schema':'vidocq-links-v1','origin':'photon-json-import','edges':edges,'reference':root,'notice':'Aggregate import: collection scope is not proof that the root page links to each target. Non-URL data is ignored.'}


def aliases(value):
    if not isinstance(value,list) or len(value)>30:raise ValueError('Use at most 30 historical aliases.')
    result=[]
    for item in value:
        if not isinstance(item,dict):raise ValueError('Invalid alias.')
        entry={k:str(item.get(k,'' )).strip() for k in ('handle','platform','first_seen','last_seen','reference','stable_id','successor')}
        if not re.fullmatch(r'@?[\w.-]{1,64}',entry['handle']) or len(entry['platform'])>40 or len(entry['stable_id'])>120:raise ValueError('Invalid alias handle/platform/ID.')
        for date in ('first_seen','last_seen'):
            if entry[date]:
                from datetime import date as date_type
                date_type.fromisoformat(entry[date])
        if entry['first_seen'] and entry['last_seen'] and entry['first_seen']>entry['last_seen']:raise ValueError('Alias dates are reversed.')
        for url in ('reference','successor'):
            if entry[url]:entry[url]=public_url(entry[url])
        entry['status']='historical-supplied-unverified';result.append(entry)
    return result


def query_plan(case):
    plan=[];seen=set()
    def add(terms,reason):
        key=tuple(x.casefold() for x in terms)
        if key not in seen and len(plan)<40:seen.add(key);plan.append({'terms':terms,'reason':reason})
    for name in case.get('names',[]):
        add([name],'supplied full name')
        parts=name.split()
        if len(parts)>2:add([parts[0]+' '+parts[-1]],'first and last name variant')
        for location in case.get('locations',[]):add([name,location],'supplied location variant')
        if case.get('employer'):add([name,case['employer']],'supplied employer context')
    for value in case.get('usernames',[]):add([value],'supplied username')
    for item in case.get('aliases',[]):
        add([item['handle']],'historical alias; current ownership unverified')
        if item.get('reference'):add([item['reference']],'supplied historical evidence reference')
        if item.get('successor'):add([item['successor']],'supplied successor reference; continuity unverified')
    for value in case.get('urls',[]):add([value],'exact supplied reference URL')
    return plan

def research_plan(case):
    """Only combine supplied identifiers; no invented names or ownership."""
    plan=query_plan(case);seen={tuple(x['terms']) for x in plan}
    def add(terms,reason):
        key=tuple(terms)
        if key not in seen and len(plan)<60:seen.add(key);plan.append({'terms':terms,'reason':reason})
    handles=list(dict.fromkeys(case.get('usernames',[])+case.get('instagram',[])+case.get('tiktok',[])))[:8]
    for name in case.get('names',[]):
        for handle in handles:add([name,handle],'name and supplied handle co-occurrence')
    for spelling in case.get('spelling_variants',[]):add([spelling],'analyst-approved name spelling variant')
    for handle in handles:
        for place in case.get('locations',[]):add([handle,place],'handle and supplied location co-occurrence')
    return plan
