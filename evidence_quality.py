"""URL-level evidence types. Classification never establishes ownership."""
from urllib.parse import urlparse
from discovery_review import profile_handle
from social_profiles import detect_platform, normalize_profile


def source_quality(record):
    ref=record.get('reference','')
    try:
        p=urlparse(ref);host=(p.hostname or '').lower().removeprefix('www.')
        parts=p.path.strip('/').split('/')
        if host in ('tiktok.com','instagram.com') and parts[0].lower() in ('discover','tag','tags','explore','search'):
            return {'kind':'discovery_page','account_candidate':False,'usable_for_ai':False,'reason':'Search/category page; name lists do not establish relationships.'}
        platform=detect_platform(ref)
        profile=False
        if platform:
            try:normalize_profile(platform,ref);profile=True
            except ValueError:pass
        profile=profile or bool(profile_handle(ref))
        if host=='steamcommunity.com' and len(parts)==2 and parts[0] in ('id','profiles') and parts[1]:profile=True
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
    return sorted(eligible,key=score,reverse=True)
