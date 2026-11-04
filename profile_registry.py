"""Public profile identities, distinct from content URLs and ownership claims."""
import re
from urllib.parse import urlparse,urlunparse,parse_qsl,urlencode

HOST_ALIASES={'www.'+h:h for h in ('instagram.com','tiktok.com','vsco.co','twitch.tv','github.com','gitlab.com','reddit.com','youtube.com','steamcommunity.com','medium.com','pinterest.com','x.com','twitter.com','last.fm','wattpad.com')}
HOST_ALIASES.update({'twitter.com':'x.com','www.twitter.com':'x.com','m.instagram.com':'instagram.com','m.tiktok.com':'tiktok.com','m.youtube.com':'youtube.com','old.reddit.com':'reddit.com'})
PROFILE_HOSTS=set(HOST_ALIASES.values())|{'open.spotify.com'}
NAVIGATION={
 'instagram.com':{'p','reel','reels','stories','explore','accounts','direct','about','legal','developer','search','challenge','web'},
 'twitch.tv':{'directory','downloads','settings','subscriptions','inventory','wallet','videos','search','jobs','turbo'},
 'github.com':{'explore','topics','settings','login','signup','features','about','pricing','search','marketplace','collections','orgs','groups','users'},
 'gitlab.com':{'explore','topics','settings','login','signup','features','about','pricing','search','groups','users','-','help'},
 'pinterest.com':{'search','pin','ideas','business','login','settings','today','topics','explore','signup'},
 'x.com':{'home','explore','i','intent','search','settings','notifications','messages','compose','login','signup','hashtag'},
 'vsco.co':{'features','learn','search','about','membership','download','studio','spaces','gallery','sites','sign-in','login','sign-up','signup','account'},
 'tiktok.com':{'discover','tag','tags','search','explore','foryou','following','login'},
}
DISCOVERY_ROUTES={'discover','search','explore','tag','tags','topics','ideas','directory','login','signup','settings','accounts','direct'}

def parsed_public(value):
    if not isinstance(value,str) or not value or len(value)>2000 or any(ord(c)<33 for c in value):raise ValueError('Invalid public reference URL.')
    try:
        p=urlparse(value)
        if p.scheme not in ('http','https') or not p.hostname or p.username or p.password or p.port is not None:raise ValueError()
    except ValueError:raise ValueError('Use a public HTTP(S) URL without credentials or an explicit port.') from None
    return p

def account_identity(value):
    try:p=parsed_public(value)
    except ValueError:return None
    host=HOST_ALIASES.get(p.hostname,p.hostname);parts=p.path.strip('/').split('/');handle=None;prefix='';platform=host;case_sensitive=False
    if host in ('instagram.com','twitch.tv','github.com','gitlab.com','pinterest.com','x.com'):
        pattern=r'[A-Za-z0-9_][A-Za-z0-9_.]{0,29}' if host=='instagram.com' else r'[A-Za-z0-9_]{1,25}' if host=='twitch.tv' else r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}'
        if len(parts)==1 and re.fullmatch(pattern,parts[0]) and parts[0].lower() not in NAVIGATION.get(host,set()) and not parts[0].endswith('.') and '..' not in parts[0]:handle=parts[0]
    elif host=='tiktok.com':
        if len(parts)==1 and re.fullmatch(r'@[A-Za-z0-9_][A-Za-z0-9_.]{0,29}',parts[0]) and not parts[0].endswith('.') and '..' not in parts[0]:handle=parts[0][1:];prefix='@'
    elif host=='vsco.co':
        if len(parts)==2 and parts[-1]=='gallery':parts=parts[:1]
        if len(parts)==1 and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{2,63}',parts[0]) and parts[0].lower() not in NAVIGATION[host]:handle=parts[0]
    elif host=='reddit.com':
        if len(parts)==2 and parts[0] in ('u','user') and re.fullmatch(r'[A-Za-z0-9_-]{3,20}',parts[1]):handle=parts[1];prefix='user/'
    elif host=='youtube.com':
        if len(parts)==1 and re.fullmatch(r'@[A-Za-z0-9_.-]{3,30}',parts[0]):handle=parts[0][1:];prefix='@'
        elif len(parts)==2 and parts[0]=='channel' and re.fullmatch(r'UC[A-Za-z0-9_-]{22}',parts[1]):handle=parts[1];prefix='channel/';case_sensitive=True
    elif host=='steamcommunity.com':
        if len(parts)==2 and parts[0] in ('id','profiles') and re.fullmatch(r'[A-Za-z0-9_-]{2,64}',parts[1]):handle=parts[1];prefix=parts[0]+'/'
    elif host=='medium.com':
        if len(parts)==1 and re.fullmatch(r'@[A-Za-z0-9_.-]{1,64}',parts[0]):handle=parts[0][1:];prefix='@'
    elif host in ('last.fm','wattpad.com'):
        if len(parts)==2 and parts[0]=='user' and re.fullmatch(r'[A-Za-z0-9_.-]{1,64}',parts[1]):handle=parts[1];prefix='user/'
    elif host=='open.spotify.com':
        if len(parts)==2 and parts[0]=='user' and re.fullmatch(r'[A-Za-z0-9_-]{1,64}',parts[1]):handle=parts[1];prefix='user/';case_sensitive=True
    if handle is None:return None
    if not case_sensitive:handle=handle.lower()
    return {'platform':platform,'handle':handle,'reference':'https://'+host+'/'+prefix+handle,'lookup_kind':{'instagram.com':'instagram','tiktok.com':'tiktok','vsco.co':'vsco','steamcommunity.com':'steam'}.get(host,'username'),'ownership_verified':False}

def canonical_reference(value):
    p=parsed_public(value);identity=account_identity(value)
    if identity:return identity['reference']
    # Preserve content parameters and opaque identifiers. Only known trackers go.
    query=urlencode([(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid','igshid')])
    return urlunparse((p.scheme,p.hostname,p.path or '/',p.params,query,''))

def url_tokens(text):
    result=[]
    for raw in re.findall(r'https?://[^\s<>"\]\[{}\\]+',str(text)):
        raw=raw.rstrip('.,;:)')
        try:parsed_public(raw)
        except ValueError:continue
        if raw not in result:result.append(raw)
    return result[:100]

def same_reference(a,b):
    try:return canonical_reference(a)==canonical_reference(b)
    except ValueError:return False
