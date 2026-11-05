"""Explicit index-snippet links and supplied history; neither establishes ownership."""
import hashlib
from profile_registry import account_identity,url_tokens
from evidence_quality import source_quality,evidence_gate
from discovery_tools import now

def indexed_profile_links(case,record):
    source=account_identity(record.get('reference',''))
    if not source or not source_quality(record)['usable_for_ai'] or evidence_gate(record,case)['strength']<3:return []
    if record.get('analyst_status')=='Rejected':return []
    text=record.get('detail','');digest=hashlib.sha256(text.encode()).hexdigest();seen={source['reference']};edges=[]
    for url in url_tokens(text):
        target=account_identity(url)
        if not target or target['reference'] in seen:continue
        seen.add(target['reference']);edges.append({'source':record['reference'],'target':target['reference'],'relation':'indexed-snippet-link','citation':record['id'],'observed_at':record.get('retrieved_at') or now(),'source_sha256':digest,'ownership_verified':False,'notice':'Explicit URL in an index snippet from a supplied-identifier profile; not a verified live bio link.'})
        if len(edges)>=10:break
    return edges

def historical_edges(aliases):
    from social_profiles import profile_reference
    mapping={'instagram':'instagram','tiktok':'tiktok','vsco':'vsco'};edges=[]
    for alias in aliases:
        platform=mapping.get(alias.get('platform','').casefold())
        if not platform or not alias.get('successor'):continue
        try:source=account_identity(profile_reference(platform,alias['handle']))
        except ValueError:continue
        target=account_identity(alias['successor'])
        if not source or not target or source['platform']!=target['platform'] or source['reference']==target['reference']:continue
        edges.append({'source':source['reference'],'target':target['reference'],'relation':'supplied-historical-successor','observed_at':now(),'evidence_reference':alias.get('reference',''),'first_seen':alias.get('first_seen',''),'last_seen':alias.get('last_seen',''),'ownership_verified':False,'notice':'Dated analyst-supplied alias/successor assertion; current ownership and continuity require review.'})
    return edges
