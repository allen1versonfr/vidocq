"""Persistent multi-input cases with bounded, cited public-index reports."""
from datetime import datetime,timezone
import copy
import hashlib
import html
import json
import os
from pathlib import Path
import re
import secrets
import threading
from urllib.parse import urlparse,urlencode
from version import VERSION
from phone_lookup import inspect_phone
from web_search import outcome
from social_profiles import PLATFORMS,normalize_profile,profile_reference
from assisted_investigation import options as investigation_options, execute as execute_investigation, report_analysis_html, report_analysis_markdown
from research_connectors import normalize_steam
from discovery_review import locations,canonical_reference

FIELDS=('names','usernames','emails','phones','domains','ips','instagram','tiktok','vsco','steam','urls')
LIMITS={'names':3,'usernames':5,'emails':5,'phones':5,'domains':5,'ips':5,'urls':10,'instagram':5,'tiktok':5,'vsco':5,'steam':5}
CAUTION='Records are search results or supplied evidence, not verified identity matches. Shared names, reassigned phone numbers, stale records, and unrelated people can produce false matches. This report covers the listed inputs and supported sources, not everything on the internet.'

def process_alive(pid):
    if type(pid) is not int or pid<=0:return False
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=(wintypes.DWORD,wintypes.BOOL,wintypes.DWORD)
        kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes=(wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD))
        kernel.CloseHandle.argtypes=(wintypes.HANDLE,)
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle:return ctypes.get_last_error()!=87
        try:
            code=wintypes.DWORD()
            return bool(kernel.GetExitCodeProcess(handle,ctypes.byref(code))) and code.value==259
        finally:kernel.CloseHandle(handle)
    try:os.kill(pid,0);return True
    except ProcessLookupError:return False
    except PermissionError:return True

def now():return datetime.now(timezone.utc).isoformat()

def safe_reference(value):
    if not isinstance(value,str) or len(value)>2000:return ''
    try:p=urlparse(value)
    except ValueError:return ''
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:return ''
    return value

def clean_case(payload,normalize):
    if not isinstance(payload,dict):raise ValueError('Invalid case input.')
    title=payload.get('title','')
    notes=payload.get('notes','')
    if not isinstance(title,str) or not title.strip() or len(title)>160:raise ValueError('Enter a case title of 1–160 characters.')
    if not isinstance(notes,str) or len(notes)>20000:raise ValueError('Case notes must be 20,000 characters or fewer.')
    region=str(payload.get('phone_region','US')).strip().upper()
    result={'title':title.strip(),'notes':notes,'phone_region':region}
    result['investigation']=investigation_options(payload.get('investigation'))
    for field in ('employer','location'):
        value=payload.get(field,'')
        if not isinstance(value,str) or len(value)>120 or any(ord(c)<32 for c in value):raise ValueError('Invalid '+field+' context.')
        result[field]=value.strip()
    result['locations']=locations(payload)
    total=0
    for field in FIELDS:
        values=payload.get(field,[])
        if isinstance(values,str):values=[x.strip() for x in values.splitlines() if x.strip()]
        if not isinstance(values,list) or len(values)>LIMITS[field]:raise ValueError(f'Too many {field}; maximum {LIMITS[field]}.')
        cleaned=[];seen=set()
        for value in values:
            if not isinstance(value,str) or not value.strip() or len(value)>2000 or any(ord(c)<32 for c in value):raise ValueError(f'Invalid {field} entry.')
            value=value.strip()
            if field in PLATFORMS:value=normalize_profile(field,value)
            elif field=='steam':value=normalize_steam(value)
            elif field=='phones':value=inspect_phone(value,region)['e164']
            elif field=='urls':
                if not safe_reference(value):raise ValueError('Reference URLs must be http(s) addresses without credentials.')
            elif field in ('names','usernames'):
                if len(value)>120:raise ValueError('Names and usernames must be at most 120 characters.')
            else:
                kind={'emails':'email','domains':'domain','ips':'ip'}[field]
                value=normalize(kind,value)[1]
            if value.casefold() not in seen:cleaned.append(value);seen.add(value.casefold())
        result[field]=cleaned
        if field!='urls':total+=len(cleaned)
    if total>15:raise ValueError('Use up to 15 searchable identifiers per case. Reference URLs and notes are additional context.')
    if not total:raise ValueError('Add at least one name, username, social profile, email, phone, domain, or public IP.')
    ids=payload.get('notebook_ids',[])
    if not isinstance(ids,list) or len(ids)>30 or any(not isinstance(x,str) or not re.fullmatch('[0-9a-f]{24}',x) for x in ids):raise ValueError('Choose up to 30 valid notebook findings.')
    result['notebook_ids']=list(dict.fromkeys(ids))
    return result

class CaseService:
    def __init__(self,database,normalize,research,news,connectors=None,context_search=None,collectors=None):
        self.database,self.normalize,self.research,self.news=database,normalize,research,news
        self.lock=threading.RLock();self.active=None
        self.cancel_flags={};self.connectors=connectors
        self.collectors=collectors
        self.context_search=context_search or (lambda terms:{'results':[{'provider':'Context web search','status':'not-configured','message':'Context index search is not connected.','rows':[]}],'links':[]})
    def initialize(self):
        with self.database() as db:
            db.execute('CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS case_runs (id TEXT PRIMARY KEY, case_id TEXT NOT NULL, data TEXT NOT NULL)')
            rows=db.execute('SELECT id,data FROM case_runs').fetchall()
            for key,raw in rows:
                data=json.loads(raw)
                if data['status'] in ('queued','running') and not process_alive(data.get('owner_pid')):
                    data.update(status='interrupted',message='Vidocq closed during this run. Start a new report to retry; completed snapshots remain available.')
                    db.execute('UPDATE case_runs SET data=? WHERE id=?',(json.dumps(data),key))
    def create(self,payload):
        data=clean_case(payload,self.normalize);data.update(id=secrets.token_hex(12),created_at=now())
        with self.database() as db:db.execute('INSERT INTO cases VALUES (?,?,?)',(data['id'],json.dumps(data),now()))
        return data
    def get(self,key):
        with self.database() as db:row=db.execute('SELECT data FROM cases WHERE id=?',(key,)).fetchone()
        if not row:raise ValueError('Case not found.')
        data=json.loads(row[0])
        for field in FIELDS:data.setdefault(field,[])
        data.setdefault('investigation',investigation_options(None))
        data.setdefault('employer','');data.setdefault('location','');data.setdefault('locations',locations(data));data.setdefault('account_decisions',[])
        return data
    def update(self,key,payload):
        previous=self.get(key)
        data=clean_case(payload,self.normalize)
        data.update(id=key,created_at=previous['created_at'],account_decisions=previous.get('account_decisions',[]))
        with self.database() as db:db.execute('UPDATE cases SET data=?,updated_at=? WHERE id=?',(json.dumps(data),now(),key))
        return data
    def account_decision(self,key,payload):
        ref=canonical_reference(payload.get('reference',''));status=payload.get('status');reason=payload.get('reason','')
        if status not in ('Rejected','Confirmed','Unverified'):raise ValueError('Choose Rejected, Confirmed or Unverified.')
        if not isinstance(reason,str) or not reason.strip() or len(reason)>2000:raise ValueError('Explain the account decision (up to 2,000 characters).')
        with self.lock,self.database() as db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT data FROM cases WHERE id=?',(key,)).fetchone()
            if not row:raise ValueError('Case not found.')
            case=json.loads(row[0]);decisions=case.setdefault('account_decisions',[])
            old=next((d for d in decisions if d['reference']==ref),None)
            decision={'reference':ref,'status':status,'reason':reason.strip(),'updated_at':now(),'history':(old.get('history',[])+[{k:old[k] for k in ('status','reason','updated_at')}]) if old else []}
            if old:decisions[decisions.index(old)]=decision
            else:
                if len(decisions)>=100:raise ValueError('This case already has 100 account decisions.')
                decisions.append(decision)
            db.execute('UPDATE cases SET data=?,updated_at=? WHERE id=?',(json.dumps(case),now(),key))
        return decision

    def browser_capture(self,key,payload,save_finding):
        case=self.get(key)
        if payload.get('consent') is not True:raise ValueError('Confirm that this is evidence you reviewed in your browser.')
        canonical_reference(payload.get('reference',''))
        ref=payload['reference'].strip()
        title=payload.get('title','');excerpt=payload.get('excerpt','');query=payload.get('query','')
        if not isinstance(title,str) or not title.strip() or len(title)>500:raise ValueError('Enter an evidence title (up to 500 characters).')
        if not isinstance(excerpt,str) or not excerpt.strip() or len(excerpt)>12000:raise ValueError('Paste a reviewed excerpt (up to 12,000 characters).')
        if not isinstance(query,str) or len(query)>1000:raise ValueError('Query must be at most 1,000 characters.')
        return save_finding({'title':title,'notes':'Manually reviewed browser evidence. Source text is user-supplied, not independently fetched or verified by Vidocq.','source':ref,'status':'Unverified lead','case_ids':[key],
            'capture':{'provider':'Browser evidence (user captured)','reference':ref,'query':query,'retrieved_at':now(),'excerpt':excerpt,'origin':'browser-capture'}})

    def list(self):
        with self.database() as db:rows=db.execute('SELECT data FROM cases ORDER BY updated_at DESC LIMIT 100').fetchall()
        return [json.loads(x[0]) for x in rows]
    def runs(self,key):
        self.get(key)
        with self.database() as db:rows=db.execute('SELECT data FROM case_runs WHERE case_id=? ORDER BY rowid DESC LIMIT 20',(key,)).fetchall()
        return [json.loads(x[0]) for x in rows]
    def run(self,key):
        with self.database() as db:row=db.execute('SELECT data FROM case_runs WHERE id=?',(key,)).fetchone()
        if not row:raise ValueError('Report not found.')
        return json.loads(row[0])
    def _save_run(self,data):
        with self.database() as db:db.execute('UPDATE case_runs SET data=? WHERE id=?',(json.dumps(data),data['id']))
    def cancel(self,key):
        self.run(key)
        with self.lock:
            flag=self.cancel_flags.get(key)
            if flag:flag.set()
        if self.connectors:self.connectors.cancel(key)
        if self.collectors:self.collectors.cancel(key)
        return {'cancel_requested':bool(flag),'message':'Cancellation requested. Current requests may finish; completed evidence will be retained.' if flag else 'This report is no longer running.'}
    def start(self,key,consent=False):
        if consent is not True:raise ValueError('Confirm sending the listed identifiers to public-index providers before running the report.')
        with self.lock:
            if self.active:raise ValueError('Another case report is running. Wait for it to finish.')
            case=self.get(key)
            supplied=[]
            investigation=[]
            with self.database() as db:
                for finding_id in case['notebook_ids']:
                    row=db.execute('SELECT data FROM findings WHERE id=?',(finding_id,)).fetchone()
                    if row:supplied.append(json.loads(row[0]))
                supplied_ids={f['id'] for f in supplied}
                for raw, in db.execute('SELECT data FROM findings'):
                    finding=json.loads(raw)
                    if finding.get('capture',{}).get('origin')=='browser-capture' and key in finding.get('case_ids',[]) and finding['id'] not in supplied_ids:
                        supplied.append(finding);supplied_ids.add(finding['id'])
                if len(supplied)>60:raise ValueError('Use at most 60 supplied findings per run.')
                if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='investigation_items'").fetchone():
                    items=[dict(json.loads(raw),kind=kind) for kind,raw in db.execute('SELECT kind,data FROM investigation_items')]
                    selected=set(case['notebook_ids'])
                    investigation=[item for item in items if key in item.get('case_ids',[]) or selected.intersection(item.get('evidence_ids',[]))]
            run={'id':secrets.token_hex(12),'case_id':key,'case':copy.deepcopy(case),'supplied_findings':supplied,
                'investigation_items':investigation,
                'version':VERSION,'owner_pid':os.getpid(),'created_at':now(),'status':'queued','completed':0,'total':0,'message':'Preparing report…','records':[],
                'social_profiles':[{'platform':platform,'handle':handle,'reference':profile_reference(platform,handle),'status':'User supplied; not visited or verified'} for platform in PLATFORMS for handle in case.get(platform,[])],
                'coverage':[],'prepared_searches':[],'phone_metadata':[],'limitations':[CAUTION,'Social profile, phone, email and username ownership is not verified. No calls, messages, account checks, direct profile visits or live target scans are performed.','Reference URLs and notes are context only. Original URLs are never fetched. Search links are prepared but not automatically run.']}
            opts=investigation_options(case.get('investigation'))
            if opts['enabled']:
                if self.collectors:
                    snapshot=self.collectors.status()
                    if isinstance(snapshot,dict):run['collector_configuration']=snapshot
                if self.connectors:
                    snapshot=self.connectors.status()
                    if isinstance(snapshot,dict):run['connector_configuration']=snapshot
                run['limitations']=[CAUTION,'Automatic follow-ups are bounded leads, not identity proof. Only selected connector data and reviewed indexes are requested; no arbitrary source pages are fetched.',
                                    'Steam/Osintgram are used only when configured and allowed for this case. Providers may log requests or charge; search budgets count identifier searches, not a guaranteed API bill.',
                                    'Notes/reference URLs may supply explicit identifiers. Their contents are not automatically fetched. Context queries send supplied name/employer/location terms to the connected search index.']
                for p in run['social_profiles']:p['status']='Supplied reference. Index/connector activity is documented in source coverage.'
            with self.database() as db:db.execute('INSERT INTO case_runs VALUES (?,?,?)',(run['id'],key,json.dumps(run)))
            self.active=run['id']
            self.cancel_flags[run['id']]=threading.Event()
            threading.Thread(target=self._execute,args=(run,),daemon=True).start()
            return self.run(run['id'])
    def _execute(self,run):
        try:
            if run['case'].get('investigation',{}).get('enabled'):
                execute_investigation(self,run)
                return
            case=run['case'];tasks=[]
            for field in FIELDS:
                if field=='urls':continue
                for value in case.get(field,[]):tasks.append((field,value))
            run.update(status='running',total=len(tasks),message='Searching supported sources…');self._save_run(run)
            records={}
            def record(provider,source,title,detail,seed,origin='retrieved',reference=''):
                source=str(source)[:2000];title=str(title)[:500];detail=str(detail)[:12000]
                key=hashlib.sha256(json.dumps([provider,reference or source,title,detail]).encode()).hexdigest()
                if key in records:
                    if seed not in records[key]['matched_inputs']:records[key]['matched_inputs'].append(seed)
                    return
                records[key]={'id':'R'+str(len(records)+1).zfill(3),'provider':provider,'source':source,'reference':safe_reference(reference),
                    'title':title,'detail':detail,'matched_inputs':[seed],'retrieved_at':now(),'origin':origin,'identity_status':'Unverified relevance'}
            for finding in run['supplied_findings']:
                capture=finding.get('capture',{})
                detail=(capture.get('excerpt','')+'\n\nAnalyst assessment: '+finding.get('notes','')) if capture else finding.get('notes','')
                if capture:detail+='\nPreserved provenance: '+json.dumps(capture,ensure_ascii=False)
                record('User-selected notebook finding',finding.get('source',''),finding.get('title','Finding'),detail,
                       'Notebook '+finding['id'],'user-supplied')
            for field,value in tasks:
                if self.cancel_flags[run['id']].is_set():break
                seed=field+': '+value
                run['message']='Processing '+field+' ('+str(run['completed']+1)+'/'+str(run['total'])+')';self._save_run(run)
                try:
                    if field=='phones':
                        metadata=inspect_phone(value,case['phone_region']);run['phone_metadata'].append(metadata)
                        record('Offline phone metadata','libphonenumber metadata '+metadata['metadata_version'],metadata['international'],'Country calling code: +'+str(metadata['country_calling_code'])+'\nRegion: '+metadata['region_code']+'\nNumber type: '+metadata['number_type']+'\nAllocation region: '+metadata['allocation_region']+'\nOriginal carrier allocation: '+metadata['original_carrier']+'\nValid numbering plan: '+str(metadata['valid_numbering_plan'])+'\n'+metadata['notice'],seed,'offline-metadata')
                        report=self.research('phone',value)
                        report['results']=[x for x in report.get('results',[]) if x['provider']!='Offline phone metadata']
                        run['coverage'].append({'seed':seed,'provider':'Offline phone metadata','status':'ok','count':1,'message':'No live phone or owner lookup was performed.'})
                    elif field in PLATFORMS or field=='steam':report=self.research(field,value)
                    elif field=='names':report=self.research('person',value)
                    else:report=self.research({'usernames':'username','emails':'email','domains':'domain','ips':'ip'}[field],value)
                    run['prepared_searches'].extend(dict(link,seed=seed,executed=False) for link in report.get('links',[]))
                    if not report.get('results'):
                        run['coverage'].append({'seed':seed,'provider':'Web index searches','status':'not-run','count':0,'message':'Prepared browser searches only; no automatic result retrieval for this input.'})
                    for provider in report.get('results',[]):
                        rows=provider.get('rows',[])
                        run['coverage'].append({'seed':seed,'provider':provider['provider'],'status':provider['status'],'count':len(rows),'source':provider.get('source',''),'message':provider.get('message','')})
                        for row in rows:record(provider['provider'],provider.get('source',''),row.get('title','Record'),row.get('detail',''),seed,reference=row.get('reference',''))
                except Exception as error:
                    run['coverage'].append({'seed':seed,'provider':'Input processing','status':'error','count':0,'message':str(error) if isinstance(error,ValueError) else 'The input could not complete. Other inputs were retained.'})
                run['completed']+=1;run['records']=list(records.values());self._save_run(run)
            result_code,result_message=outcome(run['coverage'],run['records'])
            run.update(status='complete',finished_at=now(),search_outcome=result_code,message=result_message)
            if self.cancel_flags[run['id']].is_set():run.update(status='cancelled',message='Cancelled; partial evidence retained.')
            run['summary']={'inputs':len(tasks),'records':len(records),'retrieved_records':sum(x['origin']=='retrieved' for x in records.values()),
                'supplied_records':sum(x['origin']=='user-supplied' for x in records.values()),'offline_records':sum(x['origin']=='offline-metadata' for x in records.values()),
                'source_errors':sum(x['status']=='error' for x in run['coverage']),'prepared_not_run':len(run['prepared_searches'])}
            self._save_run(run)
        except Exception:
            run.update(status='failed',message='The report stopped unexpectedly. Completed records were preserved. Start a new run to retry.');self._save_run(run)
        finally:
            with self.lock:
                self.active=None;self.cancel_flags.pop(run['id'],None)


def report_markdown(run):
    # Indent user/provider text as code blocks, so Markdown cannot inject links or HTML.
    def block(value):return '\n'.join('    '+line for line in str(value).splitlines())+'\n'
    lines=['# Vidocq case report', '',block(run['case']['title']), 'Generated: '+str(run.get('finished_at',run['created_at'])),
        'App version: '+run['version'],'Status: '+run['status'],block(run.get('message','')),'', '## Scope and uncertainty','',CAUTION,'', '## Summary','',block(json.dumps(run.get('summary',{}),indent=2)),
        '## Supplied context','',block(json.dumps(run['case'],ensure_ascii=False,indent=2)),'## Supplied social profiles','',block(json.dumps(run.get('social_profiles',[]),ensure_ascii=False,indent=2)),'## Source coverage','']
    for item in run['coverage']:lines.extend([block(json.dumps(item,ensure_ascii=False)), ''])
    if run.get('analysis'):lines.extend([report_analysis_markdown(run),''])
    lines.extend(['## Evidence and citations',''])
    for item in run['records']:
        lines.extend(['### '+item['id'],block(item['title']),block(item['detail']),block('Provider: '+item['provider']+'\nSource request: '+item['source']+'\nReference: '+item['reference']+'\nInputs: '+', '.join(item['matched_inputs'])+'\nOrigin: '+item['origin']+'\nRetrieved: '+item['retrieved_at']+'\nIdentity status: '+item['identity_status'])])
    lines.extend(['## Prepared searches — not run',''])
    for item in run['prepared_searches']:lines.append(block(item['seed']+'\n'+item['title']+'\n'+item['url']))
    lines.extend(['## Limitations','',block('\n'.join(run['limitations']))])
    lines.extend(['## Analyst relationships and timeline (supplied assertions)','',block(json.dumps(run.get('investigation_items',[]),ensure_ascii=False,indent=2))])
    if any(c.get('provider')=='Have I Been Pwned' for c in run.get('coverage',[])):
        lines.extend(['## Data attribution','','Breach data: [Have I Been Pwned](https://haveibeenpwned.com/), licensed under CC BY 4.0.'])
    return '\n'.join(lines)


def report_html(run):
    e=lambda value:html.escape(str(value),quote=True)
    title=e(run['case']['title']);summary=run.get('summary',{})
    evidence=''.join('<article><h3>'+e(x['id'])+' · '+e(x['title'])+'</h3><p>'+e(x['detail'])+'</p><dl>'+''.join('<dt>'+e(k)+'</dt><dd>'+e(v)+'</dd>' for k,v in [('Provider',x['provider']),('Source request',x['source']),('Reference',x['reference']),('Matched inputs',', '.join(x['matched_inputs'])),('Origin',x['origin']),('Retrieved',x['retrieved_at']),('Identity',x['identity_status'])])+'</dl></article>' for x in run['records'])
    coverage=''.join('<tr><td>'+e(x['seed'])+'</td><td>'+e(x['provider'])+'</td><td>'+e(x['status'])+'</td><td>'+e(x['count'])+'</td><td>'+e(x.get('message',''))+'</td></tr>' for x in run['coverage'])
    searches=''.join('<li><strong>'+e(x['title'])+'</strong><p>'+e(x['seed'])+'</p><code>'+e(x['url'])+'</code></li>' for x in run['prepared_searches'])
    summary_text=('Processed '+str(summary.get('inputs',run['completed']))+' identifiers. '+str(summary.get('retrieved_records',0))+' records were retrieved from supported indexes, '+str(summary.get('offline_records',0))+' were offline metadata, and '+str(summary.get('supplied_records',0))+' were supplied notebook findings. '+str(summary.get('source_errors',0))+' source operations failed; '+str(summary.get('prepared_not_run',len(run['prepared_searches'])))+' browser searches were prepared but not run.')
    social='<h2>Supplied social profiles</h2>'+(''.join('<p>'+e(p['platform'])+' · @'+e(p['handle'])+'<br>'+e(p['reference'])+'<br>'+e(p['status'])+'</p>' for p in run.get('social_profiles',[])) or '<p>No platform profiles supplied.</p>')
    context_text=lambda value:'\n'.join(value) if isinstance(value,list) and all(isinstance(v,str) for v in value) else json.dumps(value,ensure_ascii=False,indent=2) if isinstance(value,(list,dict)) else str(value)
    context='<dl>'+''.join('<dt>'+e(field.replace('_',' ').title())+'</dt><dd>'+e(context_text(value))+'</dd>' for field,value in run['case'].items() if field not in ('id','notebook_ids','created_at') and value)+'</dl>'
    context+='<h2>Analyst relationships and timeline (supplied assertions)</h2><pre>'+e(json.dumps(run.get('investigation_items',[]),ensure_ascii=False,indent=2))+'</pre>'
    if any(c.get('provider')=='Have I Been Pwned' for c in run.get('coverage',[])):
        context+='<p>Breach data: <a href="https://haveibeenpwned.com/" rel="noreferrer">Have I Been Pwned</a>, licensed under CC BY 4.0.</p>'
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'"><title>'+title+' · Vidocq report</title><style>body{font:16px/1.6 system-ui,sans-serif;max-width:1000px;margin:40px auto;padding:24px;color:#172638}h1,h2,h3{line-height:1.2}h2{margin-top:36px;border-bottom:1px solid #ccd5df;padding-bottom:12px}p,dd,code,pre{white-space:pre-wrap;overflow-wrap:anywhere}article{padding:20px;border:1px solid #ccd5df;margin:16px 0;break-inside:avoid}dt{font-weight:bold}dd{margin:0 0 8px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd5df;padding:8px;text-align:left;overflow-wrap:anywhere}aside{padding:20px;background:#fff3d8}@media print{body{margin:0;max-width:none;padding:8px;font-size:11px}h2{break-after:avoid}}</style><header><p>VIDOCQ · CASE REPORT · '+e(run['version'])+'</p><h1>'+title+'</h1><p>'+e(run.get('finished_at',run['created_at']))+' · '+e(run['status'])+'</p><p>'+e(run.get('message',''))+'</p></header><aside>'+e(CAUTION)+'</aside><h2>Summary</h2><p>'+e(summary_text)+'</p>'+report_analysis_html(run)+'<h2>Supplied context</h2>'+context+social+'<h2>Source coverage</h2><table><thead><tr><th>Input</th><th>Provider</th><th>Status</th><th>Records</th><th>Notes</th></tr></thead><tbody>'+coverage+'</tbody></table><h2>Evidence and citations</h2>'+ (evidence or '<p>No records were returned. See the source coverage for empty results, failures and unsupported searches.</p>')+'<h2>Prepared searches — not run</h2><ul>'+searches+'</ul><h2>Limitations</h2><ul>'+''.join('<li>'+e(x)+'</li>' for x in run['limitations'])+'</ul><p>This export contains the supplied case details. Store and share it deliberately. Use your browser’s Print command to save a PDF.</p></html>'
