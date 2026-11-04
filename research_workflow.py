"""Finite query variations and guided review plans, using supplied clues only."""
from discovery_tools import research_plan,query_plan
from discovery_review import locations

NEXT_STEPS=['Collect reviewed public bios and outgoing links from supplied profiles.','Review the prepared major-index queries and attach selected public results.','Independently verify a current positive and negative public checker control.','Review conflicting display names with their original citations.','Confirm account ownership with the consenting subject before attribution.','Add a dated historical alias or approved spelling only when supported by evidence.']

def variations(case):
    result=research_plan(case);seen={tuple(q['terms']) for q in result}
    for name in case.get('names',[]):
        parts=name.split()
        if len(parts)>1:
            terms=[parts[0],parts[-1]]
            if tuple(terms) not in seen:result.append({'terms':terms,'reason':'separate supplied first/last name tokens'});seen.add(tuple(terms))
    base={tuple(q['terms']) for q in query_plan(case)}
    return [q for q in result if tuple(q['terms']) not in base][:12]

def review_plan(case,run=None):
    searched={tuple(x['value']) for x in (run or {}).get('search_log',[]) if x['kind']=='context' and x['status']=='completed'}
    queries=[];seen=set()
    for q in variations(case)+query_plan(case):
        key=tuple(q['terms'])
        if key in seen:continue
        seen.add(key);queries.append({**q,'previously_attempted':key in searched,'reviewed_capture_required':True})
    return {'case_id':case['id'],'previous_run':(run or {}).get('id'),'queries':queries[:16],'next_steps':NEXT_STEPS,'source_gaps':(run or {}).get('coverage_assessment'),'notice':'Open the next search in your browser, review/capture public text or a profile bio, then create a new report with the added evidence. Continuing uses a new approved run budget; earlier reports remain unchanged.'}
