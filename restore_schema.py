"""Bounded structural validation for restored report data before SQLite writes."""
def mapping(value):
    if not isinstance(value,dict):raise ValueError('Expected an imported object.')
    return value

def strings(value,limit=10000):
    if not isinstance(value,list) or len(value)>limit or any(not isinstance(v,str) for v in value):raise ValueError('Invalid imported string list.')

def rows(value,fields=(),limit=10000):
    if not isinstance(value,list) or len(value)>limit:raise ValueError('Invalid imported record list.')
    for row in value:
        mapping(row)
        if any(not isinstance(row.get(f),str) for f in fields):raise ValueError('Invalid imported record fields.')
    return value

def validate_report(report):
    mapping(report)
    for record in rows(report.get('records',[]),('id','title','detail')):
        if not isinstance(record.get('reference',''),str):raise ValueError('Invalid imported reference.')
        strings(record.get('matched_inputs',[]))
        relevance=mapping(record.get('relevance',{}));strings(relevance.get('matched_identifiers',[]))
        observations=mapping(record.get('observations',{}))
        if 'profile' in observations:
            profile=mapping(observations['profile']);strings(profile.get('links',[]),50)
            if any(not isinstance(profile.get(k,''),str) for k in ('biography','display_name','stable_id','handle')):raise ValueError('Invalid imported profile observation.')
    for field in ('coverage','prepared_searches','supplied_findings','query_variations'):rows(report.get(field,[]))
    rows(report.get('link_evidence',[]),('citation','source','target','relation','observed_at'))
    rows(report.get('discovered_clues',[]),('kind','value','parent_citation','status','reason'))
    rows(report.get('search_log',[]),('status',))
    mapping(report.get('summary',{}))
    if report.get('analysis') is not None:
        analysis=mapping(report['analysis']);mapping(analysis.get('counts',{}))
        if any(not isinstance(analysis.get(k),str) for k in ('headline','method')):raise ValueError('Invalid imported analysis summary.')
        for name in ('stronger_leads','needs_review','unlinked_results','rejected_evidence'):rows(analysis.get(name,[]),('citation','title','reason'))
        rows(analysis.get('review_flags',[]),('citation','message'));strings(analysis.get('unanswered',[]))
    ai=mapping(report.get('ai',{}));strings(ai.get('errors',[]))
    if ai.get('summary') is not None:rows(mapping(ai['summary']).get('claims',[]),('citation','quote'))
    if ai.get('assessment') is not None:mapping(ai['assessment'])
