"""Persist opt-in service choices; startup never runs a target investigation."""
import json,threading
from pathlib import Path
from credential_vault import Vault
from managed_collectors import ManagedCollectors
from managed_local_ai import safe_path

class AutomationSetup:
    def __init__(self,data,web,collectors,connectors,ai):
        self.path=Path(data)/'automations.json';self.search_path=Path(data)/'search-connection.json';self.vault=Vault(data);self.manager=ManagedCollectors(data)
        self.web,self.collectors,self.connectors,self.ai=web,collectors,connectors,ai
        self.choices={k:False for k in ('mwmbl','maigret','harvester','photon','osintgram')};self.worker=None;self.messages={};self.lock=threading.RLock()
        try:
            if safe_path(self.path).is_file() and self.path.stat().st_size<4000:
                saved=json.loads(self.path.read_text(encoding='utf-8'))
                if isinstance(saved,dict):self.choices.update({k:v for k,v in saved.items() if k in self.choices and type(v) is bool})
        except (ValueError,OSError):self.messages['settings']='Saved setup choices could not be read.'
    def status(self):
        credentials=self.vault.status()
        return {'configured':self.path.exists(),'choices':dict(self.choices),'busy':bool(self.worker and self.worker.is_alive()),'services':self.manager.status(),'messages':dict(self.messages),'credentials':credentials,'needs_osintgram_credentials':(self.choices['osintgram'] or not self.path.exists()) and (not credentials['saved'] or credentials['locked']),'llm':self.ai.status(),'notice':'Services start without target queries. Cases still require source permissions. Osintgram uses your saved encrypted operator session or provider key; paid backend charges can apply.'}
    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True);p=safe_path(self.path.with_name('automations.json.part'));p.write_text(json.dumps(self.choices),encoding='utf-8');p.replace(safe_path(self.path))
    def apply(self,p):
        if p.get('consent') is not True:raise ValueError('Approve starting the selected local tools and enabling the free index.')
        if any(type(p.get(k,False)) is not bool for k in self.choices):raise ValueError('Invalid setup choice.')
        with self.lock:
            if self.worker and self.worker.is_alive():raise ValueError('Setup is already running.')
            if self.choices['mwmbl'] and not p.get('mwmbl') and self.web.status().get('provider')=='mwmbl':self.web.configure({'provider':'mwmbl','enabled':False})
            self.choices={k:p.get(k,False) for k in self.choices};self.save();self.start()
        if p.get('download_ai') is True:self.ai.setup(True,p.get('backend','vulkan'))
        return self.status()
    def start(self):
        if self.worker and self.worker.is_alive():return
        self.worker=threading.Thread(target=self._start,daemon=True);self.worker.start()
    def _start(self):
        if self.choices['mwmbl']:self.web.configure({'provider':'mwmbl','enabled':True});self.messages['mwmbl']='Free anonymous web search enabled. Major-index browser fallback is also available.'
        try:
            if safe_path(self.search_path).is_file() and self.search_path.stat().st_size<4000:
                prefs=json.loads(self.search_path.read_text(encoding='utf-8'));provider=prefs.get('provider')
                if provider not in ('serper','serpapi'):raise ValueError('Invalid saved search provider.')
                self.web.configure({**prefs,'key':self.vault.search_key(provider)})
        except (OSError,ValueError):self.messages['search']='Saved search connection could not be restored. Enter its key in Search connection.'
        for kind in ('maigret','harvester','photon','osintgram'):
            try:
                if not self.choices[kind]:
                    if kind=='maigret':self.collectors.configure({'maigret_enabled':False})
                    if kind!='maigret':self.manager.stop(kind)
                    if kind=='harvester':self.collectors.enabled['harvester']=False
                    if kind=='osintgram':self.connectors.osintgram_enabled=False
                    continue
                self.messages[kind]='Starting local service…'
                if kind=='maigret':self.collectors.setup_maigret()
                elif kind=='harvester':
                    key,port=self.manager.ensure(kind);self.collectors.keys[kind]=key;self.collectors.ports[kind]=port;self.collectors.enabled[kind]=True
                    self.collectors.harvester_manager=self.manager
                    catalog=self.manager.request(kind,'/api/v1/sources');self.messages['harvester_sources']=[{'name':s['name'],'ready':s['ready'],'credentials':s.get('credentials',[])} for s in catalog['sources'] if s['name'] in ('crtsh','certspotter','duckduckgo','otx','urlscan','github-code','rapiddns')]
                elif kind=='osintgram':
                    credentials=self.vault.osintgram()
                    if not (credentials.get('hiker_key') or credentials.get('session')):self.messages[kind]='Connect your operator session or enter a HikerAPI key to finish setup.';continue
                    key,port=self.manager.ensure(kind,credentials);self.connectors.port=port;self.connectors.osintgram_enabled=True;self.connectors.managed_key=key;self.connectors.managed_manager=self.manager;self.connectors.managed_vault=self.vault
                else:self.manager.ensure(kind)
                self.messages[kind]='Ready. No target lookup ran during setup.'
            except Exception as e:self.messages[kind]=str(e) if isinstance(e,ValueError) else 'Service setup failed. Check the current Windows build and credential status.'
    def credentials(self,p):
        if self.worker and self.worker.is_alive():raise ValueError('Wait for automatic setup to finish before changing credentials.')
        if p.get('forget') is True:
            self.manager.stop('osintgram');self.connectors.osintgram_enabled=False;return self.vault.forget_osintgram()
        result=self.vault.save(p.get('hiker_key'));self.manager.stop('osintgram');self.choices['osintgram']=True;self.save()
        self.start();return result
    def search(self,p):
        provider=p.get('provider',self.web.provider);payload=dict(p)
        if provider in ('serper','serpapi') and 'key' not in payload:payload['key']=self.vault.search_key(provider) or self.web.other_keys.get(provider,'')
        state=self.web.configure(payload)
        if provider in ('serper','serpapi') and p.get('remember') is True:
            self.vault.save_search(provider,payload.get('key',''));prefs={'provider':provider,'enabled':state['enabled'],'session_limit':state['session_limit']}
            temp=safe_path(self.search_path.with_name('search-connection.json.part'));temp.write_text(json.dumps(prefs),encoding='utf-8');temp.replace(safe_path(self.search_path))
        if p.get('forget_saved') is True:
            if provider in ('serper','serpapi'):self.vault.save_search(provider,'')
            safe_path(self.search_path).unlink(missing_ok=True)
        return state
    def stop(self):self.manager.stop()
