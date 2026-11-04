"""Process creation identity, so a reused PID cannot own a stale report."""
import os
from pathlib import Path

def birth(pid):
    if type(pid) is not int or pid<=0:return None
    try:
        if os.name!='nt':return Path('/proc/'+str(pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
        import ctypes
        from ctypes import wintypes as w
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=(w.DWORD,w.BOOL,w.DWORD);kernel.OpenProcess.restype=w.HANDLE
        kernel.GetProcessTimes.argtypes=(w.HANDLE,*[ctypes.POINTER(w.FILETIME)]*4)
        kernel.CloseHandle.argtypes=(w.HANDLE,)
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle:return None
        try:
            times=[w.FILETIME() for _ in range(4)]
            if not kernel.GetProcessTimes(handle,*[ctypes.byref(t) for t in times]):return None
            return str((times[0].dwHighDateTime<<32)|times[0].dwLowDateTime)
        finally:kernel.CloseHandle(handle)
    except (OSError,ValueError,IndexError):return None
