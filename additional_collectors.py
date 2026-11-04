"""Documented HIBP API, passive HarvestView API, and scoped Maigret companion."""
import copy
import json
import re
import threading
import time
from urllib.parse import quote,urlparse
from urllib.request import Request,ProxyHandler,build_opener
from urllib.error import HTTPError,URLError
from research_connectors import NoRedirect,ConnectorUnavailable
from collector_policy import HARVESTER_SOURCES,MAIGRET_SITES,selected
from version import VERSION

HIBP_ATTRIBUTION={'name':'Have I Been Pwned','url':'https://haveibeenpwned.com/','license':'CC BY 4.0'}

def transport(url,payload=None,key=None,service='hibp',timeout=15):
    p=urlparse(url)
    if service=='hibp':valid=p.scheme=='https' and p.hostname=='haveibeenpwned.com' and p.port is None and p.path.startswith('/api/v3/breachedaccount/')
    else:
        path_ok=bool(re.fullmatch(r'/api/v1/(?:sources|runs(?:/[A-Za-z0-9-]{1,80}(?:/cancel)?)?)',p.path)) if service=='harvester' else p.path in ('/api/about','/api/search','/api/cancel')
        valid=p.scheme=='http' and p.hostname=='127.0.0.1' and p.port is not None and 1024<=p.port<=65535 and path_ok
    if not valid or p.username or p.password:raise ValueError('Collector destination is not reviewed.')
    headers={'Accept':'application/json','User-Agent':'Vidocq/'+VERSION+' (+https://github.com/allen1versonfr/vidocq)'}
    if key:headers[{'hibp':'hibp-api-key','harvester':'X-API-Key','maigret':'X-Vidocq-Key'}[service]]=key
    raw=None
    if payload is not None:headers['Content-Type']='application/json';raw=json.dumps(payload).encode()
    try:
        with build_opener(ProxyHandler({}),NoRedirect()).open(Request(url,data=raw,headers=headers),timeout=timeout) as response:data=response.read(2_000_001)
        if len(data)>2_000_000:raise ValueError('Collector response exceeded 2 MB.')
        return json.loads(data)
    except HTTPError as e:
        if service=='hibp' and e.code==404:return []
        error=ConnectorUnavailable('Collector returned HTTP '+str(e.code)+'. Check access, rate limits and configuration; this is not a no-match result.')
        error.retry_after=min(3600,max(1,int(e.headers.get('Retry-After','60')))) if e.code==429 and str(e.headers.get('Retry-After','60')).isdigit() else 60
        error.http_status=e.code
        raise error from None
    except (URLError,TimeoutError,OSError):raise ConnectorUnavailable('Collector could not be reached. Check its local service or provider access.') from None
    except (json.JSONDecodeError,UnicodeError):raise ConnectorUnavailable('Collector returned unreadable JSON.') from None

class AdditionalCollectors:
    def __init__(self):
        self.lock=threading.RLock();self.enabled={x:False for x in ('hibp','harvester','maigret')};self.keys={x:'' for x in self.enabled}
        self.ports={'harvester':5000,'maigret':8001};self.counts={x:0 for x in self.enabled};self.next_hibp=0;self.cache={};self.pending={};self.cancelled=set();self.manager=None;self.managed=False
        self.harvester_manager=None
        self.quarantined_sites={}

    def status(self):
        with self.lock:return {**{k:{'enabled':self.enabled[k],'configured':bool(self.keys[k]),'port':self.ports.get(k),'session_requests':self.counts[k],'session_limit':100 if k=='hibp' else 20} for k in self.enabled},
                               'managed_maigret':self.manager.status() if self.manager else {'state':'stopped','running':False,'bundled':True},'hibp_attribution':HIBP_ATTRIBUTION,'harvester_sources':list(HARVESTER_SOURCES),'maigret_sites':list(MAIGRET_SITES)}

    def configure(self,p):
        with self.lock:
            keys=dict(self.keys);enabled=dict(self.enabled);ports=dict(self.ports)
            for kind in enabled:
                if kind+'_enabled' in p:
                    if type(p[kind+'_enabled']) is not bool:raise ValueError('Invalid collector enablement.')
                    enabled[kind]=p[kind+'_enabled']
                if kind+'_key' in p:
                    value=p[kind+'_key']
                    pattern=r'[A-Fa-f0-9]{32}' if kind=='hibp' else r'[A-Za-z0-9._~-]{16,256}'
                    if not isinstance(value,str) or (value and not re.fullmatch(pattern,value)):raise ValueError('Invalid '+kind+' API key format.')
                    keys[kind]=value
                if enabled[kind] and not keys[kind]:raise ValueError('Configure the '+kind+' key before enabling it.')
                if kind in ports and kind+'_port' in p:
                    value=p[kind+'_port']
                    if type(value) is not int or not 1024<=value<=65535:raise ValueError('Choose a valid loopback service port.')
                    ports[kind]=value
            if keys['hibp']!=self.keys['hibp']:self.cache.clear()
            self.keys=keys;self.enabled=enabled;self.ports=ports
        if 'maigret_key' in p:self.managed=False
        if self.harvester_manager and (not enabled['harvester'] or p.get('harvester_key')):
            self.harvester_manager.stop('harvester');self.harvester_manager=None
        if self.manager and (not enabled['maigret'] or not self.managed):self.manager.stop()
        return self.status()

    def setup_maigret(self):
        from managed_maigret import ManagedMaigret
        with self.lock:
            if self.manager is None:self.manager=ManagedMaigret()
            key,port=self.manager.ensure()
            self.keys['maigret']=key;self.ports['maigret']=port;self.enabled['maigret']=True;self.managed=True
        return self.status()

    def _access(self,kind):
        with self.lock:
            if not self.enabled[kind] or not self.keys[kind]:raise ConnectorUnavailable('Collector not configured: enable '+kind+' and its API key in Search connection.')
            if self.counts[kind]>=(100 if kind=='hibp' else 20):raise ConnectorUnavailable('Collector session limit reached.')
            return self.keys[kind],self.ports.get(kind)

    def hibp(self,email):
        if not isinstance(email,str) or len(email)>240 or not re.fullmatch(r'[^\s@/\\?#]+@[^\s@/\\?#]+\.[A-Za-z]{2,63}',email):raise ValueError('Enter a valid email address for HIBP.')
        email=email.casefold();key,_=self._access('hibp')
        if key=='0'*32 and not email.endswith('@hibp-integration-tests.com'):raise ValueError('The HIBP test key can only query reserved integration-test addresses.')
        with self.lock:
            cached=self.cache.get(email)
            if cached and time.monotonic()-cached[0]<900:return copy.deepcopy(cached[1])
            if time.monotonic()<self.next_hibp:raise ConnectorUnavailable('HIBP rate-limit cooldown is active. Wait and start a new report; no request was sent.')
            self.next_hibp=time.monotonic()+6;self.counts['hibp']+=1
        source='https://haveibeenpwned.com/api/v3/breachedaccount/'+quote(email,safe='')+'?truncateResponse=false&includeUnverified=false'
        try:data=transport(source,key=key)
        except ConnectorUnavailable as e:
            if getattr(e,'http_status',None)==429:
                with self.lock:self.next_hibp=time.monotonic()+e.retry_after
            raise
        if not isinstance(data,list) or any(not isinstance(b,dict) or not isinstance(b.get('Name'),str) for b in data):raise ValueError('HIBP returned an unexpected breach list.')
        rows=[]
        for breach in data[:100]:
            if breach.get('IsSensitive') or breach.get('IsRetired'):continue
            allowed={k:breach[k] for k in ('Name','Title','Domain','BreachDate','AddedDate','ModifiedDate','DataClasses','IsVerified','IsFabricated','IsSpamList','IsMalware') if k in breach}
            title=breach.get('Title') if isinstance(breach.get('Title'),str) else breach['Name']
            rows.append({'title':'HIBP exposure: '+title[:300],
                         'detail':json.dumps({'queried_email':email,'breach_metadata':allowed},ensure_ascii=False)+'\nSource: Have I Been Pwned (https://haveibeenpwned.com/), CC BY 4.0. Exposure metadata is not a password, proof of current compromise, or an identity match.',
                         'reference':'https://haveibeenpwned.com/','lead_only':True,'attribution':HIBP_ATTRIBUTION})
        report={'results':[{'provider':'Have I Been Pwned','status':'ok' if rows else 'empty','source':source,'message':'No public breach matches returned. This does not prove the address is safe or absent from all breaches.' if not rows else ('Showing up to 100 public breach records.' if len(data)>100 else 'Public breach metadata only; passwords and stealer logs are not retrieved.'),'rows':rows}],'links':[]}
        with self.lock:self.cache[email]=(time.monotonic(),copy.deepcopy(report))
        return report

    def _cancel_backend(self,kind,base,key,job):
        path='/api/v1/runs/'+job+'/cancel' if kind=='harvester' else '/api/cancel'
        try:transport(base+path,{} if kind=='harvester' else {'run_id':job},key,kind,timeout=5)
        except ValueError:pass

    def cancel(self,run_id):
        with self.lock:
            self.cancelled.add(run_id);pending=[(job,kind,base,key) for job,(owner,kind,base,key) in self.pending.items() if owner==run_id]
        for job,kind,base,key in pending:self._cancel_backend(kind,base,key,job)

    def harvester(self,domain,run_id,sources):
        from app import normalize
        if self.harvester_manager and self.enabled['harvester']:
            key,port=self.harvester_manager.ensure('harvester');self.keys['harvester']=key;self.ports['harvester']=port
        _,domain=normalize('domain',domain);sources=selected(sources,HARVESTER_SOURCES,4);key,port=self._access('harvester');base='http://127.0.0.1:'+str(port)
        catalog=transport(base+'/api/v1/sources',key=key,service='harvester')
        if not isinstance(catalog,dict) or not isinstance(catalog.get('sources'),list):raise ValueError('Local service is not a compatible HarvestView API.')
        available={s.get('name'):s for s in catalog['sources'] if isinstance(s,dict)}
        if any(s not in available or available[s].get('activity')!='P0' or available[s].get('ready') is not True for s in sources):raise ValueError('Selected theHarvester sources are unavailable, not ready, or not passive P0. No run was submitted.')
        request={'target':domain,'sources':sources,'limit':50,'source_workers':1,'deadline_seconds':60,
                 'dns_brute':False,'dns_lookup':False,'dns_resolve':False,'dns_recursive_depth':0,'routeviews':False,'shodan':False,'screenshot':False,'takeover':False,'api_scan':False,'vhost':False}
        with self.lock:
            if run_id in self.cancelled:raise ConnectorUnavailable('Investigation was cancelled before collector submission.')
            self.counts['harvester']+=1
        data=transport(base+'/api/v1/runs',request,key,'harvester');job=data.get('run_id') if isinstance(data,dict) else None
        if not isinstance(job,str) or not re.fullmatch('[A-Za-z0-9-]{1,80}',job):raise ValueError('theHarvester did not return a valid run ID.')
        with self.lock:self.pending[job]=(run_id,'harvester',base,key)
        deadline=time.monotonic()+90
        try:
            while True:
                if not isinstance(data,dict):raise ValueError('theHarvester returned unreadable run state.')
                if data.get('target')!=domain or set(data.get('sources',[]))!=set(sources) or set(data.get('activities',[]))!={'P0'}:
                    raise ValueError('theHarvester reported an unexpected target/source/activity scope. Cancellation requested.')
                with self.lock:cancelled=run_id in self.cancelled
                if cancelled or time.monotonic()>deadline:
                    self._cancel_backend('harvester',base,key,job)
                    # Retrieve retained partial evidence; never report a cancelled run as complete.
                    data=transport(base+'/api/v1/runs/'+job,key=key,service='harvester');data['status']='cancelled';break
                if data.get('status') in ('completed','failed','cancelled'):break
                if data.get('status') not in ('queued','running','cancelling'):raise ValueError('theHarvester returned an unknown run state.')
                time.sleep(.25);data=transport(base+'/api/v1/runs/'+job,key=key,service='harvester')
            items=data.get('results')
            if not isinstance(items,list):raise ValueError('theHarvester returned malformed result data.')
            rows=[]
            for item in items[:500]:
                if not isinstance(item,dict) or not isinstance(item.get('type'),str) or not isinstance(item.get('value'),str):raise ValueError('theHarvester returned a malformed finding.')
                rows.append({'title':'theHarvester · '+item['type']+' · '+item['value'][:300],
                             'detail':json.dumps({'type':item['type'],'value':item['value'],'sources':item.get('sources',[]),'run_id':job,'run_target':domain},ensure_ascii=False)+'\nDomain-relationship lead, not proof of person/account ownership.','reference':'','lead_only':True})
            partial=data.get('status')!='completed' or data.get('evidence_status')!='complete' or len(items)>500
            source=base+'/api/v1/runs/'+job
            result=[{'provider':'theHarvester','status':'partial' if partial else 'ok' if rows else 'empty','source':source,'rows':rows,'message':'Partial/limited evidence; review the retained run in HarvestView.' if partial else 'Passive P0 source results only.'}]
            for execution in data.get('source_executions',[]):
                if not isinstance(execution,dict):continue
                status=execution.get('status')
                if status not in ('completed','complete'):
                    result.append({'provider':'theHarvester source outcome','status':'error','source':source,'rows':[],'message':'An upstream source did not complete successfully; consult HarvestView for diagnostics.'})
            return {'results':result,'links':[]}
        except (ValueError,TypeError):
            self._cancel_backend('harvester',base,key,job);raise ValueError('theHarvester run could not complete within its reviewed contract. Cancellation requested; inspect the local service for retained evidence.') from None
        finally:
            with self.lock:self.pending.pop(job,None)

    def maigret(self,username,run_id,sites,ignore_health=False):
        import secrets
        username=username.removeprefix('@') if isinstance(username,str) else ''
        if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}',username):raise ValueError('Maigret requires a supplied handle, not an email, name or URL.')
        sites=selected(sites,MAIGRET_SITES,10)
        held=[] if ignore_health else [s for s in sites if s in self.quarantined_sites]
        held_checks=[{'site':s,'status':'Unknown','outcome':'unsupported','reason':'Checker disabled after a verified control mismatch; run a new public control before reuse.'} for s in held]
        sites=[s for s in sites if s not in held]
        if not sites:return {'results':[{'provider':'Maigret','status':'partial','rows':[],'checks':held_checks,'message':'Selected checker unavailable after control validation.'}],'links':[]}
        if self.manager and self.managed and self.enabled['maigret']:
            key,port=self.manager.ensure()
            with self.lock:self.keys['maigret']=key;self.ports['maigret']=port
        key,port=self._access('maigret');base='http://127.0.0.1:'+str(port)
        about=transport(base+'/api/about',key=key,service='maigret')
        if not isinstance(about,dict) or about.get('service')!='vidocq-maigret-bridge' or about.get('protocol')!=1:raise ValueError('Start the compatible Vidocq Maigret companion on this loopback port.')
        job=secrets.token_hex(12)
        with self.lock:
            if run_id in self.cancelled:raise ConnectorUnavailable('Investigation was cancelled before Maigret submission.')
            self.counts['maigret']+=1;self.pending[job]=(run_id,'maigret',base,key)
        try:
            data=transport(base+'/api/search',{'username':username,'sites':sites,'run_id':job},key,'maigret',timeout=90)
            if not isinstance(data,dict) or data.get('username')!=username or not isinstance(data.get('results'),list):raise ValueError('Maigret returned an unexpected username or result format.')
            rows=[];checks=[];failed=bool(data.get('cancelled')) or {i.get('site') for i in data['results'] if isinstance(i,dict)}!=set(sites)
            seen=set()
            for item in data['results']:
                if not isinstance(item,dict) or item.get('site') not in sites or item.get('status') not in ('Claimed','Available','Unknown','Illegal'):raise ValueError('Maigret returned out-of-scope data.')
                if item['site'] in seen:raise ValueError('Maigret returned duplicate site checks.')
                seen.add(item['site'])
                result_outcome=item.get('outcome',{'Claimed':'candidate','Available':'absent','Unknown':'unknown','Illegal':'invalid-handle'}[item['status']])
                if result_outcome not in ('candidate','absent','unknown','invalid-handle','unsupported','cancelled','timeout','blocked','error'):raise ValueError('Maigret returned an unknown diagnostic outcome.')
                reason={'candidate':'Matching account candidate; ownership not established.','absent':'No account detected; not proof of absence.','unknown':'No reliable result or diagnostic.','invalid-handle':'Handle unsupported by site.','unsupported':'Checker unavailable in reviewed database.','cancelled':'Check cancelled.','timeout':'Deadline exceeded.','blocked':'Access/challenge/rate restriction.','error':'Check failed.'}[result_outcome]
                checks.append({'site':item['site'],'status':item['status'],'outcome':result_outcome,'reason':reason,'diagnostics':{k:v for k,v in item.get('diagnostics',{}).items() if k in ('checked_at','error_type','maigret_version','checker_sha256','fresh_check','http_status') and isinstance(v,(str,int,bool))} if isinstance(item.get('diagnostics'),dict) else {}})
                if (item['status']=='Claimed' and result_outcome!='candidate') or (item['status']=='Available' and result_outcome!='absent'):raise ValueError('Maigret returned inconsistent site diagnostics.')
                failed=failed or result_outcome not in ('candidate','absent')
                if item['status']!='Claimed':continue
                url=str(item.get('url',''));p=urlparse(url)
                if p.scheme not in ('https','http') or p.hostname not in MAIGRET_SITES[item['site']] or p.username or p.password:raise ValueError('Maigret returned an out-of-scope profile reference.')
                rows.append({'title':'Maigret candidate · '+item['site']+' · '+username,'detail':json.dumps(item,ensure_ascii=False)+'\nPublic username check only. A matching handle is not proof of account ownership or common identity.','reference':url,'lead_only':True})
            for missing in set(sites)-seen:checks.append({'site':missing,'status':'Unknown','outcome':'unknown','reason':'Companion did not return this selected site.'})
            if held_checks:checks+=held_checks;failed=True
            return {'results':[{'provider':'Maigret','status':'partial' if failed else 'ok' if rows else 'empty','source':base+'/api/search','rows':rows,'checks':checks,'message':'Some checks were blocked, unavailable or cancelled; missing results are not proof of absent accounts.' if failed else 'Selected-site username checks; all candidates require review.'}],'links':[]}
        except ValueError:
            self._cancel_backend('maigret',base,key,job);raise
        finally:
            with self.lock:self.pending.pop(job,None)

CLIENT=AdditionalCollectors()
