"""Bounded, deterministic clue following and evidence-linked report synthesis."""
from collections import deque
import hashlib
import json
import re
from urllib.parse import urlparse

from research_connectors import normalize_steam
from social_profiles import detect_platform, normalize_profile, profile_reference

KINDS={'names':'person','usernames':'username','emails':'email','phones':'phone','domains':'domain','ips':'ip','instagram':'instagram','tiktok':'tiktok','vsco':'vsco','steam':'steam'}
COMMANDS=('get_user_info','get_account_about','get_captions','get_hashtags')

def report_sections(run):
    analysis=run.get('analysis')
    if not analysis:return []
    sections=[('Investigation summary',[analysis['headline'],analysis['method']])]
    for name,title in [('stronger_leads','Stronger leads — multiple supplied identifiers'),('needs_review','Leads needing review'),('unlinked_results','Results without a supplied-identifier match'),('rejected_evidence','Previously rejected supplied evidence')]:
        sections.append((title,['['+x['citation']+'] '+x['title']+' — '+x['reason'] for x in analysis.get(name,[])] or ['None.']))
    sections.append(('Differences and contradictions to review',['['+x['citation']+'] '+x['message'] for x in analysis.get('review_flags',[])] or ['No explicit profile-name differences detected. This is not a comprehensive contradiction check.']))
    sections.append(('Discovered clues and follow-up trail',[(x['kind']+': '+x['value']+' · from ['+x['parent_citation']+'] · '+x['status']+' · '+x['reason']) for x in run.get('discovered_clues',[])] or ['No additional explicit identifiers discovered.']))
    sections.append(('Search gaps',[x.get('input','')+' · '+x.get('provider','')+' · '+x.get('status','')+' · '+x.get('message','') for x in analysis.get('coverage_gaps',[])] + ['Unsearched: '+json.dumps(x,ensure_ascii=False) for x in run.get('search_log',[]) if x['status']=='not-run'] or ['No logged source failures or unsearched inputs. Coverage still depends on selected providers.']))
    sections.append(('Unanswered questions',analysis['unanswered']))
    return sections

def report_analysis_html(run):
    import html
    return ''.join('<h2>'+html.escape(title)+'</h2>'+''.join('<p>'+html.escape(line)+'</p>' for line in lines) for title,lines in report_sections(run))

def report_analysis_markdown(run):
    return '\n'.join('## '+title+'\n\n'+'\n\n'.join('\n'.join('    '+p for p in line.splitlines()) for line in lines) for title,lines in report_sections(run))

def options(value):
    if value is None:value={}
    if not isinstance(value,dict):raise ValueError('Invalid investigation settings.')
    result={}
    for field,default in [('enabled',False),('follow_clues',True),('direct_sources',False)]:
        result[field]=value.get(field,default)
        if type(result[field]) is not bool:raise ValueError('Invalid investigation setting: '+field)
    for field,default,low,high in [('max_searches',25,1,40),('max_followups',5,0,10),('depth',1,0,2)]:
        number=value.get(field,default)
        if type(number) is not int or not low<=number<=high:raise ValueError('Investigation '+field+' is outside its allowed range.')
        result[field]=number
    result['osintgram_commands']=value.get('osintgram_commands',['get_user_info'])
    if not isinstance(result['osintgram_commands'],list) or not result['osintgram_commands'] or len(result['osintgram_commands'])>4 or any(c not in COMMANDS for c in result['osintgram_commands']):raise ValueError('Choose supported Osintgram commands.')
    result['osintgram_commands']=list(dict.fromkeys(['get_user_info']+result['osintgram_commands']))
    app_id=value.get('steam_app_id')
    if app_id in ('',None):app_id=None
    if app_id is not None and (type(app_id) is not int or not 1<=app_id<=2147483647):raise ValueError('Enter a valid numeric Steam game AppID.')
    result['steam_app_id']=app_id
    return result

def token_match(value,blob):
    return bool(re.search(r'(?<![\w])'+re.escape(value.casefold())+r'(?![\w])',blob.casefold()))

def relevance(case,record):
    blob=record.get('title','')+'\n'+record.get('detail','')+'\n'+record.get('reference','')
    matched=[];seen=set();strong=False
    for field,kind in KINDS.items():
        for value in case.get(field,[]):
            canonical=value.lstrip('@').casefold()
            hit=token_match(canonical,blob)
            if field=='phones':
                digits=re.sub(r'\D','',value)
                hit=any(re.sub(r'\D','',part)==digits for part in re.findall(r'\+?\d[\d ()\.-]{6,}\d',blob))
            if field in ('instagram','tiktok','vsco'):
                hit=hit or profile_reference(field,value).rstrip('/').casefold() in blob.casefold()
                strong=strong or (profile_reference(field,value).rstrip('/').casefold() in record.get('reference','').casefold())
            if hit and canonical not in seen:
                seen.add(canonical);matched.append(field+': '+value)
                strong=strong or field in ('phones','emails','steam')
    # Matching several identifiers is corroborating relevance, not ownership verification.
    label='Multiple supplied identifiers co-occur' if len(matched)>=2 else 'Matches one supplied identifier' if matched else 'Unlinked result — needs review'
    return {'label':label,'matched_identifiers':matched,'strong_anchor':strong,'can_expand':strong or len(matched)>=2,
            'notice':'Co-occurrence is not proof of identity. A result may concern a namesake, recycled number or unrelated account.'}

def extract_clues(blob,normalize):
    """Only explicit identifiers; never invent names, query arbitrary URLs or run tool text."""
    found=[];seen=set()
    def add(kind,value):
        try:
            if kind=='steam':value=normalize_steam(value)
            elif kind in ('instagram','tiktok','vsco'):value=normalize_profile(kind,value)
            else:_,value=normalize(kind,value)
            identity=(kind,value.casefold())
            if identity not in seen:seen.add(identity);found.append({'kind':kind,'value':value})
        except ValueError:pass
    for email in re.findall(r'(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,63}',blob):add('email',email)
    for phone in re.findall(r'(?<!\w)\+[1-9][\d ()\.-]{7,20}\d(?!\w)',blob):add('phone',phone)
    for url in re.findall(r'https?://[^\s<>"\]\[{}\\]+',blob):
        url=url.rstrip('.,;)')
        platform=detect_platform(url)
        if platform:add(platform,url)
        elif urlparse(url).hostname in ('steamcommunity.com','www.steamcommunity.com'):add('steam',url)
        elif urlparse(url).hostname:add('domain',urlparse(url).hostname)
    return found[:30]

def synthesis(run):
    records=run.get('records',[]);coverage=run.get('coverage',[])
    grouped={'stronger_leads':[],'needs_review':[],'unlinked_results':[],'rejected_evidence':[]}
    flags=[]
    for record in records:
        r=record.get('relevance',{})
        bucket='stronger_leads' if len(r.get('matched_identifiers',[]))>=2 else 'needs_review' if r.get('matched_identifiers') else 'unlinked_results'
        if record.get('analyst_status')=='Rejected':bucket='rejected_evidence'
        grouped[bucket].append({'citation':record['id'],'title':record['title'],'reason':r.get('label','Supplied or offline context; not independently verified.'),'matched_identifiers':r.get('matched_identifiers',[])})
        reported=record.get('observations',{}).get('reported_name')
        names=run['case'].get('names',[])
        if isinstance(reported,str) and reported.strip() and names and reported.strip().casefold() not in {n.strip().casefold() for n in names}:
            flags.append({'citation':record['id'],'message':'Reported profile name differs from supplied names: '+reported[:200]+'. This may be an alias or an unrelated account; review before attributing it.'})
    gaps=[{'input':c.get('seed',''),'provider':c.get('provider',''),'status':c.get('status',''),'message':c.get('message','')} for c in coverage if c.get('status') not in ('ok','empty')]
    stronger=len(grouped['stronger_leads'])
    headline=('Evidence records containing multiple supplied identifiers: '+str(stronger)+'. Review their citations before attributing them to the same person.' if stronger else 'No record linked multiple supplied identifiers. Returned leads remain unverified; no identity conclusion was made.')
    if run.get('cancel_requested'):headline='Investigation cancelled. This report contains partial results only. '+headline
    return dict(grouped,headline=headline,coverage_gaps=gaps,review_flags=flags,
                unanswered=['Ownership of supplied and discovered accounts is not established.','Missing results may reflect source coverage, privacy settings, access failures or search limits.'],
                method='Deterministic evidence summary; no generated biography or unsupported identity confidence score.',
                searched=run.get('completed',0),discovered=len(run.get('discovered_clues',[])))

def execute(service,run):
    from case_reports import now, safe_reference
    from web_search import outcome
    case=run['case'];opts=options(case.get('investigation'));queue=deque();seen=set();records={};followups=0
    cancelled=service.cancel_flags[run['id']]
    run.update(status='running',completed=0,total=0,message='Building the investigation plan…',discovered_clues=[],search_log=[],discovery_links=[])
    def enqueue(kind,value,depth=0,parent=None,origin='supplied'):
        identity=(kind,json.dumps(value,sort_keys=True).casefold())
        if identity in seen:return False
        seen.add(identity);queue.append({'kind':kind,'value':value,'depth':depth,'parent_citation':parent,'origin':origin});return True
    for field,kind in KINDS.items():
        for value in case.get(field,[]):enqueue(kind,value)
    # Provided context is input, not independent evidence. Never send full notes to a provider.
    supplied_blob=case.get('notes','')+'\n'+'\n'.join(case.get('urls',[]))
    supplied_blob+='\n'+'\n'.join((f.get('capture',{}).get('excerpt','')+'\n'+f.get('notes',''))[:10000] for f in run['supplied_findings'] if f.get('status')!='Rejected')
    for clue in extract_clues(supplied_blob,service.normalize)[:5]:enqueue(clue['kind'],clue['value'],origin='supplied-context')
    for name in case.get('names',[]):
        terms=[name]+[case[x] for x in ('employer','location') if case.get(x)]
        if len(terms)>1:enqueue('context',terms)
    initial_count=len(queue)
    if opts['max_searches']<initial_count:run['limits_note']='Search budget is smaller than the supplied/context search plan; some inputs will remain unsearched.'
    def record(provider,source,row,task,origin='retrieved'):
        title=str(row.get('title','Record'))[:500];detail=str(row.get('detail',''));ref=safe_reference(row.get('reference',''))
        if len(detail)>12000:detail=detail[:11900]+'\n[Evidence text truncated at the per-record report limit.]'
        fingerprint=hashlib.sha256(json.dumps([provider,ref or source,title,detail]).encode()).hexdigest()
        seed=task['kind']+': '+(' + '.join(task['value']) if isinstance(task['value'],list) else task['value'])
        if fingerprint in records:
            existing=records[fingerprint]
            if seed not in existing['matched_inputs']:existing['matched_inputs'].append(seed)
            if task.get('parent_citation') and task['parent_citation']!=existing['id'] and task['parent_citation'] not in existing['parent_citations']:existing['parent_citations'].append(task['parent_citation'])
            return existing
        entry={'id':'R'+str(len(records)+1).zfill(3),'provider':provider,'source':str(source)[:2000],'reference':ref,'title':title,'detail':detail,
               'matched_inputs':[seed],'retrieved_at':now(),'origin':origin,'identity_status':'Unverified relevance',
               'parent_citations':[task['parent_citation']] if task.get('parent_citation') else [],'search_depth':task['depth']}
        if isinstance(row.get('observations'),dict):entry['observations']=row['observations']
        entry['relevance']=relevance(case,entry);records[fingerprint]=entry
        return entry
    for finding in run['supplied_findings']:
        capture=finding.get('capture',{})
        entry=record('User-selected notebook finding',finding.get('source',''),{'title':finding.get('title','Finding'),'detail':capture.get('excerpt',finding.get('notes',''))+'\nAnalyst notes: '+finding.get('notes',''),'reference':capture.get('reference','')},
               {'kind':'notebook','value':finding['id'],'depth':0},'user-supplied')
        entry['analyst_status']=finding.get('status','Unverified lead')
    while queue and run['completed']<opts['max_searches'] and not cancelled.is_set():
        task=queue.popleft();kind,value=task['kind'],task['value'];seed=kind+': '+(' + '.join(value) if isinstance(value,list) else value)
        run.update(total=min(opts['max_searches'],run['completed']+len(queue)+1),message='Researching '+seed[:180]);service._save_run(run)
        reports=[]
        try:
            if kind=='context':reports.append(service.context_search(value))
            else:reports.append(service.research(kind,value))
        except ValueError as error:reports.append({'results':[{'provider':'Index research','status':'error','message':str(error),'rows':[]}],'links':[]})
        if opts['direct_sources'] and kind in ('steam','instagram') and not cancelled.is_set():
            try:
                if service.connectors is None:raise ValueError('Enable the relevant connector before direct source research.')
                reports.append(service.connectors.steam(value,opts['steam_app_id']) if kind=='steam' else service.connectors.osintgram(value,run['id'],opts['osintgram_commands']))
            except ValueError as error:reports.append({'results':[{'provider':'Steam connector' if kind=='steam' else 'Osintgram connector','status':'not-configured' if 'enable' in str(error).lower() else 'error','message':str(error),'rows':[]}],'links':[]})
        for report in reports:
            run['prepared_searches'].extend(dict(link,seed=seed,executed=False) for link in report.get('links',[]))
            if not report.get('results'):run['coverage'].append({'seed':seed,'provider':'Index research','status':'not-run','count':0,'message':'No connected source ran for this identifier.'})
            for provider in report.get('results',[]):
                rows=provider.get('rows',[]);label=provider.get('provider','Research source')
                run['coverage'].append({'seed':seed,'provider':label,'status':provider.get('status','error'),'count':len(rows),'source':provider.get('source',''),'message':provider.get('message','')})
                for row in rows:
                    origin='offline-metadata' if label=='Offline phone metadata' else 'retrieved'
                    entry=record(label,provider.get('source',''),row,task,origin)
                    if task.get('parent_citation') and task['parent_citation']!=entry['id']:
                        run['discovery_links'].append({'from':task['parent_citation'],'to':entry['id'],'relation':'Follow-up search; identity not established'})
                        field=next((f for f,k in KINDS.items() if k==kind),None)
                        if field and relevance({field:[value]},entry)['matched_identifiers']:
                            entry['relevance']['can_expand']=True
                            entry['relevance']['supported_chain_identifier']=kind+': '+value
                    if not opts['follow_clues'] or task['depth']>=opts['depth'] or origin!='retrieved' or label=='Community Ban List':continue
                    ref=entry['reference']
                    reference_clue=ref if detect_platform(ref) or urlparse(ref).hostname in ('steamcommunity.com','www.steamcommunity.com') else ''
                    clues=extract_clues(entry['title']+'\n'+entry['detail']+'\n'+reference_clue,service.normalize)
                    for clue in clues:
                        identity=(clue['kind'],json.dumps(clue['value'],sort_keys=True).casefold())
                        if identity in seen:continue
                        permitted=entry['relevance']['can_expand'] or (opts['direct_sources'] and label.startswith(('Steam public profile','Osintgram / get_user_info')))
                        scheduled=permitted and followups<opts['max_followups'] and run['completed']+len(queue)+1<opts['max_searches'] and not cancelled.is_set()
                        reason='Queued within limits' if scheduled else 'Cancelled before follow-up' if cancelled.is_set() else 'Uncertain relevance — manual review required' if not permitted else 'Follow-up budget reached'
                        clue=dict(clue,parent_citation=entry['id'],depth=task['depth']+1,status='queued' if scheduled else 'not-searched',reason=reason)
                        run['discovered_clues'].append(clue)
                        if scheduled:enqueue(clue['kind'],clue['value'],clue['depth'],entry['id'],'discovered');followups+=1
                        else:seen.add(identity)
        run['completed']+=1
        run['search_log'].append(dict(task,status='completed',seed=seed))
        run['records']=list(records.values());service._save_run(run)
    run['cancel_requested']=cancelled.is_set()
    for task in queue:
        run['search_log'].append(dict(task,status='not-run',reason='Cancelled' if cancelled.is_set() else 'Search budget reached'))
    searched={(x['kind'],json.dumps(x['value'],sort_keys=True).casefold()) for x in run['search_log'] if x['status']=='completed'}
    for clue in run['discovered_clues']:
        if clue['status']=='queued':
            clue['status']='attempted' if (clue['kind'],json.dumps(clue['value'],sort_keys=True).casefold()) in searched else 'not-searched'
            if clue['status']=='attempted':clue['reason']='Follow-up processing finished; see source coverage for successful requests, failures or missing connections.'
    run['records']=list(records.values());run['analysis']=synthesis(run)
    result_code,message=outcome(run['coverage'],run['records'])
    run.update(status='cancelled' if cancelled.is_set() else 'complete',finished_at=now(),search_outcome=result_code,message='Investigation cancelled; partial report preserved.' if cancelled.is_set() else message,
               summary={'inputs':initial_count,'records':len(records),'retrieved_records':sum(x['origin']=='retrieved' for x in records.values()),'supplied_records':sum(x['origin']=='user-supplied' for x in records.values()),
                        'offline_records':sum(x['origin']=='offline-metadata' for x in records.values()),'source_errors':sum(x['status']=='error' for x in run['coverage']),'prepared_not_run':len(run['prepared_searches']),
                        'followups_scheduled':followups,'unsearched_inputs':len(queue),'search_budget':opts['max_searches']})
    service._save_run(run)
