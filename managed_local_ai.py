"""Opt-in, pinned local AI installer and authenticated on-demand runtime."""
from run_control import read_bounded
import atexit
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import threading
import time
from urllib.parse import urlparse
from urllib.request import Request,build_opener,HTTPRedirectHandler,ProxyHandler
from zipfile import ZipFile
from local_ai_assets import MODEL,RUNTIME,RUNTIME_FILES
from child_environment import environment
from run_control import timeout

HOSTS={'huggingface.co','us.aws.cdn.hf.co','eu.aws.cdn.hf.co','cas-bridge.xethub.hf.co','cdn-lfs.hf.co','cdn-lfs-us-1.hf.co','github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'}


def checked_url(url):
    p=urlparse(url)
    if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None,443):raise ValueError('AI download left the approved upstream hosts.')
    return url


class Redirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        checked_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def safe_path(path):
    path=Path(path).absolute()
    for node in (path,*path.parents):
        if node.is_symlink() or (node.exists() and getattr(node.stat(follow_symlinks=False),'st_file_attributes',0)&0x400):raise ValueError('Local AI refuses symbolic links and reparse points.')
    return path


def digest(path,cancel=None):
    value=hashlib.sha256()
    with safe_path(path).open('rb') as stream:
        while block:=stream.read(4*1024*1024):
            timeout()
            if cancel and cancel.is_set():raise ValueError('Setup cancelled; verified existing files are preserved.')
            value.update(block)
    return value.hexdigest()


def download(spec,path,cancel,progress,opener=None):
    path=safe_path(path);part=safe_path(path.with_name(path.name+'.part'))
    if path.is_file() and path.stat().st_size==spec['size'] and digest(path,cancel)==spec['sha256']:return
    offset=part.stat().st_size if part.is_file() else 0
    if offset>spec['size']:part.unlink();offset=0
    if offset<spec['size']:
        opener=opener or build_opener(ProxyHandler({}),Redirect())
        headers={'User-Agent':'Vidocq-Local-AI-Setup','Accept-Encoding':'identity'}
        if offset:headers['Range']='bytes='+str(offset)+'-'
        with opener.open(Request(checked_url(spec['url']),headers=headers),timeout=30) as response:
            checked_url(response.url)
            if offset and response.status==206:
                match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',response.headers.get('Content-Range',''))
                if not match or int(match[1])!=offset or int(match[2])!=spec['size']-1 or int(match[3])!=spec['size']:raise ValueError('Invalid AI download resume response.')
            elif response.status==200:offset=0
            else:raise ValueError('AI download did not return the requested file.')
            with part.open('ab' if offset else 'wb') as stream:
                while block:=response.read(1024*1024):
                    if cancel.is_set():raise ValueError('Setup cancelled; partial download retained for retry.')
                    offset+=len(block)
                    if offset>spec['size']:raise ValueError('AI download exceeded the pinned size.')
                    stream.write(block);progress(offset,spec['size'])
    if not part.is_file() or part.stat().st_size!=spec['size']:raise ValueError('Incomplete AI download; retry resumes the partial file.')
    progress(spec['size'],spec['size'])
    if digest(part,cancel)!=spec['sha256']:
        part.unlink();raise ValueError('AI checksum mismatch; unverified download removed and never executed.')
    os.replace(part,path)


def extract_runtime(archive,folder):
    folder=safe_path(folder);folder.mkdir(parents=True,exist_ok=True)
    with ZipFile(safe_path(archive)) as z:
        entries=z.infolist()
        if len({x.filename for x in entries})!=len(entries):raise ValueError('Duplicate runtime archive entries.')
        lookup={x.filename:x for x in entries}
        for name,spec in RUNTIME_FILES.items():
            item=lookup.get(name)
            if item is None or item.file_size!=spec['size'] or item.external_attr>>16&0o170000==0o120000:raise ValueError('Unexpected runtime archive contents.')
            data=z.read(item)
            if hashlib.sha256(data).hexdigest()!=spec['sha256']:raise ValueError('Runtime member checksum mismatch.')
            target=safe_path(folder/name);part=safe_path(folder/(name+'.part'))
            part.write_bytes(data);os.replace(part,target)


def owned_ai_files():
    return ['local-ai/runtime.zip','local-ai/runtime.zip.part','local-ai/installed.json','local-ai/installed.json.part',
            'local-ai/'+MODEL['filename'],'local-ai/'+MODEL['filename']+'.part']+['local-ai/runtime/'+name+suffix for name in RUNTIME_FILES for suffix in ('','.part')]


class WindowsJob:
    """Kill runtime descendants even when the app is forcibly closed."""
    def __init__(self,process):
        if os.name!='nt':self.handle=None;return
        import ctypes
        from ctypes import wintypes as w
        class BASIC(ctypes.Structure):
            _fields_=[('time1',ctypes.c_int64),('time2',ctypes.c_int64),('flags',w.DWORD),('min',ctypes.c_size_t),('max',ctypes.c_size_t),('count',w.DWORD),('affinity',ctypes.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]
        class IO(ctypes.Structure):_fields_=[(n,ctypes.c_uint64) for n in ('r','w','o','rb','wb','ob')]
        class LIMIT(ctypes.Structure):_fields_=[('basic',BASIC),('io',IO),('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,w.LPCWSTR];self.kernel.CreateJobObjectW.restype=w.HANDLE
        self.kernel.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD]
        self.kernel.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]
        self.kernel.CloseHandle.argtypes=[w.HANDLE]
        self.handle=self.kernel.CreateJobObjectW(None,None);limit=LIMIT();limit.basic.flags=0x2000
        if not self.handle or not self.kernel.SetInformationJobObject(self.handle,9,ctypes.byref(limit),ctypes.sizeof(limit)) or not self.kernel.AssignProcessToJobObject(self.handle,w.HANDLE(int(process._handle))):
            self.close();raise ValueError('Could not attach the local runtime to app lifecycle protection.')
    def close(self):
        if self.handle:self.kernel.CloseHandle(self.handle);self.handle=None


class ManagedLocalAI:
    def __init__(self,data):
        self.data=safe_path(data);self.root=self.data/'local-ai';self.settings_path=self.data/'local-ai.json'
        self.lock=threading.RLock();self.lifecycle=threading.RLock();self.worker=None;self.cancelled=threading.Event();self.process=None;self.job=None;self.port=None;self.key=''
        self.phase='idle';self.message='Optional local AI is not installed.';self.received=0;self.total=0;self.backend_used=None
        self.settings={'enabled':False,'backend':'vulkan'}
        try:
            if safe_path(self.settings_path).is_file() and self.settings_path.stat().st_size<4096:
                saved=json.loads(self.settings_path.read_text(encoding='utf-8'))
                if isinstance(saved,dict) and type(saved.get('enabled')) is bool and saved.get('backend') in ('vulkan','cpu'):self.settings={k:saved[k] for k in ('enabled','backend')}
        except (ValueError,OSError):self.message='Saved AI settings could not be read; setup is disabled.'
        if self.installed():self.phase='installed';self.message='Local AI is installed. It loads on your next approved draft when enabled.'
        atexit.register(self.stop)
    @property
    def busy(self):return bool(self.worker and self.worker.is_alive())
    @property
    def enabled(self):return self.settings['enabled']
    def installed(self):
        try:
            if safe_path(self.root/'installed.json').stat().st_size>4096:return False
            manifest=json.loads(safe_path(self.root/'installed.json').read_text(encoding='utf-8'))
            return isinstance(manifest,dict) and manifest.get('model_sha256')==MODEL['sha256'] and manifest.get('runtime_sha256')==RUNTIME['sha256'] and safe_path(self.root/MODEL['filename']).stat().st_size==MODEL['size'] and all(safe_path(self.root/'runtime'/n).stat().st_size==s['size'] for n,s in RUNTIME_FILES.items())
        except (ValueError,OSError):return False
    def status(self):
        with self.lock:
            running=bool(self.process and self.process.poll() is None)
            return {'supported':os.name=='nt','installed':self.installed(),'enabled':self.enabled,'running':running,'busy':self.busy,'phase':self.phase,'message':self.message,'received':self.received,'total':self.total,'backend':self.settings['backend'],'backend_used':self.backend_used,'model':MODEL['name'],'model_bytes':MODEL['size'],'runtime_version':RUNTIME['version'],'download_bytes':MODEL['size']+RUNTIME['size'],'task_contract':getattr(self,'contract_check',{'tested':False,'passed':False}),'directory':str(self.root),'port':self.port if running else None,'notice':'Optional pinned downloads from GitHub and Hugging Face. Installation survives app updates. Inference is local, authenticated and starts on demand; no cloud fallback.'}
    def _save(self):
        safe_path(self.data).mkdir(parents=True,exist_ok=True)
        part=safe_path(self.settings_path.with_name('local-ai.json.part'));part.write_text(json.dumps(self.settings),encoding='utf-8');os.replace(part,safe_path(self.settings_path))
    def set_enabled(self,enabled,backend=None):
        if type(enabled) is not bool or backend not in (None,'vulkan','cpu'):raise ValueError('Choose enabled/disabled and Vulkan or CPU.')
        with self.lock:
            if self.busy:raise ValueError('Wait for setup or cancel it before changing AI settings.')
            if enabled and not self.installed():raise ValueError('Install the recommended local AI first.')
            self.stop();self.cancelled.clear();self.settings={'enabled':enabled,'backend':backend or self.settings['backend']};self._save()
            self.phase='installed' if self.installed() else 'idle';self.message='Local AI enabled; loads on your next approved draft.' if enabled else 'Local AI disabled. Installed files are preserved.'
        return self.status()
    def setup(self,consent=False,backend='vulkan'):
        if consent is not True:raise ValueError('Approve the approximately 2.54 GB runtime/model download and upstream licenses.')
        if os.name!='nt':raise ValueError('Automatic local AI setup currently supports Windows x64 only.')
        if backend not in ('vulkan','cpu'):raise ValueError('Choose Vulkan or CPU.')
        with self.lock:
            if self.busy:raise ValueError('Local AI setup is already running.')
            self.stop();self.cancelled.clear();self.phase='preparing';self.message='Preparing local AI setup.';self.received=0;self.total=0
            self.worker=threading.Thread(target=self._install,args=(backend,),daemon=True);self.worker.start()
        return self.status()
    def cancel(self):
        self.cancelled.set()
        with self.lock:self.message='Cancellation requested; waiting for the current network/startup operation to stop.'
        return self.status()
    def _progress(self,received,total):
        with self.lock:self.received=received;self.total=total
    def _install(self,backend):
        try:
            safe_path(self.root).mkdir(parents=True,exist_ok=True)
            missing=max(0,MODEL['size']-(self.root/(MODEL['filename']+'.part')).stat().st_size) if (self.root/(MODEL['filename']+'.part')).is_file() else (0 if self.installed() else MODEL['size'])
            if shutil.disk_usage(self.root).free<missing+400_000_000:raise ValueError('Not enough disk space; allow about 3 GB for local AI setup.')
            for name,spec,path in [('runtime',RUNTIME,self.root/'runtime.zip'),('model',MODEL,self.root/MODEL['filename'])]:
                with self.lock:self.phase='downloading-'+name;self.message='Downloading/verifying '+name+'. Retry resumes an incomplete download.'
                download(spec,path,self.cancelled,self._progress)
                if name=='runtime':extract_runtime(path,self.root/'runtime')
            if self.cancelled.is_set():raise ValueError('Setup cancelled. Verified downloads are preserved.')
            part=safe_path(self.root/'installed.json.part');part.write_text(json.dumps({'model_sha256':MODEL['sha256'],'runtime_sha256':RUNTIME['sha256']}),encoding='utf-8');os.replace(part,safe_path(self.root/'installed.json'))
            with self.lock:
                self.settings={'enabled':True,'backend':backend};self._save();self.phase='checking';self.message='Starting local AI and checking a synthetic response (no case data).'
            port,key=self.ensure(internal=True)
            result=self._request(port,key,'/v1/chat/completions',{'model':'vidocq-qwen3-4b','messages':[{'role':'system','content':'Return only JSON.'},{'role':'user','content':'Return {"ok": true}.'}],'temperature':0,'max_tokens':32,'response_format':{'type':'json_object'}})
            if json.loads(result['choices'][0]['message']['content']).get('ok') is not True:raise ValueError('Local model did not pass its synthetic setup check.')
            self.contract_check={'tested':True,'passed':False}
            try:
                check=self._request(port,key,'/v1/chat/completions',{'model':'vidocq-qwen3-4b','messages':[{'role':'system','content':'Select IDs only. Return JSON.'},{'role':'user','content':'Excerpt IDs: R001-S1 is a public biography; R002-S1 is an unrelated menu. Return {"selection_ids":["R001-S1"]}.'}],'temperature':0,'max_tokens':64,'response_format':{'type':'json_object'}})
                self.contract_check['passed']=json.loads(check['choices'][0]['message']['content']).get('selection_ids')==['R001-S1']
            except (ValueError,KeyError,TypeError):pass
            if self.cancelled.is_set():raise ValueError('Setup cancelled. Verified files are preserved.')
            self.stop()
            with self.lock:self.phase='ready';self.message='Local AI installed and checked. Updates reuse these files. '+('CPU fallback is active.' if self.backend_used=='cpu' and backend=='vulkan' else 'Vulkan acceleration selected.' if backend=='vulkan' else 'CPU mode selected.')
        except Exception as e:
            self.stop()
            with self.lock:
                self.phase='cancelled' if self.cancelled.is_set() else 'failed';self.message=str(e)[:350] if isinstance(e,ValueError) else 'Local AI setup failed. Retry to reuse verified files and resume partial downloads.'
                self.settings['enabled']=False
                try:self._save()
                except OSError:pass
    def _request(self,port,key,path,payload=None):
        opener=build_opener(ProxyHandler({}),NoLocalRedirect())
        headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'}
        with opener.open(Request('http://127.0.0.1:'+str(port)+path,data=None if payload is None else json.dumps(payload).encode(),headers=headers),timeout=timeout(45)) as response:
            raw=read_bounded(response,64000)
            if len(raw)>64000:raise ValueError('Local model response too large.')
            return json.loads(raw)
    def ensure(self,internal=False):
        with self.lifecycle:
            if self.busy and not internal:raise ValueError('Local AI setup is still running.')
            if not self.enabled or not self.installed():raise ValueError('Install and enable local AI first.')
            if self.process and self.process.poll() is None:return self.port,self.key
            self.stop();runtime=safe_path(self.root/'runtime')
            unexpected=[p.name for p in runtime.iterdir() if p.suffix.lower() in ('.dll','.exe') and p.name not in RUNTIME_FILES]
            if unexpected:raise ValueError('Unexpected executable files in managed runtime; repair installation before starting.')
            for name,spec in RUNTIME_FILES.items():
                if digest(runtime/name)!=spec['sha256']:raise ValueError('Runtime integrity check failed; run setup to repair it.')
            if digest(self.root/MODEL['filename'])!=MODEL['sha256']:raise ValueError('Model integrity check failed; run setup to repair it.')
            modes=['vulkan','cpu'] if self.settings['backend']=='vulkan' else ['cpu']
            for mode in modes:
                timeout()
                if self.cancelled.is_set():raise ValueError('Setup cancelled.')
                with socket.socket() as listener:listener.bind(('127.0.0.1',0));self.port=listener.getsockname()[1]
                self.key=secrets.token_urlsafe(32)
                command=[str(runtime/'llama-server.exe'),'-m',str(self.root/MODEL['filename']),'--host','127.0.0.1','--port',str(self.port),'--alias','vidocq-qwen3-4b','-c','8192','-np','1','-ngl','99' if mode=='vulkan' else '0','--offline','--no-webui','--log-disable']
                if mode=='cpu':command+=['--device','none']
                env=environment({'LLAMA_API_KEY':self.key})
                self.process=subprocess.Popen(command,cwd=runtime,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                try:
                    self.job=WindowsJob(self.process);deadline=time.monotonic()+75
                    while time.monotonic()<deadline and not self.cancelled.is_set() and self.process.poll() is None:
                        timeout()
                        try:
                            if self._request(self.port,self.key,'/health').get('status')=='ok':self.backend_used=mode;return self.port,self.key
                        except (ValueError,OSError):pass
                        time.sleep(.3)
                except Exception:
                    self.stop();raise
                self.stop()
            raise ValueError('Neither Vulkan nor CPU runtime started. Check driver/Windows runtime support, then retry setup. No cloud fallback was used.')
    def stop(self):
        with self.lifecycle:
            process=self.process;self.process=None
            if self.job:self.job.close();self.job=None
            if process and process.poll() is None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            self.key='';self.port=None


class NoLocalRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Local AI redirects are disabled.')
