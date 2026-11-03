"""Deterministic profile parsing and case-specific analyst decisions."""
import re
from urllib.parse import urlparse,urlunparse

PROFILE_HOSTS={'twitch.tv','github.com','gitlab.com','reddit.com','youtube.com','instagram.com','tiktok.com','vsco.co','steamcommunity.com','medium.com','pinterest.com'}

def profile_handle(value):
    try:p=urlparse(value if '://' in value else 'https://'+value)
    except ValueError:return None
    host=(p.hostname or '').removeprefix('www.');path=p.path.strip('/')
    try:port=p.port
    except ValueError:return None
    if p.scheme not in ('https','http') or p.username or p.password or port is not None:return None
    parts=path.split('/')
    if host=='twitch.tv' and len(parts)==1 and re.fullmatch('[A-Za-z0-9_]{1,25}',path) and path.lower() not in {'directory','downloads','settings','subscriptions','inventory','wallet','videos','search','jobs','turbo'}:return path.lower()
    if host in ('github.com','gitlab.com') and len(parts)==1 and re.fullmatch('[A-Za-z0-9_][A-Za-z0-9_-]{0,38}',path) and path.lower() not in {'explore','topics','settings','login','signup','features','about','pricing','search','marketplace','collections','orgs','groups','users'}:return path.lower()
    if host=='reddit.com' and len(parts)==2 and parts[0] in ('u','user') and re.fullmatch('[A-Za-z0-9_-]{3,20}',parts[1]):return parts[1]
    if host=='youtube.com' and len(parts)==1 and path.startswith('@') and re.fullmatch('[A-Za-z0-9_.-]{3,30}',path[1:]):return path[1:]
    return None

def canonical_reference(value):
    if not isinstance(value,str) or not value or len(value)>2000:raise ValueError('Enter a public source URL.')
    try:
        p=urlparse(value);host=(p.hostname or '').removeprefix('www.').lower()
        if p.scheme not in ('http','https') or not host or p.username or p.password or p.port is not None:raise ValueError()
    except ValueError:raise ValueError('Use a public HTTP(S) URL without credentials or an explicit port.') from None
    path=p.path.rstrip('/') or '/'
    if host in PROFILE_HOSTS:path=path.lower()
    if host not in PROFILE_HOSTS:host=(p.hostname or '').lower()
    return urlunparse(('https' if host in PROFILE_HOSTS else p.scheme,host,path,'',p.query if host not in PROFILE_HOSTS else '', ''))

def apply_decision(case,record):
    ref=record.get('reference')
    if not ref:return
    try:key=canonical_reference(ref)
    except ValueError:return
    decision=next((x for x in case.get('account_decisions',[]) if x.get('reference')==key),None)
    if decision:
        record['account_decision']=decision
        record['analyst_status']=decision['status']
        record['identity_status']='Rejected by analyst' if decision['status']=='Rejected' else 'Ownership confirmed by analyst; supplied assertion' if decision['status']=='Confirmed' else 'Unverified relevance'
        if decision['status']=='Rejected':record['relevance']['can_expand']=False

def locations(case):
    values=case.get('locations')
    if values is None:values=re.split('[;\n]',case.get('location',''))
    if not isinstance(values,list) or len(values)>5 or any(not isinstance(v,str) or len(v)>120 or any(ord(c)<32 for c in v) for v in values):raise ValueError('Use up to five locations, one per line or separated with semicolons.')
    return list(dict.fromkeys(v.strip() for v in values if v.strip()))

def rejected(case,reference):
    try:key=canonical_reference(reference)
    except ValueError:return False
    return any(d.get('reference')==key and d.get('status')=='Rejected' for d in case.get('account_decisions',[]))

def rejected_sites(case,username,sites):
    from collector_policy import MAIGRET_SITES
    excluded=[]
    for site in sites:
        for decision in case.get('account_decisions',[]):
            if decision.get('status')!='Rejected':continue
            p=urlparse(decision['reference']);parts=p.path.strip('/').split('/')
            if p.hostname in MAIGRET_SITES[site] and 1<=len(parts)<=2 and parts[-1].lstrip('@').casefold()==username.lstrip('@').casefold():
                excluded.append(site);break
    return excluded
