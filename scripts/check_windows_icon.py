"""Verify the built PE embeds the generated ICO's exact frame payloads."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import struct

def verify(executable,icon):
    raw=Path(icon).read_bytes();reserved,kind,count=struct.unpack_from('<HHH',raw)
    assert (reserved,kind)==(0,1) and count>=7,'Missing multi-size Windows ICO'
    expected=set()
    for index in range(count):
        size,offset=struct.unpack_from('<II',raw,6+index*16+8);expected.add(raw[offset:offset+size])
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.LoadLibraryExW.argtypes=(wintypes.LPCWSTR,ctypes.c_void_p,wintypes.DWORD);k.LoadLibraryExW.restype=ctypes.c_void_p
    k.FindResourceW.argtypes=(ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p);k.FindResourceW.restype=ctypes.c_void_p
    k.LoadResource.argtypes=(ctypes.c_void_p,ctypes.c_void_p);k.LoadResource.restype=ctypes.c_void_p
    k.LockResource.argtypes=(ctypes.c_void_p,);k.LockResource.restype=ctypes.c_void_p
    k.SizeofResource.argtypes=(ctypes.c_void_p,ctypes.c_void_p);k.SizeofResource.restype=wintypes.DWORD
    k.FreeLibrary.argtypes=(ctypes.c_void_p,)
    callback=ctypes.WINFUNCTYPE(wintypes.BOOL,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ssize_t)
    k.EnumResourceNamesW.argtypes=(ctypes.c_void_p,ctypes.c_void_p,callback,ctypes.c_ssize_t);k.EnumResourceNamesW.restype=wintypes.BOOL
    module=k.LoadLibraryExW(str(Path(executable).resolve()),None,0x22);assert module,'Cannot read executable icon resources'
    actual=set()
    @callback
    def collect(handle,resource_type,name,param):
        resource=k.FindResourceW(handle,name,resource_type)
        data=k.LockResource(k.LoadResource(handle,resource));size=k.SizeofResource(handle,resource)
        if data and size:actual.add(ctypes.string_at(data,size))
        return True
    try:
        assert k.EnumResourceNamesW(module,3,collect,0),'No RT_ICON resources in executable'
        assert expected.issubset(actual),'Executable icon differs from Vidocq design'
    finally:k.FreeLibrary(module)
    print('Verified '+str(len(expected))+' exact Vidocq icon frames embedded in Windows executable.')
if __name__=='__main__':verify('dist/Vidocq.exe','build/assets/vidocq.ico')
