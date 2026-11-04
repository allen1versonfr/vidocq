"""Windows-user-bound DPAPI storage. No plaintext fallback or secret read API."""
import ctypes,json,os,threading
from pathlib import Path
from managed_local_ai import safe_path

def protect(value,decrypt=False):
    if os.name!='nt':raise ValueError('Saved credentials require Windows DPAPI; no plaintext fallback is used.')
    from ctypes import wintypes as w
    class Blob(ctypes.Structure):_fields_=[('size',w.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    raw=ctypes.create_string_buffer(value);source=Blob(len(value),ctypes.cast(raw,ctypes.POINTER(ctypes.c_ubyte)));out=Blob()
    library=ctypes.WinDLL('crypt32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    call=library.CryptUnprotectData if decrypt else library.CryptProtectData
    call.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,w.DWORD,ctypes.POINTER(Blob)];call.restype=w.BOOL
    kernel.LocalFree.argtypes=[ctypes.c_void_p]
    if not call(ctypes.byref(source),None,None,None,None,1,ctypes.byref(out)):raise ValueError('Windows could not unlock/save this credential for the current user.')
    try:return ctypes.string_at(out.data,out.size)
    finally:kernel.LocalFree(out.data)

class Vault:
    def __init__(self,data):self.path=Path(data)/'credentials.dpapi';self.lock=threading.RLock()
    def load(self):
        if not safe_path(self.path).is_file():return {}
        if self.path.stat().st_size>400000:raise ValueError('Credential store is invalid.')
        value=json.loads(protect(self.path.read_bytes(),True))
        if not isinstance(value,dict):raise ValueError('Credential store is invalid.')
        return value
    def status(self):
        try:
            value=self.load();backend=value.get('backend','hikerapi');invalid=bool(value.get('instagram',{}).get('needs_reconnect'));ready=bool(value.get('instagram',{}).get('session')) and not invalid if backend=='instagrapi' else bool(value.get('hiker_key'))
            return {'saved':ready,'locked':False,'backend':backend,'instagram_saved':bool(value.get('instagram',{}).get('session')),'instagram_needs_reconnect':invalid,'search_providers':sorted(value.get('search_keys',{}))}
        except (ValueError,OSError):return {'saved':True,'locked':True,'backend':'locked','instagram_saved':False,'search_providers':[]}
    def write(self,value):
        with self.lock:
            payload=protect(json.dumps(value).encode())
            if len(payload)>400000:raise ValueError('Credential store exceeds its size limit.')
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temp=safe_path(self.path.with_name('credentials.dpapi.part'));temp.write_bytes(payload);os.replace(temp,safe_path(self.path))
    def save(self,key):
        if not isinstance(key,str) or not 10<=len(key)<=1024 or any(ord(c)<33 for c in key):raise ValueError('Enter your HikerAPI key.')
        with self.lock:value=self.load();value.update(hiker_key=key,backend='hikerapi');self.write(value)
        return self.status()
    def save_instagram(self,username,session):
        if not isinstance(username,str) or not isinstance(session,dict) or len(json.dumps(session))>200000:raise ValueError('Invalid saved Instagram session.')
        with self.lock:value=self.load();value.update(backend='instagrapi',instagram={'username':username,'session':session});self.write(value)
        return self.status()
    def osintgram(self):
        value=self.load()
        if value.get('backend')=='instagrapi':return {'backend':'instagrapi',**value.get('instagram',{})}
        return {'backend':'hikerapi','hiker_key':value.get('hiker_key','')}
    def search_key(self,provider):return self.load().get('search_keys',{}).get(provider,'')
    def save_search(self,provider,key):
        if provider not in ('serper','serpapi') or not isinstance(key,str) or len(key)>500 or (key and any(not (c.isascii() and (c.isalnum() or c in '._-')) for c in key)):raise ValueError('Invalid search provider key.')
        with self.lock:
            value=self.load();keys=value.setdefault('search_keys',{})
            if key:keys[provider]=key
            else:keys.pop(provider,None)
            self.write(value)
        return self.status()
    def forget(self):
        safe_path(self.path).unlink(missing_ok=True);safe_path(self.path.with_name('credentials.dpapi.part')).unlink(missing_ok=True)
        return self.status()
    def forget_osintgram(self):
        with self.lock:
            keys=self.load().get('search_keys',{})
            if keys:self.write({'search_keys':keys})
            else:self.forget()
        return self.status()
    def forget_instagram(self):
        with self.lock:
            value=self.load();value.pop('instagram',None)
            if value.get('backend')=='instagrapi':value['backend']='hikerapi'
            self.write(value)
        return self.status()
    def invalidate_instagram(self):
        with self.lock:
            value=self.load()
            if value.get('instagram',{}).get('session'):value['instagram']['needs_reconnect']=True;self.write(value)
