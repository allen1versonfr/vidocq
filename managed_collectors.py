"""Lifecycle for independently licensed bundled collector processes."""
from run_control import read_bounded
from run_control import timeout as bounded_timeout
import atexit,hashlib,json,os,secrets,socket,subprocess,sys,threading,time
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from urllib.error import HTTPError,URLError
from local_drafts import NoRedirect
from managed_local_ai import WindowsJob,safe_path,digest
from child_environment import environment

class ManagedCollectors:
    def __init__(self,data,bundle=None):
        root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
        self.bundle=Path(bundle) if bundle else root/('assets/collectors' if getattr(sys,'frozen',False) else 'build/assets/collectors')
        self.data=Path(data);self.entries={};self.lifecycle=threading.RLock();atexit.register(self.stop)
    def manifest(self):
        try:
            p=safe_path(self.bundle/'manifest.json')
            if p.stat().st_size>10000:return {}
            v=json.loads(p.read_text(encoding='utf-8'));return v if isinstance(v,dict) else {}
        except (OSError,ValueError):return {}
    def status(self):
        manifest=self.manifest()
        return {kind:{'bundled':kind in manifest,'running':bool(self.entries.get(kind) and self.entries[kind]['process'].poll() is None),'commit':manifest.get(kind,{}).get('commit')} for kind in ('harvester','osintgram','photon')}
    def request(self,kind,path,payload=None,timeout=15):
        entry=self.entries.get(kind)
        if not entry:raise ValueError('Start the managed collector first.')
        allowed={'harvester':('/api/about','/api/v1/sources'),'osintgram':('/api/about','/api/run','/api/cancel','/api/auth/start','/api/auth/status','/api/auth/code','/api/auth/cancel','/api/auth/session'),'photon':('/api/about','/api/crawl')}
        if path not in allowed[kind]:raise ValueError('Unsupported managed endpoint.')
        headers={'Content-Type':'application/json',('X-API-Key' if kind=='harvester' else 'X-Vidocq-Key'):entry['key']}
        req=Request('http://127.0.0.1:'+str(entry['port'])+path,data=None if payload is None else json.dumps(payload).encode(),headers=headers)
        try:
            with build_opener(ProxyHandler({}),NoRedirect()).open(req,timeout=bounded_timeout(timeout)) as response:
                raw=read_bounded(response,2_000_000)
                if len(raw)>2_000_000:raise ValueError('Collector response exceeds 2 MB.')
                return json.loads(raw)
        except HTTPError as e:
            try:
                error=json.loads(e.read(2000));message=error.get('error') or error.get('detail')
                if not isinstance(message,str):message='The collector rejected the request.'
            except (ValueError,OSError):message='The collector could not complete the request.'
            raise ValueError(kind+' HTTP '+str(e.code)+': '+message[:300]) from None
        except (URLError,TimeoutError,OSError):raise ValueError('The local '+kind+' service is unavailable or timed out. Review setup status.') from None
    def ensure(self,kind,credentials=None):
        if kind not in ('harvester','osintgram','photon'):raise ValueError('Unsupported managed collector.')
        with self.lifecycle:
            if kind in self.entries and self.entries[kind]['process'].poll() is None:return self.entries[kind]['key'],self.entries[kind]['port']
            self.stop(kind);manifest=self.manifest();spec=manifest.get(kind)
            if not isinstance(spec,dict):raise ValueError('This build has no bundled '+kind+' companion. Install the current Windows release.')
            executable=safe_path(self.bundle/(kind+'.exe'))
            if executable.stat().st_size!=spec.get('size') or digest(executable)!=spec.get('sha256'):raise ValueError('Bundled collector integrity check failed; reinstall Vidocq.')
            if kind=='osintgram' and (not credentials or not (credentials.get('hiker_key') or credentials.get('backend')=='instagrapi')):raise ValueError('Save your provider key or connect an operator session first.')
            data=safe_path(self.data/kind);data.mkdir(parents=True,exist_ok=True)
            with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
            key=secrets.token_urlsafe(32);env=environment()
            env.update(VIDOCQ_COMPANION_KEY=key,THEHARVESTER_API_KEY=key,PYINSTALLER_RESET_ENVIRONMENT='1')
            process=subprocess.Popen([str(executable),'--port',str(port),'--data',str(data)],env=env,cwd=data,stdin=subprocess.PIPE if kind=='osintgram' else subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            self.entries[kind]={'process':process,'port':port,'key':key,'job':None}
            try:
                self.entries[kind]['job']=WindowsJob(process)
                if kind=='osintgram':process.stdin.write(json.dumps(credentials).encode()+b'\n');process.stdin.close()
                deadline=time.monotonic()+60
                while time.monotonic()<deadline and process.poll() is None:
                    try:
                        about=self.request(kind,'/api/about')
                        if about.get('service')=='vidocq-'+kind and about.get('protocol')==1:return key,port
                    except (ValueError,OSError):pass
                    time.sleep(.2)
                raise ValueError('The managed '+kind+' companion did not start. Check the setup status or reinstall this release.')
            except Exception:self.stop(kind);raise
    def stop(self,kind=None):
        with self.lifecycle:
            for name in list(self.entries) if kind is None else [kind]:
                entry=self.entries.pop(name,None)
                if not entry:continue
                if entry['job']:entry['job'].close()
                process=entry['process']
                if process.poll() is None:
                    process.terminate()
                    try:process.wait(timeout=5)
                    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
