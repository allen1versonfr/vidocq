"""Offline benchmark validation and scoring; never submits keys to a collector."""
from datetime import date
import hashlib,json,re
from urllib.parse import urlparse
from profile_registry import account_identity,parsed_public

ROLES={'seed','withheld','previously-confirmed','supplied-handle-control','negative'}

def validate_key(sheet):
    accounts=sheet.get('accounts') if isinstance(sheet,dict) else None
    if not isinstance(accounts,list) or not accounts or len(accounts)>1000:raise ValueError('Use a nonempty account list with at most 1,000 entries.')
    seen=set();seen_accounts=set();warnings=[];clean=[]
    for raw in accounts:
        if not isinstance(raw,dict):raise ValueError('Invalid account entry.')
        row=dict(raw);key=row.get('id');role=row.get('role','withheld')
        if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',key) or key in seen:raise ValueError('Account IDs must be unique and use letters, numbers, underscores or dashes.')
        seen.add(key)
        if role not in ROLES:raise ValueError(key+': invalid account role.')
        exclusion=row.get('exclude_reason','')
        if exclusion and (not isinstance(exclusion,str) or len(exclusion)>1000):raise ValueError(key+': invalid exclusion reason.')
        ref=row.get('canonical_url')
        if not ref and not exclusion:raise ValueError(key+': missing profile URL; provide it or an explicit exclusion reason before testing.')
        if ref:
            parsed_public(ref);identity=account_identity(ref)
            if not identity and not exclusion:raise ValueError(key+': URL is not a supported account profile; supply a supported URL or an explicit exclusion reason.')
            if identity and not exclusion:
                if identity['reference'] in seen_accounts:raise ValueError(key+': duplicate account identity in scoring key.')
                seen_accounts.add(identity['reference'])
        variants=row.get('reference_variants',[])
        if not isinstance(variants,list) or len(variants)>10:raise ValueError(key+': invalid reference variants.')
        for variant in variants:parsed_public(variant)
        visibility=row.get('public_visibility','unknown');ownership=row.get('ownership','unknown')
        if visibility not in ('public','restricted','unavailable','unknown') or ownership not in ('confirmed','asserted','unknown','rejected'):raise ValueError(key+': invalid eligibility labels.')
        verified=row.get('public_verified_on')
        if verified:
            try:age=(date.today()-date.fromisoformat(verified)).days
            except (ValueError,TypeError):raise ValueError(key+': invalid verification date.') from None
            if age<0:raise ValueError(key+': verification date is in the future.')
        else:age=None
        if not exclusion and (ownership!='confirmed' or visibility!='public' or age is None or age>30):warnings.append(key+': not independently eligible for public-account recall.')
        row.update(role=role,ownership=ownership,public_visibility=visibility,eligible=not exclusion and ownership=='confirmed' and visibility=='public' and age is not None and age<=30)
        clean.append(row)
    return {'accounts':clean,'warnings':warnings,'key_sha256':hashlib.sha256(json.dumps(sheet,sort_keys=True).encode()).hexdigest()}

def reference_key(value,case_sensitive=False):
    """Scoring oracle uses explicit expected URLs/variants, not discovery scores."""
    try:p=parsed_public(value)
    except ValueError:return None
    host=p.hostname.removeprefix('www.');path=p.path.rstrip('/') or '/'
    return (host,path if case_sensitive else path.casefold())

def evaluate(report,sheet):
    key=validate_key(sheet)
    if report.get('status') not in ('complete','cancelled','interrupted','failed'):raise ValueError('Seal the blind report before scoring or running controls.')
    records=report.get('records',[])
    if not isinstance(records,list) or any(not isinstance(r,dict) for r in records):raise ValueError('Invalid sealed report records.')
    matched={};eligible=[];excluded=[];all_known=set()
    for row in key['accounts']:
        if row.get('exclude_reason'):excluded.append(row['id']);continue
        case_sensitive=row.get('case_sensitive',row.get('platform')=='Spotify')
        expected={reference_key(v,case_sensitive) for v in [row['canonical_url']]+row.get('reference_variants',[])}
        expected.discard(None);all_known.update(reference_key(v) for v in [row['canonical_url']]+row.get('reference_variants',[]))
        found=[r for r in records if r.get('analyst_status')!='Rejected' and reference_key(r.get('reference',''),case_sensitive) in expected]
        if found:matched[row['id']]=[r.get('id') for r in found]
        if row['eligible'] and row['role']=='withheld':eligible.append(row['id'])
    new=[r['id'] for r in key['accounts'] if r['role']=='withheld' and r['id'] in matched]
    negatives=[r['id'] for r in key['accounts'] if r['role']=='negative' and r['id'] in matched]
    eligible_found=[i for i in eligible if i in matched]
    candidates={reference_key(r['reference']) for r in records if r.get('analyst_status')!='Rejected' and account_identity(r.get('reference',''))}
    confirmed_positive=set();confirmed_negative=set();seeds=set()
    for row in key['accounts']:
        refs={reference_key(v) for v in [row.get('canonical_url','')]+row.get('reference_variants',[])};refs.discard(None)
        if row['role'] in ('seed','previously-confirmed'):seeds.update(refs)
        elif row['role']=='negative' and row['ownership'] in ('confirmed','rejected'):confirmed_negative.update(refs)
        elif row['ownership']=='confirmed' and row['role']!='negative':confirmed_positive.update(refs)
    new_candidates=candidates-seeds;right=len(new_candidates&confirmed_positive);wrong=len(new_candidates&confirmed_negative)
    unresolved=len(new_candidates-confirmed_positive-confirmed_negative)
    return {'key_sha256':key['key_sha256'],'report_sha256':hashlib.sha256(json.dumps(report,sort_keys=True).encode()).hexdigest(),'new_known_list_matches':new,'matched_citations':matched,
            'seed_rediscoveries':[r['id'] for r in key['accounts'] if r['role']=='seed' and r['id'] in matched],
            'prior_rediscoveries':[r['id'] for r in key['accounts'] if r['role']=='previously-confirmed' and r['id'] in matched],
            'negative_matches':negatives,'eligible_withheld':len(eligible),'eligible_found':len(eligible_found),'public_account_recall':len(eligible_found)/len(eligible) if eligible else None,
            'unresolved_candidate_profiles':unresolved,'resolved_candidate_precision':right/(right+wrong) if right+wrong else None,'resolved_correct':right,'resolved_wrong':wrong,'excluded_ids':excluded,'warnings':key['warnings'],
            'notice':'Known-list matches are not independently verified discoveries. Precision requires ownership labels for every resolved candidate; unresolved candidates remain separate.'}

def compare_conditions(conditions,sheet):
    fields=('names','usernames','locations','location','urls','aliases','spelling_variants','notes','employer','emails','phones','domains','ips','instagram','tiktok','vsco','steam','notebook_ids')
    fingerprints=[];results=[]
    for label,report in conditions:
        case=report.get('case',{});fingerprints.append(hashlib.sha256(json.dumps({f:case.get(f) for f in fields},sort_keys=True).encode()).hexdigest())
        results.append({'condition':label,'score':evaluate(report,sheet),'run_configuration':report.get('research_configuration',{}),'requests':report.get('request_ledger',{})})
    return {'same_starting_clues':len(set(fingerprints))<=1,'conditions':results,'notice':'Different providers, rank depth, reviewed bios and model modes are different conditions. Use fixed clues and budgets; no score increase is inferred automatically.'}
