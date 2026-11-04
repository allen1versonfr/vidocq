"""URL-level evidence types. Classification never establishes ownership."""
from urllib.parse import urlparse
from profile_registry import account_identity,parsed_public,canonical_reference,HOST_ALIASES,PROFILE_HOSTS,DISCOVERY_ROUTES,NAVIGATION


def source_quality(record):
    ref=record.get('reference','')
    try:
        parsed_public(ref)
        p=urlparse(ref);host=(p.hostname or '').lower().removeprefix('www.')
        host=HOST_ALIASES.get(host,host)
        parts=p.path.strip('/').split('/')
        if host in PROFILE_HOSTS and parts[0].lower() in DISCOVERY_ROUTES and parts[0].lower() in NAVIGATION.get(host,DISCOVERY_ROUTES):
            return {'kind':'discovery_page','account_candidate':False,'usable_for_ai':False,'reason':'Search/category page; name lists do not establish relationships.'}
        profile=bool(account_identity(ref))
        if profile:return {'kind':'profile','account_candidate':True,'usable_for_ai':True,'reason':'Profile-shaped URL; existence and ownership remain unverified.'}
        return {'kind':'context','account_candidate':False,'usable_for_ai':True,'reason':'Context source; not a recognized account profile URL.'}
    except (ValueError,TypeError,AttributeError):
        return {'kind':'unknown','account_candidate':False,'usable_for_ai':False,'reason':'Missing or invalid source URL.'}


def ranked_ai_records(records):
    eligible=[r for r in records if r.get('analyst_status')!='Rejected' and source_quality(r)['usable_for_ai']]
    def score(r):
        relevance=r.get('relevance',{})
        return (bool(r.get('observations',{}).get('profile')),bool(relevance.get('strong_anchor')),
                len(relevance.get('matched_identifiers',[])),source_quality(r)['account_candidate'])
    ordered=sorted(eligible,key=score,reverse=True);seen=set();result=[]
    for record in ordered:
        try:key=canonical_reference(record.get('reference',''))
        except ValueError:key=record.get('id')
        if key in seen:continue
        seen.add(key);result.append(record)
    return result
