"""Read-only post-test miss diagnosis. Answer keys never enter a research plan."""
import hashlib,json
from collections import Counter
from urllib.parse import urlparse,parse_qs
from benchmark_evaluation import validate_key
from retrieval_diagnostics import diagnose_control
from profile_registry import account_identity,canonical_reference,supplied_profiles

def diagnostic_reference(value):
    try:return canonical_reference(value)
    except (ValueError,TypeError):return None

def diagnose_misses(report,sheet,controls=None):
    if not isinstance(report,dict):raise ValueError('Use a finished report object.')
    if report.get('status') not in ('complete','cancelled','interrupted','failed'):raise ValueError('Finish and seal the blind report before examining its answer key.')
    # Exact-URL diagnosis also covers profile-shaped pages outside the finite
    # registry. This never grants public-account recall/ownership eligibility.
    prepared=[];outside=set()
    if not isinstance(sheet,dict) or not isinstance(sheet.get('accounts'),list):raise ValueError('Use an answer key with an accounts list.')
    for raw in sheet['accounts']:
        if not isinstance(raw,dict):raise ValueError('Invalid answer-key row.')
        row=dict(raw)
        if row.get('canonical_url') and not account_identity(row['canonical_url']) and not row.get('exclude_reason'):
            if isinstance(row.get('id'),str):outside.add(row['id'])
            row['exclude_reason']='Outside the finite profile registry; exact-URL diagnosis only.'
        prepared.append(row)
    accounts=validate_key({'accounts':prepared})['accounts'];records=report.get('records',[]);controls=controls or {};results=[]
    for row in accounts:
        if row['id'] in outside:row.pop('exclude_reason',None)
    coverage=report.get('coverage',[])
    if not isinstance(records,list) or any(not isinstance(r,dict) for r in records) or not isinstance(coverage,list) or any(not isinstance(c,dict) for c in coverage):raise ValueError('Invalid report evidence or coverage.')
    if not isinstance(controls,dict):raise ValueError('Use controls indexed by account id.')
    for c in coverage:
        refs=c.get('returned_references',[])
        if not isinstance(refs,list) or any(not isinstance(r,dict) for r in refs):raise ValueError('Invalid adapter reference trace.')
    links=report.get('link_evidence',[])
    if not isinstance(links,list) or any(not isinstance(e,dict) for e in links):raise ValueError('Invalid link evidence.')
    def query(source):
        try:p=urlparse(source);return (p.hostname,tuple(parse_qs(p.query).get('q',[])))
        except (ValueError,TypeError):return (None,())
    original_queries={query(c.get('source','')) for c in coverage if query(c.get('source',''))[1]}
    supplied=supplied_profiles(report.get('case',{}))
    for a in accounts:
        result={'id':a['id'],'role':a['role'],'profile_registry_supported':bool(account_identity(a.get('canonical_url','')))}
        expected={diagnostic_reference(u) for u in [a.get('canonical_url','')]+a.get('reference_variants',[])};expected.discard(None)
        matches=lambda ref:diagnostic_reference(ref) in expected
        found=[r for r in records if matches(r.get('reference',''))]
        active=[r for r in found if r.get('analyst_status')!='Rejected']
        observed=[r for c in coverage for r in c.get('returned_references',[]) if matches(r.get('reference',''))]
        linked=[e for e in links if matches(e.get('target',''))]
        if a.get('exclude_reason'):result.update(stage='excluded',reason=a['exclude_reason'])
        elif a['role']!='withheld':result.update(stage='not-held-out',reason='Seeds, prior accounts, supplied-handle controls and negatives earn no new-discovery credit.')
        elif expected & supplied:result.update(stage='key-starting-clue-conflict',reason='This withheld URL was already supplied as a starting clue; no blind discovery credit is valid.')
        elif active:
            result.update(stage='returned-linked-review-lead' if all(r.get('origin')=='explicit-linked-profile' for r in active) else 'returned-in-blind-report',citations=[r.get('id') for r in active],reason='An exact answer URL is present; existence/ownership still require independent review.')
        elif found:result.update(stage='rejected-in-blind-report',citations=[r.get('id') for r in found],reason='Review the analyst decision and key consistency; do not silently override rejection.')
        elif observed:result.update(stage='adapter-row-missing-from-report',reason='The original blind adapter reference trace contains this URL, but no record preserves it.')
        elif linked:result.update(stage='explicit-link-not-materialized',citations=[e.get('citation') for e in linked],reason='An exact URL exists in link evidence; the link does not prove a live account or ownership.')
        elif a['id'] in controls:
            control=controls[a['id']];diagnostic=diagnose_control(a['canonical_url'],control)
            same=any(query(p.get('source','')) in original_queries and any(matches(r.get('reference','')) for r in p.get('rows',[])) for p in control.get('results',[]) if query(p.get('source',''))[1])
            result.update(stage='repeat-query-control-found-profile' if diagnostic['exact_profile_returned'] and same else 'post-test-control-only' if diagnostic['exact_profile_returned'] else 'post-test-control-incomplete' if diagnostic['stage']=='source_incomplete' else 'not-in-control-returned-rows',control_diagnostic=diagnostic,same_original_query=same,reason='Post-test controls do not change blind scores. A different answer-targeted query cannot prove a blind pipeline loss; repeat-query differences may reflect time/ranking/cache changes.')
            control_matches=[]
            for provider in control.get('results',[]):
                limits=[c.get('retrieval_diagnostics',{}).get('result_limit') for c in coverage if query(c.get('source',''))==query(provider.get('source','')) and query(c.get('source',''))[1]]
                limits=[n for n in limits if type(n) is int and n>0]
                for row in provider.get('rows',[]):
                    if not matches(row.get('reference','')):continue
                    rank=row.get('index_rank');original_limit=max(limits) if limits else None
                    control_matches.append({'rank':rank,'original_result_limit':original_limit,'provider':provider.get('provider')})
                    if original_limit and type(rank) is int and rank>original_limit:result['stage']='post-test-deeper-result'
            result['control_matches']=control_matches[:20]
        else:result.update(stage='unresolved-no-control',reason='No original retained reference, link or separately supplied control explains this miss. This does not prove index absence.')
        results.append(result)
    return {'accounts':results,'stages':dict(Counter(r['stage'] for r in results)),'network_requests':0,'discovery_score_changed':False,'report_content_sha256':hashlib.sha256(json.dumps(report,sort_keys=True).encode()).hexdigest(),'notice':'Offline diagnosis only. Controls are post-test evidence, never blind discoveries. No ownership, index-absence or 30-percent guarantee is inferred.'}
