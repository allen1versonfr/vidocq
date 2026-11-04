"""Windows-user-bound DPAPI storage. No plaintext fallback or secret read API."""
import ctypes,json,os
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
    def __init__(self,data):self.path=Path(data)/'credentials.dpapi'
    def load(self):
        if not safe_path(self.path).is_file():return {}
        if self.path.stat().st_size>20000:raise ValueError('Credential store is invalid.')
        value=json.loads(protect(self.path.read_bytes(),True))
        if not isinstance(value,dict):raise ValueError('Credential store is invalid.')
        return value
    def status(self):
        try:return {'saved':bool(self.load().get('hiker_key')),'locked':False}
        except (ValueError,OSError):return {'saved':True,'locked':True}
    def save(self,key):
        if not isinstance(key,str) or not 10<=len(key)<=1024 or any(ord(c)<33 for c in key):raise ValueError('Enter your HikerAPI key.')
        payload=protect(json.dumps({'hiker_key':key}).encode());self.path.parent.mkdir(parents=True,exist_ok=True)
        temp=safe_path(self.path.with_name('credentials.dpapi.part'));temp.write_bytes(payload);os.replace(temp,safe_path(self.path))
        return self.status()
    def forget(self):
        safe_path(self.path).unlink(missing_ok=True);safe_path(self.path.with_name('credentials.dpapi.part')).unlink(missing_ok=True)
        return self.status()
