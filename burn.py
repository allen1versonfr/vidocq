"""Explicit removal of named Vidocq-owned files; never a forensic-erasure claim."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import threading

OWNED_FILES=('workspace.sqlite3','workspace.sqlite3-wal','workspace.sqlite3-shm','workspace.sqlite3-journal','startup.log','update-result.json','.vidocq-owner.json')

def no_links(path):
    path=Path(path).absolute()
    for node in (path,*path.parents):
        if node.is_symlink() or (node.exists() and getattr(node.stat(follow_symlinks=False),'st_file_attributes',0)&0x400):raise ValueError('Burn refuses symbolic links and Windows reparse points.')
    return path

def safe_root(path):
    root=no_links(path).resolve()
    forbidden={Path(root.anchor),Path.home().resolve(),Path.cwd().resolve()}
    forbidden.update(Path.home()/p for p in ('Desktop','Documents','Downloads'))
    if root in forbidden or len(root.parts)<3:raise ValueError('Burn requires a dedicated app data folder, not a shared/system/workspace root.')
    for env in ('SYSTEMROOT','ProgramFiles','ProgramFiles(x86)'):
        base=os.environ.get(env)
        if base and (root==Path(base).resolve() or root.is_relative_to(Path(base).resolve())):raise ValueError('Burn cannot operate in system/application folders.')
    return root

def mark_workspace(path):
    root=safe_root(path);root.mkdir(parents=True,exist_ok=True);marker=root/'.vidocq-owner.json'
    if not marker.exists():marker.write_text(json.dumps({'application':'Vidocq','id':secrets.token_hex(24)}),encoding='utf-8')
    no_links(marker)
    value=json.loads(marker.read_text(encoding='utf-8'))
    if value.get('application')!='Vidocq' or not isinstance(value.get('id'),str):raise ValueError('Workspace ownership marker is invalid.')
    return root,value['id']

class BurnManager:
    def __init__(self,data):self.data=Path(data);self.plan=None;self.pending=False;self.lock=threading.RLock()
    def preview(self,remove_executable=False):
        with self.lock:return self._preview(remove_executable)
    def _preview(self,remove_executable):
        if type(remove_executable) is not bool:raise ValueError('Choose whether to remove the executable.')
        root,owner=mark_workspace(self.data)
        files=[]
        for name in OWNED_FILES:
            target=no_links(root/name)
            if target.exists() and not target.is_file():raise ValueError('An owned filename is not a regular file; burn refused.')
            files.append({'path':str(target),'exists':target.exists(),'size':target.stat().st_size if target.exists() else 0})
        executable=None;executable_files=[]
        if remove_executable:
            if os.name!='nt' or not getattr(sys,'frozen',False):raise ValueError('Executable removal is available only in the portable Windows build. Source code and Python environments are never removed.')
            target=no_links(sys.executable).resolve()
            executable={'path':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()};executable_files.append(executable)
            backup=no_links(target.with_name(target.name+'.previous'))
            if backup.is_file():executable_files.append({'path':str(backup),'sha256':hashlib.sha256(backup.read_bytes()).hexdigest()})
        self.plan={'token':secrets.token_urlsafe(32),'created':time.monotonic(),'root':str(root),'owner':owner,'files':files,'executable':executable,'executable_files':executable_files}
        return {'token':self.plan['token'],'data_directory':str(root),'files':files,'remove_executable':bool(executable),'executable':executable['path'] if executable else None,'executable_files':[x['path'] for x in executable_files],
            'limitations':['Permanent file deletion, not guaranteed secure erasure on SSDs or backups.','Exports/screenshots saved elsewhere, other Vidocq copies, browser history/downloads and OS/security logs are outside this operation.','Third-party tools, credentials stored outside Vidocq and provider-side logs are not removed.','Unknown files in the data folder are preserved. The folder is removed only if empty.']}
    def execute(self,payload):
        with self.lock:return self._execute(payload)
    def _execute(self,payload):
        plan=self.plan
        if not plan or payload.get('confirmation')!='BURN VIDOCQ' or not secrets.compare_digest(str(payload.get('token','')),plan['token']) or time.monotonic()-plan['created']>300:raise ValueError('Preview deletion, then type BURN VIDOCQ within five minutes.')
        root,owner=mark_workspace(self.data)
        if str(root)!=plan['root'] or owner!=plan['owner']:raise ValueError('Workspace identity changed; create a fresh preview.')
        current=[str(no_links(root/name)) for name in OWNED_FILES if (root/name).is_file()]
        if set(current)!={f['path'] for f in plan['files'] if f['exists']}:raise ValueError('Workspace files changed; create a fresh preview.')
        if os.name!='nt':raise ValueError('This burn helper is supported in the Windows app only.')
        folder=Path(tempfile.mkdtemp(prefix='Vidocq-burn-'));script=folder/'cleanup.ps1';job=folder/'job.json'
        source=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/'scripts/burn_cleanup.ps1'
        script.write_bytes(source.read_bytes())
        job.write_text(json.dumps({**plan,'parent_pid':os.getpid(),'helper_directory':str(folder)}),encoding='utf-8')
        subprocess.Popen(['powershell.exe','-ExecutionPolicy','Bypass','-NoProfile','-NonInteractive','-WindowStyle','Hidden','-File',str(script),'-Job',str(job)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
        self.pending=True;self.plan=None
        return {'closing':True,'message':'Vidocq is closing. The helper removes only the previewed files after process exit. External copies and OS/browser records remain outside its scope. If deletion fails, details remain at '+str(folder/'failure.txt')+'.'}
