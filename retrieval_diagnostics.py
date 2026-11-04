"""Offline scoring of sealed control responses; never makes network requests."""
from discovery_review import canonical_reference
from evidence_quality import source_quality


def diagnose_control(expected_url, report, retained_records=None):
    expected=canonical_reference(expected_url)
    providers=[p for p in report.get('results',[]) if any(n in p.get('provider','') for n in ('Brave','Mwmbl','Serper','SerpApi'))]
    rows=[r for p in providers for r in p.get('rows',[])]
    def matches(row):
        try:return canonical_reference(row.get('reference',''))==expected
        except ValueError:return False
    exact=any(matches(r) for r in rows)
    if not providers:stage='not_searched'
    elif exact and retained_records is not None and not any(matches(r) for r in retained_records):stage='lost_after_retrieval'
    elif exact:stage='exact_profile_returned'
    elif any(p.get('status') not in ('ok','empty') for p in providers):stage='source_incomplete'
    elif not rows and any(p.get('retrieval_diagnostics',{}).get('provider_rows',0)>0 for p in providers):stage='all_rows_filtered_by_adapter'
    elif not rows:stage='no_rows_returned'
    else:stage='target_not_in_returned_rows'
    return {'stage':stage,'exact_profile_returned':exact,'rows':len(rows),
            'discovery_page_rows':sum(source_quality(r)['kind']=='discovery_page' for r in rows),
            'profile_rows':sum(source_quality(r)['account_candidate'] for r in rows),
            'notice':'Missing from returned rows does not prove absent from the index. Original query, ranking, index coverage and adapter filtering remain possible causes.'}
