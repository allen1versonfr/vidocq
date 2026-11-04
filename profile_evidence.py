"""Cited public profile observations; links and stable IDs never confirm ownership."""
import hashlib,json,re
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from discovery_tools import public_url,fetch_public,Links,now

def profile_reference(value):
    ref=public_url(value);parsed=urlparse(ref)
    if not parsed.path.strip('/') or re.search(r'(?i)/(login|logout|accounts|settings|stories|follow|subscribe|delete)(/|$)',parsed.path):raise ValueError('Supply a public profile URL, not a platform root/account action.')
    return ref

def reviewed_profile(p):
    if p.get('consent') is not True or p.get('public_reviewed') is not True:raise ValueError('Confirm you reviewed this publicly visible profile evidence.')
    ref=profile_reference(p.get('reference',''));parsed=urlparse(ref)
    bio=p.get('biography','');name=p.get('display_name','');stable=p.get('stable_id','');handle=p.get('handle','')
    if not isinstance(bio,str) or not 1<=len(bio)<=6000 or not isinstance(name,str) or len(name)>200:raise ValueError('Enter reviewed public bio text (up to 6,000 characters) and a short display name.')
    if any(not isinstance(x,str) for x in (stable,handle)) or not re.fullmatch(r'[A-Za-z0-9_.:-]{0,128}',stable) or not re.fullmatch(r'[A-Za-z0-9_.-]{0,64}',handle):raise ValueError('Invalid supplied public handle/stable ID.')
    urls=p.get('links',[])
    if not isinstance(urls,list) or len(urls)>50:raise ValueError('Use up to 50 explicit public links.')
    urls=urls+re.findall(r'https://[^\s<>"\x27]+',bio);stamp=now();digest=hashlib.sha256(bio.encode()).hexdigest();edges=[];seen={ref}
    for url in urls:
        try:url=public_url(url)
        except (ValueError,TypeError):continue
        if url in seen:continue
        seen.add(url);edges.append({'source':ref,'target':url,'relation':'browser-captured-link','observed_at':stamp,'source_sha256':digest})
    return {'schema':'vidocq-links-v1','origin':'reviewed-public-profile','reference':ref,'title':'Reviewed public profile'+(' · '+name if name else ''),'excerpt':bio,'profile':{'platform':parsed.hostname.removeprefix('www.'),'handle':handle,'display_name':name,'stable_id':stable,'biography':bio,'links':[e['target'] for e in edges[:50]],'observed_at':stamp},'edges':edges[:50],'notice':'Analyst-reviewed public observations. Stable IDs apply only within the named platform; ownership remains unverified.'}

class Metadata(HTMLParser):
    def __init__(self):super().__init__();self.bio='';self.title='';self.in_title=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='title':self.in_title=True
        if tag=='meta' and (a.get('property') or a.get('name')) in ('description','og:description') and not self.bio:self.bio=a.get('content','')[:6000]
    def handle_endtag(self,tag):
        if tag=='title':self.in_title=False
    def handle_data(self,value):
        if self.in_title:self.title=(self.title+value)[:200]

def capture_profile(p,fetch=fetch_public):
    if p.get('consent') is not True:raise ValueError('Approve this direct public profile request. Visits may be logged.')
    ref=profile_reference(p.get('reference',''))
    if urlparse(ref).query:raise ValueError('Direct profile capture requires a query-free URL.')
    host=urlparse(ref).netloc;robots=RobotFileParser();robots.parse(fetch('https://'+host+'/robots.txt').splitlines())
    if not robots.can_fetch('Vidocq-PublicProfile',ref):raise ValueError('Profile capture disallowed by robots.txt. Use reviewed browser evidence.')
    delay=robots.crawl_delay('Vidocq-PublicProfile') or robots.crawl_delay('*') or 0
    if delay>10:raise ValueError('Use browser review for this site’s crawl-delay requirement.')
    if delay:
        import time
        time.sleep(delay)
    body=fetch(ref);metadata=Metadata();metadata.feed(body)
    if not metadata.bio or re.search(r'(?i)(log\s?in|sign\s?in|challenge|captcha)',metadata.title):raise ValueError('No reliable public profile metadata captured. Review it in your browser; no bypass was attempted.')
    parser=Links(ref);parser.feed(body)
    capture=reviewed_profile({'consent':True,'public_reviewed':True,'reference':ref,'biography':metadata.bio,'display_name':metadata.title,'links':list(parser.links)[:50]})
    capture['origin']='direct-public-profile';capture['source_sha256']=hashlib.sha256(body.encode()).hexdigest()
    capture['profile']['links']=[]
    for edge in capture['edges']:edge['relation']='published-link';edge['source_sha256']=capture['source_sha256']
    capture['notice']='One approved public page, parsed metadata and links; no login, redirects or challenge bypass. Account ownership remains unverified.'
    return capture

def profile_graph(records):
    nodes={};edges=[];ids={}
    for record in records:
        if record.get('analyst_status')=='Rejected':continue
        profile=record.get('observations',{}).get('profile')
        if not isinstance(profile,dict):continue
        try:ref=public_url(record.get('reference',''))
        except (ValueError,TypeError):continue
        host=urlparse(ref).hostname.removeprefix('www.');stable=profile.get('stable_id','')
        if not isinstance(stable,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{0,128}',stable):stable=''
        node=nodes.setdefault(ref,{'reference':ref,'platform':host,'stable_id':stable,'citations':[],'display_name':str(profile.get('display_name',''))[:200],'ownership_verified':False})
        node['citations'].append(record['id'])
        if stable:ids.setdefault((host,stable),[]).append((ref,record['id']))
        bio=str(profile.get('biography',''))[:6000]
        links=profile.get('links',[]);links=links[:50] if isinstance(links,list) else []
        for raw in re.findall(r'https://[^\s<>"\x27]+',bio)+links:
            try:target=public_url(raw)
            except (ValueError,TypeError):continue
            if target!=ref:edges.append({'source':ref,'target':target,'relation':'public-bio-link','citations':[record['id']],'ownership_verified':False})
    for key,values in ids.items():
        unique=list(dict.fromkeys(values))
        for left,right in zip(unique,unique[1:]):
            if left[0]!=right[0]:edges.append({'source':left[0],'target':right[0],'relation':'same-platform-id-observed','citations':[left[1],right[1]],'platform':key[0],'stable_id':key[1],'ownership_verified':False})
    return {'nodes':list(nodes.values()),'edges':edges[:100],'notice':'Published links and matching platform-scoped IDs are evidence to review, never automatic ownership confirmation.'}
