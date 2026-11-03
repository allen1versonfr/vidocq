"""Start the bundled, isolated Maigret companion without installing software."""
import atexit
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time

class ManagedMaigret:
    def __init__(self):
        self.lock=threading.RLock();self.process=None;self.port=None;self.key='';self.state='stopped'
        atexit.register(self.stop)

    def status(self):
        with self.lock:
            alive=self.process is not None and self.process.poll() is None
            return {'state':self.state if alive or self.state=='starting' else 'stopped','running':alive,'bundled':True}

    def ensure(self):
        from additional_collectors import transport
        with self.lock:
            if self.process is not None and self.process.poll() is None and self.state=='ready':return self.key,self.port
            self.stop();self.state='starting'
            with socket.socket() as listener:
                listener.bind(('127.0.0.1',0));self.port=listener.getsockname()[1]
            self.key=secrets.token_urlsafe(32)
            if getattr(sys,'frozen',False):command=[sys.executable,'--maigret-companion']
            else:command=[sys.executable,str(Path(__file__).resolve().parent/'scripts/maigret_bridge.py')]
            command+=['--port',str(self.port),'--parent-pid',str(os.getpid())]
            env=dict(os.environ,VIDOCQ_MAIGRET_BRIDGE_KEY=self.key)
            # A child uses the parent's extracted bundle and never opens a console.
            env.pop('PYINSTALLER_RESET_ENVIRONMENT',None)
            try:
                self.process=subprocess.Popen(command,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                deadline=time.monotonic()+60
                while time.monotonic()<deadline:
                    if self.process.poll() is not None:break
                    try:
                        about=transport('http://127.0.0.1:'+str(self.port)+'/api/about',key=self.key,service='maigret',timeout=1)
                        if about.get('service')=='vidocq-maigret-bridge' and about.get('protocol')==1:
                            self.state='ready';return self.key,self.port
                    except (ValueError,OSError):pass
                    time.sleep(.15)
                raise ValueError('Bundled Maigret could not start. Retry setup or reinstall the latest Vidocq release.')
            except Exception:
                self.stop();raise

    def stop(self):
        with self.lock:
            process=self.process;self.process=None;self.state='stopped'
            if process is not None and process.poll() is None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            self.key='';self.port=None

def watch_parent(server,pid):
    """Stop orphaned companions, including after a forced Windows app exit."""
    def watch():
        if os.name=='nt':
            import ctypes
            from ctypes import wintypes
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
            kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
            kernel.CloseHandle.argtypes=[wintypes.HANDLE]
            handle=kernel.OpenProcess(0x00100000,False,pid)
            if handle:
                try:kernel.WaitForSingleObject(handle,0xFFFFFFFF)
                finally:kernel.CloseHandle(handle)
        else:
            while os.getppid()==pid:time.sleep(1)
        server.shutdown()
    threading.Thread(target=watch,daemon=True).start()
