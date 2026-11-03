"""Optional real frozen-model test; requires an existing isolated test installation."""
import argparse
from http.cookiejar import CookieJar
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request
import urllib.error


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,required=True);args=parser.parse_args()
    repo=Path(__file__).resolve().parents[1];data=args.data.resolve()
    if not data.is_relative_to((repo/'.test-data').resolve()) or not (data/'local-ai'/'installed.json').is_file():raise ValueError('Use an already installed disposable .test-data workspace, never a live user workspace.')
    with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    process=subprocess.Popen([str(repo/'dist/Vidocq.exe'),'--serve-only','--port',str(port)],env=dict(os.environ,VIDOCQ_DATA=str(data),PYINSTALLER_RESET_ENVIRONMENT='1'),creationflags=subprocess.CREATE_NO_WINDOW)
    client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()));base='http://127.0.0.1:'+str(port)
    def request(path,payload=None):
        req=urllib.request.Request(base+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with client.open(req,timeout=180) as response:return response.read()
    try:
        deadline=time.monotonic()+90
        while True:
            try:request('/');break
            except urllib.error.URLError:
                if process.poll() is not None or time.monotonic()>deadline:raise
                time.sleep(.5)
        status=json.loads(request('/api/local-ai'));assert status['installed'] and status['enabled'] and not status['running'],status
        case=json.loads(request('/api/cases',{'title':'Synthetic real local AI test','names':['Ada Byron Lovelace'],'locations':['London'],'investigation':{'enabled':True,'max_searches':3,'max_followups':0}}))
        path='/api/cases/'+case['id']
        queries=json.loads(request(path+'/local-draft',{'mode':'queries','consent':True}));assert queries['draft'] and queries['queries']
        request(path+'/browser-evidence',{'title':'Synthetic source fixture','reference':'https://example.org/biography','excerpt':'This synthetic fixture describes a public biography and a mathematics archive.','consent':True})
        run=json.loads(request(path+'/run',{'consent':True}));deadline=time.monotonic()+30
        while True:
            report=json.loads(request('/api/case-runs/'+run['id']))
            if report['status']=='complete':break
            assert time.monotonic()<deadline;time.sleep(.2)
        summary=json.loads(request(path+'/local-draft',{'mode':'summary','consent':True,'run_id':run['id']}));assert summary['draft'] and summary['claims']
        status=json.loads(request('/api/local-ai'));runtime_port=status['port'];assert status['running']
        try:urllib.request.urlopen('http://127.0.0.1:'+str(runtime_port)+'/v1/models',timeout=5);raise AssertionError('Managed inference is unauthenticated')
        except urllib.error.HTTPError as error:assert error.code==401
        print(json.dumps({'ok':True,'model':status['model'],'backend':status['backend_used'],'queries':len(queries['queries']),'cited_excerpts':len(summary['claims']),'authenticated':True}),flush=True)
    finally:
        # Kill only the frozen Python host, not its descendants. The job object
        # must terminate llama-server; the one-file bootloader then exits itself.
        import psutil
        children=psutil.Process(process.pid).children(recursive=True)
        hosts=[p for p in children if p.exe().casefold()==str(repo/'dist/Vidocq.exe').casefold()]
        for host in hosts or [psutil.Process(process.pid)]:
            subprocess.run(['taskkill','/PID',str(host.pid),'/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
        try:process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False);raise
    # Job-object protection must close the model socket on parent shutdown.
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        with socket.socket() as connection:
            if connection.connect_ex(('127.0.0.1',runtime_port))!=0:break
        time.sleep(.2)
    else:raise AssertionError('Managed model survived parent exit')
    print('Real frozen inference, persisted installation, auth and parent-exit cleanup passed.')


if __name__=='__main__':main()
