"""User-triggered browser capture relay. Incoming evidence always awaits review."""
import json,os,re,secrets,sys,threading,time
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from urllib.request import Request,build_opener,ProxyHandler
from local_drafts import NoRedirect
from managed_local_ai import safe_path

SCHEME='vidocq-evidence'
def parse_capture(uri):
    if not isinstance(uri,str) or len(uri)>26000:raise ValueError('Capture is too large; select a smaller excerpt.')
    p=urlparse(uri)
    if p.scheme!=SCHEME or p.netloc!='capture':raise ValueError('Invalid browser capture URI.')
    value=json.loads(parse_qs(p.query).get('data',[''])[0])
    if not isinstance(value,dict) or not re.fullmatch('[0-9a-f]{24}',value.get('case_id','')) or not isinstance(value.get('data'),dict):raise ValueError('Invalid browser capture.')
    from discovery_tools import import_links
    import_links({'mode':'browser','data':value['data']})
    return value

def relay_to_running(uri,data):
    capture=parse_capture(uri)
    try:
        p=safe_path(Path(data)/'browser-relay.json')
        if p.stat().st_size>2000:return False
        state=json.loads(p.read_text(encoding='utf-8'));port=state['port'];key=state['key']
        if type(port) is not int or not 1024<=port<=65535 or not isinstance(key,str) or not re.fullmatch('[A-Za-z0-9_-]{30,100}',key):return False
        request=Request('http://127.0.0.1:'+str(port)+'/api/browser-relay',data=json.dumps(capture).encode(),headers={'Content-Type':'application/json','X-Vidocq-Relay':key})
        with build_opener(ProxyHandler({}),NoRedirect()).open(request,timeout=3) as response:return response.status==202
    except (OSError,ValueError,KeyError):return False

class BrowserBridge:
    def __init__(self,data):self.data=Path(data);self.key=secrets.token_urlsafe(32);self.pending=[];self.lock=threading.RLock()
    def publish(self,port):
        self.data.mkdir(parents=True,exist_ok=True);safe_path(self.data/'browser-relay.json').write_text(json.dumps({'port':port,'key':self.key,'pid':os.getpid()}),encoding='utf-8')
    def receive(self,p):
        from discovery_tools import import_links
        if not isinstance(p,dict) or not re.fullmatch('[0-9a-f]{24}',p.get('case_id','')):raise ValueError('Invalid capture case.')
        import_links({'mode':'browser','data':p.get('data')})
        with self.lock:
            self.pending=[x for x in self.pending if time.monotonic()-x['created']<600]
            if len(self.pending)>=10:raise ValueError('Review pending browser captures first.')
            self.pending.append({'id':secrets.token_hex(12),'created':time.monotonic(),'case_id':p['case_id'],'data':p['data']})
        return {'queued':True,'notice':'Review and approve this capture inside Vidocq before it enters a case.'}
    def list(self):
        with self.lock:return [{k:v for k,v in x.items() if k!='created'} for x in self.pending if time.monotonic()-x['created']<600]
    def peek(self,key):
        with self.lock:
            item=next((x for x in self.pending if x['id']==key and time.monotonic()-x['created']<600),None)
            if not item:raise ValueError('Capture expired or already reviewed.')
            return item
    def pop(self,key):
        with self.lock:
            item=self.peek(key);self.pending.remove(item);return item
    def close(self):
        p=safe_path(self.data/'browser-relay.json')
        try:
            if json.loads(p.read_text(encoding='utf-8')).get('key')==self.key:p.unlink()
        except (OSError,ValueError):pass

def register(executable=None,scheme=SCHEME):
    if os.name!='nt' or (executable is None and not getattr(sys,'frozen',False)):raise ValueError('Browser integration registration requires the Windows executable.')
    if not re.fullmatch('[a-z][a-z0-9-]{3,60}',scheme):raise ValueError('Invalid helper scheme.')
    import winreg
    path='Software\\Classes\\'+scheme;exe=str(Path(executable or sys.executable).resolve())
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,path) as key:
            if winreg.QueryValueEx(key,'VidocqOwner')[0]!='Vidocq':raise ValueError('This browser helper scheme belongs to another application.')
    except FileNotFoundError:pass
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,path) as key:
        winreg.SetValueEx(key,'',0,winreg.REG_SZ,'URL:Vidocq reviewed evidence');winreg.SetValueEx(key,'URL Protocol',0,winreg.REG_SZ,'');winreg.SetValueEx(key,'VidocqOwner',0,winreg.REG_SZ,'Vidocq')
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,path+'\\shell\\open\\command') as key:winreg.SetValueEx(key,'',0,winreg.REG_SZ,'"'+exe+'" --browser-capture "%1"')
    return {'registered':True,'notice':'Use the generated capture bookmark or browser helper. Chrome/Firefox may ask you to approve opening Vidocq; Vidocq does not bypass browser approval.'}

def unregister(executable=None,scheme=SCHEME):
    if os.name!='nt':return
    import winreg
    path='Software\\Classes\\'+scheme;exe=str(Path(executable or sys.executable).resolve())
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,path) as key:
            if winreg.QueryValueEx(key,'VidocqOwner')[0]!='Vidocq':return
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,path+'\\shell\\open\\command') as key:
            if winreg.QueryValueEx(key,'')[0]!='"'+exe+'" --browser-capture "%1"':return
        for suffix in ('\\shell\\open\\command','\\shell\\open','\\shell',''):winreg.DeleteKey(winreg.HKEY_CURRENT_USER,path+suffix)
    except FileNotFoundError:pass
