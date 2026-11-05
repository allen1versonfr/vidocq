"""URL-level evidence types. Classification never establishes ownership."""
from urllib.parse import urlparse
from profile_registry import account_identity,parsed_public,canonical_reference,HOST_ALIASES,PROFILE_HOSTS,DISCOVERY_ROUTES,NAVIGATION
import re,unicodedata

DIRECTORY_HOSTS={'whitepages.com','veripages.com','officialusa.com','searchpeoplefree.com','idcrawl.com','fastpeoplesearch.com','truepeoplesearch.com','spokeo.com','beenverified.com'}
LISTING_HOSTS={'magicbricks.com','99acres.com','housing.com','zillow.com','realtor.com','redfin.com'}


def source_quality(record):
    ref=record.get('reference','')
    try:
        parsed_public(ref)
        p=urlparse(ref);host=(p.hostname or '').lower().removeprefix('www.')
        host=HOST_ALIASES.get(host,host)
        parts=p.path.strip('/').split('/')
        for domains,kind,reason in [(DIRECTORY_HOSTS,'directory_page','People directory results do not establish a matching identity.'),(LISTING_HOSTS,'commercial_listing','Property listings are outside public-account discovery evidence.')]:
            if any(host==d or host.endswith('.'+d) for d in domains):return {'kind':kind,'account_candidate':False,'usable_for_ai':False,'reason':reason}
        if host in PROFILE_HOSTS and parts[0].lower() in DISCOVERY_ROUTES and parts[0].lower() in NAVIGATION.get(host,DISCOVERY_ROUTES):
            return {'kind':'discovery_page','account_candidate':False,'usable_for_ai':False,'reason':'Search/category page; name lists do not establish relationships.'}
        profile=bool(account_identity(ref))
        if profile:return {'kind':'profile','account_candidate':True,'usable_for_ai':True,'reason':'Profile-shaped URL; existence and ownership remain unverified.'}
        return {'kind':'context','account_candidate':False,'usable_for_ai':True,'reason':'Context source; not a recognized account profile URL.'}
    except (ValueError,TypeError,AttributeError):
        return {'kind':'unknown','account_candidate':False,'usable_for_ai':False,'reason':'Missing or invalid source URL.'}


def evidence_gate(record,case=None):
    quality=source_quality(record)
    if record.get('analyst_status')=='Rejected':return {'eligible':False,'reason':'Analyst rejected this source.','strength':0}
    if record.get('assertion_only') or record.get('origin') in ('explicit-linked-profile','derived-public-content'):return {'eligible':False,'reason':'Supplied assertions and generated navigation captions are not independent source evidence; review the parent citation.','strength':0}
    if not quality['usable_for_ai']:return {'eligible':False,'reason':quality['reason'],'strength':0}
    if case is None:return {'eligible':True,'reason':'Provenance filter only; no case context supplied.','strength':1}
    if record.get('analyst_status')=='Confirmed':return {'eligible':True,'reason':'Analyst-confirmed evidence; retain source citations.','strength':4}
    def norm(s):return ' '.join(unicodedata.normalize('NFKC',str(s)).casefold().split())
    blob=norm(record.get('title','')+'\n'+record.get('detail','')+'\n'+record.get('reference',''))
    def match(v):return bool(v and re.search(r'(?<!\w)'+re.escape(norm(v).lstrip('@'))+r'(?!\w)',blob))
    from profile_registry import supplied_profiles
    try:anchor=canonical_reference(record.get('reference','')) in supplied_profiles(case)
    except ValueError:anchor=False
    handle=any(match(v) for f in ('usernames','instagram','tiktok','vsco','emails') for v in case.get(f,[]))
    name=any(match(v) or (len(v.split())>2 and match(v.split()[0]+' '+v.split()[-1])) for v in case.get('names',[])+case.get('spelling_variants',[]))
    if anchor or handle:return {'eligible':True,'reason':'Matches an exact supplied account reference or identifier; ownership unverified.','strength':3}
    if name:return {'eligible':True,'reason':'Matching name only; a namesake is possible.','strength':1}
    return {'eligible':False,'reason':'No complete supplied name, identifier or account reference matched.','strength':0}

def ranked_ai_records(records,case=None):
    eligible=[r for r in records if evidence_gate(r,case)['eligible']]
    def score(r):
        relevance=r.get('relevance',{})
        return (evidence_gate(r,case)['strength'],bool(r.get('observations',{}).get('profile')),bool(relevance.get('strong_anchor')),
                len(relevance.get('matched_identifiers',[])),source_quality(r)['account_candidate'],len(r.get('detail','')))
    ordered=sorted(eligible,key=score,reverse=True);seen=set();seen_text=set();result=[]
    for record in ordered:
        try:key=canonical_reference(record.get('reference',''))
        except ValueError:key=record.get('id')
        text=' '.join(record.get('detail','').casefold().split())
        if key in seen or (len(text)>=60 and text in seen_text):continue
        seen.add(key)
        if len(text)>=60:seen_text.add(text)
        result.append(record)
    return result

def evidence_excerpt(record,case,maximum=1500):
    """Keep one exact contiguous source window near supplied identifiers."""
    text=record.get('detail','');identifiers=[]
    for field in ('names','spelling_variants','usernames','instagram','tiktok','vsco','emails'):
        identifiers.extend(case.get(field,[]))
    identifiers += [n.split()[0]+' '+n.split()[-1] for n in case.get('names',[]) if len(n.split())>2]
    positions=[]
    for value in identifiers:
        pattern=r'(?<!\w)'+r'\s+'.join(re.escape(v) for v in value.lstrip('@').split())+r'(?!\w)'
        match=re.search(pattern,text,re.IGNORECASE)
        if match:positions.append(match.start())
    start=max(0,min(positions)-200) if positions else 0
    start=min(start,max(0,len(text)-maximum));end=min(len(text),start+maximum)
    return {'text':text[start:end],'start':start,'end':end}
