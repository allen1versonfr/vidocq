"""Real Windows frozen executable and helper replacement/rollback checks."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from version import VERSION
import time
import socket
import urllib.request
import urllib.error
from http.cookiejar import CookieJar

exe = Path('dist/Vidocq.exe').resolve()
from check_windows_icon import verify
verify(exe,'build/assets/vidocq.ico')
env = dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT='1')
with tempfile.TemporaryDirectory(prefix='Vidocq-ci-') as temp:
    root = Path(temp)
    env['VIDOCQ_DATA'] = str(root/'data')
    smoke = root/'smoke.json'
    subprocess.run([str(exe), '--smoke-test', str(smoke)], env=env, check=True, timeout=120)
    assert json.loads(smoke.read_text()) == {'ok':True, 'version':VERSION}
    # Exercise case creation/report/export against the actual frozen HTTP backend,
    # using only offline phone metadata and prepared username links (no network queries).
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    server=subprocess.Popen([str(exe),'--serve-only','--port',str(port)],env=env)
    client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    base='http://127.0.0.1:'+str(port)
    def request(path,payload=None):
        req=urllib.request.Request(base+path,data=None if payload is None else json.dumps(payload).encode(),headers={} if payload is None else {'Content-Type':'application/json'})
        return client.open(req,timeout=90)
    try:
        deadline=time.monotonic()+90
        while True:
            try:
                with request('/') as response:assert response.status==200
                break
            except urllib.error.URLError:
                if server.poll() is not None or time.monotonic()>=deadline:raise
                time.sleep(.5)
        with request('/api/search-connection',{'key':'','enabled':False}) as response:assert not json.load(response)['configured']
        for platform,url in [('instagram','https://www.instagram.com/example/'),('tiktok','https://www.tiktok.com/@example'),('vsco','https://vsco.co/example/gallery')]:
            with request('/api/research',{'kind':'auto','value':url}) as response:result=json.load(response)
            assert result['kind']==platform and result['social_profile']['handle']=='example'
            assert result['results'][0]['status']=='not-configured' and len(result['links'])==3
        with request('/api/cases',{'title':'Frozen case report','phones':['2025550123'],'usernames':['example'],'instagram':['@example'],'tiktok':['https://www.tiktok.com/@example'],'vsco':['https://vsco.co/example/gallery']}) as response:case=json.load(response)
        with request('/api/cases/'+case['id']+'/run',{'consent':True}) as response:run=json.load(response)
        deadline=time.monotonic()+30
        while True:
            with request('/api/case-runs/'+run['id']) as response:report=json.load(response)
            if report['status']=='complete':break
            assert report['status'] in ('queued','running'),report
            assert time.monotonic()<deadline,'Frozen case report timed out'
            time.sleep(.25)
        assert len(report['social_profiles'])==3 and report['completed']==5
        assert {p['platform'] for p in report['social_profiles']}=={'instagram','tiktok','vsco'}
        assert report['summary']['offline_records']==1 and report['summary']['prepared_not_run']>0
        with request('/api/case-runs/'+run['id']+'?format=html') as response:
            text=response.read().decode();assert 'Frozen case report' in text and 'Offline phone metadata' in text and 'https://www.tiktok.com/@example/' in text and 'https://www.instagram.com/example/' in text and 'https://vsco.co/example/' in text
        # Investigation dependencies and new local APIs must work inside the frozen build.
        import base64, io
        from PIL import Image, ImageDraw, ImageFont
        with request('/api/investigation',{'kind':'entity','label':'Frozen example'}) as response:entity=json.load(response)
        image=Image.new('RGB',(1000,180),'white')
        ImageDraw.Draw(image).text((20,40),'VIDOCQ EXAMPLE EVIDENCE',font=ImageFont.truetype('arial.ttf',40),fill='black')
        buffer=io.BytesIO();image.save(buffer,format='PNG')
        with request('/api/ingest',{'name':'example.png','content':base64.b64encode(buffer.getvalue()).decode()}) as response:document=json.load(response)
        assert 'VIDOCQ' in document['pages'][0] or 'OCR unavailable' in document['notice'],document['notice']
        from pypdf import PdfWriter
        pdf=PdfWriter();pdf.add_blank_page(width=300,height=200);buffer=io.BytesIO();pdf.write(buffer)
        with request('/api/ingest',{'name':'example.pdf','content':base64.b64encode(buffer.getvalue()).decode()}) as response:pdf_document=json.load(response)
        assert len(pdf_document['pages'])==1 and 'Local OCR attempted' in pdf_document['notice'],pdf_document
        with request('/api/save',{'title':'Frozen citation','entity_ids':[entity['id']],'capture':{'excerpt':document['pages'][0],'attachments':[document['id']]}}) as response:finding=json.load(response)
        sf_rows=[{'data':'example.com','event_type':'DOMAIN_NAME','module':'sfp_example','source_data':'','false_positive':0,'last_seen':'2026-01-01 00:00:00','scan_name':'Frozen import','scan_target':'example.com'}, {'data':'192.0.2.1','event_type':'IP_ADDRESS','module':'sfp_example','source_data':'example.com','false_positive':0,'last_seen':'2026-01-01 00:00:01','scan_name':'Frozen import','scan_target':'example.com'}]
        sf_payload={'name':'example-SpiderFoot.json','content':base64.b64encode(json.dumps(sf_rows).encode()).decode()}
        with request('/api/import/spiderfoot',sf_payload) as response:sf_preview=json.load(response)
        assert not sf_preview['imported'] and sf_preview['new_records']['findings']==2
        with request('/api/import/spiderfoot',dict(sf_payload,confirm=True)) as response:sf_import=json.load(response)
        assert sf_import['imported'] and sf_import['new_records']['relationships']==1
        with request('/api/import/spiderfoot',sf_payload) as response:sf_repeat=json.load(response)
        assert all(n==0 for n in sf_repeat['new_records'].values())
        with request('/spiderfoot.js') as response:assert response.status==200
        print('Frozen SpiderFoot preview/import/re-import and frontend asset passed.')
        with request('/api/workspace/backup',{'password':'synthetic backup password'}) as response:bundle=json.load(response)
        assert bundle['encrypted']
        with request('/api/workspace/restore',dict(bundle,password='synthetic backup password')) as response:preview=json.load(response)
        assert not preview['imported'] and all(n==0 for n in preview['counts'].values())
        print('Frozen investigation, screenshot/PDF OCR, encrypted backup and restore preview passed.')
        print('Actual frozen phone/case/report/HTML export API passed.')
    finally:
        subprocess.run(['taskkill','/PID',str(server.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
        server.wait(timeout=20)
    for scenario in ('success', 'rollback'):
        folder=root/scenario;folder.mkdir()
        target=folder/'Vidocq.exe';shutil.copyfile(exe,target)
        staged=folder/'candidate.exe'
        if scenario=='success':shutil.copyfile(exe,staged)
        else:staged.write_bytes(b'MZ'+b'not-a-real-executable'*100)
        ready=folder/'ready';result=folder/'result.json';check=folder/'child.json'
        data=staged.read_bytes()
        job={'target':str(target),'staged':str(staged),'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),
             'parent_pid':0,'ready':str(ready),'result':str(result),'version':VERSION,
             'launch_args':['--smoke-test',str(check)]}
        jobfile=folder/'job.json';jobfile.write_text(json.dumps(job))
        helper=folder/'helper.exe';shutil.copyfile(exe,helper)
        process=subprocess.run([str(helper),'--apply-update',str(jobfile)],env=env,timeout=180)
        assert process.returncode==(0 if scenario=='success' else 1), (scenario,process.returncode)
        assert json.loads(result.read_text())['status']==('updated' if scenario=='success' else 'failed')
        assert hashlib.sha256(target.read_bytes()).digest()==hashlib.sha256(exe.read_bytes()).digest()
        deadline=time.monotonic()+90
        while not check.exists() and time.monotonic()<deadline:time.sleep(.5)
        assert check.exists(),f'{scenario}: restarted executable did not complete smoke test'
        # The child writes its marker just before exit; allow Windows to release the file.
        time.sleep(2)
    print('Frozen imports/UI/database, executable replacement/restart, and failed-launch rollback passed.')
