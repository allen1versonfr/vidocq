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
        # Exercise the assisted engine against a synthetic Osintgram-compatible local service.
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import threading
        class OsintgramFixture(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def reply(self,data):
                raw=json.dumps(data).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            def do_GET(self):self.reply({'repository':'https://github.com/Datalux/Osintgram'})
            def do_POST(self):
                p=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                assert self.path=='/api/run' and p['target']=='example' and p['max_items']==5
                assert p['calls']==[{'name':'get_user_info','args':{}}]
                self.reply({'target':'example','backend':'synthetic fixture','api_calls_total':1,'tool_calls':[{'name':'get_user_info','result':{'username':'example','full_name':'Example Person','biography':'Contact sample@example.com or +12025550123','is_private':False}}]})
        fixture=ThreadingHTTPServer(('127.0.0.1',0),OsintgramFixture);threading.Thread(target=fixture.serve_forever,daemon=True).start()
        try:
            with request('/api/connectors',{'steam_enabled':False,'osintgram_enabled':True,'osintgram_port':fixture.server_port}) as response:assert json.load(response)['osintgram']['enabled']
            with request('/api/cases',{'title':'Assisted frozen investigation','phones':['+12025550123'],'instagram':['example'],'steam':['example'],'investigation':{'enabled':True,'direct_sources':True,'max_searches':6,'max_followups':1}}) as response:assisted_case=json.load(response)
            with request('/api/cases/'+assisted_case['id']+'/run',{'consent':True}) as response:assisted_run=json.load(response)
            deadline=time.monotonic()+30
            while True:
                with request('/api/case-runs/'+assisted_run['id']) as response:assisted_report=json.load(response)
                if assisted_report['status']=='complete':break
                assert assisted_report['status'] in ('queued','running') and time.monotonic()<deadline,assisted_report
                time.sleep(.1)
            assert assisted_report['analysis']['stronger_leads'] and assisted_report['discovered_clues']
            assert assisted_report['summary']['followups_scheduled']==1
            assert any(c['provider']=='Steam connector' and c['status']=='not-configured' for c in assisted_report['coverage'])
            with request('/api/case-runs/'+assisted_run['id']+'?format=html') as response:assert 'Investigation summary' in response.read().decode()
            with request('/api/connectors',{'steam_enabled':False,'osintgram_enabled':False}) as response:assert not json.load(response)['osintgram']['enabled']
            with request('/assisted.js') as response:assert response.status==200
            print('Frozen assisted investigation, Osintgram bridge, derived-clue budget, Steam configuration gaps and cited summary passed.')
        finally:fixture.shutdown();fixture.server_close()
        with request('/collectors.js') as response:assert b'case-allow-hibp' in response.read()
        with request('/api/collectors') as response:collector_status=json.load(response)
        assert all(not collector_status[k]['enabled'] for k in ('hibp','harvester','maigret'))
        with request('/api/cases',{'title':'Additional collector gaps','emails':['sample@example.com'],'domains':['example.com'],'usernames':['sample'],'investigation':{'enabled':True,'allow_hibp':True,'allow_harvester':True,'allow_maigret':True,'max_searches':3,'max_followups':0}}) as response:extra_case=json.load(response)
        with request('/api/cases/'+extra_case['id']+'/run',{'consent':True}) as response:extra_run=json.load(response)
        deadline=time.monotonic()+30
        while True:
            with request('/api/case-runs/'+extra_run['id']) as response:extra_report=json.load(response)
            if extra_report['status']=='complete':break
            assert extra_report['status'] in ('queued','running') and time.monotonic()<deadline,extra_report
            time.sleep(.1)
        assert all(any(name.lower() in c['provider'].lower() and c['status']=='not-configured' for c in extra_report['coverage']) for name in ('Have I Been Pwned','theHarvester','Maigret')),extra_report['coverage']
        print('Frozen additional collector asset, default-off configuration and missing-connection coverage passed.')
        class CollectorFixture(OsintgramFixture):
            def do_GET(self):
                assert self.headers.get('X-API-Key')=='synthetic-collector-key' or self.headers.get('X-Vidocq-Key')=='synthetic-collector-key'
                if self.path=='/api/v1/sources':return self.reply({'sources':[{'name':'crtsh','activity':'P0','ready':True}]})
                assert self.path=='/api/about'
                self.reply({'service':'vidocq-maigret-bridge','protocol':1})
            def do_POST(self):
                p=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if self.path=='/api/v1/runs':
                    assert p['target']=='example.com' and p['sources']==['crtsh'] and not p['dns_resolve']
                    return self.reply({'run_id':'fixture-1','target':'example.com','sources':['crtsh'],'activities':['P0'],'status':'completed','evidence_status':'complete','results':[{'type':'hostname','value':'sub.example.com','sources':['crtsh']}]})
                assert self.path=='/api/search' and p['username']=='synthetic' and p['sites']==['GitHub']
                self.reply({'username':'synthetic','results':[{'site':'GitHub','status':'Claimed','url':'https://github.com/synthetic'}]})
        extra_fixture=ThreadingHTTPServer(('127.0.0.1',0),CollectorFixture);threading.Thread(target=extra_fixture.serve_forever,daemon=True).start()
        try:
            settings={k+'_enabled':True for k in ('harvester','maigret')}
            settings.update({k+'_key':'synthetic-collector-key' for k in ('harvester','maigret')})
            settings.update({k+'_port':extra_fixture.server_port for k in ('harvester','maigret')})
            with request('/api/collectors',settings) as response:assert json.load(response)['maigret']['enabled']
            for kind,value,choices in [('harvester','example.com',{'sources':['crtsh']}),('maigret','synthetic',{'sites':['GitHub']})]:
                with request('/api/collectors/lookup',dict(kind=kind,value=value,consent=True,**choices)) as response:lookup=json.load(response)
                assert lookup['results'][0]['status']=='ok' and lookup['results'][0]['rows'][0]['lead_only']
            with request('/api/collectors',{'harvester_enabled':False,'maigret_enabled':False,'harvester_key':'','maigret_key':''}) as response:assert not json.load(response)['maigret']['configured']
            print('Frozen authenticated HarvestView and Maigret synthetic lookups passed.')
        finally:extra_fixture.shutdown();extra_fixture.server_close()

        # Start the real bundled library without checking any public account.
        with request('/api/collectors/maigret/setup',{}) as response:auto=json.load(response)
        assert auto['managed_maigret']['running'] and auto['maigret']['enabled'] and auto['maigret']['configured']
        managed_port=auto['maigret']['port']
        with request('/api/collectors/maigret/setup',{}) as response:again=json.load(response)
        assert again['maigret']['port']==managed_port
        try:
            urllib.request.urlopen('http://127.0.0.1:'+str(managed_port)+'/api/about',timeout=5)
            raise AssertionError('Bundled companion allowed unauthenticated access')
        except urllib.error.HTTPError as error:assert error.code==403
        with request('/api/collectors',{'maigret_enabled':False}) as response:assert not json.load(response)['managed_maigret']['running']
        try:
            urllib.request.urlopen('http://127.0.0.1:'+str(managed_port)+'/api/about',timeout=2)
            raise AssertionError('Disabled bundled companion still running')
        except urllib.error.URLError:pass
        print('Actual bundled Maigret automatic setup, repeat setup, authentication and shutdown passed without account queries.')
        with request('/api/search-connection',{'provider':'mwmbl','enabled':True}) as response:free_status=json.load(response)
        assert free_status['configured'] and not free_status['requires_key'] and not free_status['key_configured']
        with request('/api/research',{'kind':'person','value':'Ada Lovelace'}) as response:free_result=json.load(response)
        assert len(free_result['results'])==1 and free_result['results'][0]['provider']=='Mwmbl free web index'
        assert free_result['results'][0]['status']=='ok' and free_result['results'][0]['rows'],free_result
        assert all('api.mwmbl.org' in row['source'] for row in free_result['results'])
        with request('/api/search-connection',{'provider':'mwmbl','enabled':False}) as response:assert not json.load(response)['enabled']
        print('Frozen free anonymous web search returned live canary results without a paid key or account.')
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
        # The marker precedes process exit. Wait for the actual restarted
        # executable/bootloader, especially with a larger bundled dependency set.
        import psutil
        target_path=str(target.resolve()).casefold()
        for child in psutil.process_iter(['exe']):
            if child.info['exe'] and str(Path(child.info['exe']).resolve()).casefold()==target_path:
                try:child.wait(timeout=60)
                except psutil.NoSuchProcess:pass
    print('Frozen imports/UI/database, executable replacement/restart, and failed-launch rollback passed.')
