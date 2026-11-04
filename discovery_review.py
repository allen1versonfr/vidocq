"""Deterministic profile parsing and case-specific analyst decisions."""
import re
from urllib.parse import urlparse
from profile_registry import account_identity,canonical_reference,PROFILE_HOSTS


def profile_handle(value):
    if not isinstance(value,str):return None
    identity=account_identity(value if '://' in value else 'https://'+value)
    return identity['handle'] if identity and identity['lookup_kind']=='username' else None

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
