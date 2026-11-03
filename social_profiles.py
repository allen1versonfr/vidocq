"""Social identifiers and index queries. Never resolves or fetches profile URLs."""
import re
from urllib.parse import urlparse
PLATFORMS={'instagram':{'name':'Instagram','host':'instagram.com'},'tiktok':{'name':'TikTok','host':'tiktok.com'},'vsco':{'name':'VSCO','host':'vsco.co'}}

def detect_platform(value):
    try:
        p=urlparse(value if '://' in value else 'https://'+value)
        if not p.path or p.path=='/':return None
        return next((key for key,item in PLATFORMS.items() if p.hostname in (item['host'],'www.'+item['host'])),None)
    except ValueError:return None

def normalize_profile(platform,value):
    if platform not in PLATFORMS:raise ValueError('Choose Instagram, TikTok or VSCO.')
    if not isinstance(value,str) or not value.strip() or len(value)>2000 or any(ord(c)<32 for c in value):raise ValueError('Enter a social handle or full profile URL.')
    value=value.strip();item=PLATFORMS[platform]
    if '://' in value or '/' in value:
        try:p=urlparse(value if '://' in value else 'https://'+value)
        except ValueError:raise ValueError('Invalid social profile URL.') from None
        if p.scheme not in ('http','https') or p.hostname not in (item['host'],'www.'+item['host']) or p.username or p.password or p.port is not None:raise ValueError('Use a full '+item['name']+' profile URL on '+item['host']+'.')
        path=p.path.strip('/')
        if platform=='vsco' and path.endswith('/gallery'):path=path[:-8]
        if '/' in path or (platform=='tiktok' and not path.startswith('@')):raise ValueError('Use a profile URL, not a post, video or share link.')
        value=path
    handle=value.removeprefix('@').lower()
    pattern=r'[a-z0-9-]{3,64}' if platform=='vsco' else r'[a-z0-9_\.]{1,30}'
    if platform=='vsco' and not re.fullmatch(pattern,handle):raise ValueError('VSCO profile handles need at least 3 letters, numbers or dashes (maximum 64 in Vidocq).')
    if not re.fullmatch(pattern,handle) or handle.endswith('.') or '..' in handle or (platform=='instagram' and handle.startswith('.')):raise ValueError('Use a handle, not a display name: letters, numbers, underscores or periods (hyphens also supported for VSCO).')
    if platform=='instagram' and handle in {'p','reel','reels','stories','explore','accounts','direct','about','legal','developer'}:raise ValueError('Use an Instagram profile handle, not a navigation or post URL.')
    if platform=='vsco' and handle in {'features','learn','search','about','membership','download','studio','spaces','gallery','sites','sign-in','login','sign-up','signup','account'}:raise ValueError('Use a VSCO profile handle, not a navigation or gallery share URL.')
    return handle

def profile_reference(platform,handle):
    handle=normalize_profile(platform,handle)
    return ('https://' if platform=='vsco' else 'https://www.')+PLATFORMS[platform]['host']+'/'+('@' if platform=='tiktok' else '')+handle+'/'
