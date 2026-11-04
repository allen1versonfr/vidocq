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
        with request('/local-ai.js') as response:assert b'Install recommended local AI' in response.read()
        with request('/api/local-ai') as response:ai_status=json.load(response)
        assert not ai_status['installed'] and not ai_status['enabled'] and not ai_status['running'] and ai_status['model_bytes']==2497280448
        with request('/api/local-ai/licenses') as response:assert 'Apache' in json.load(response)['text']
        try:request('/api/local-ai/setup',{'consent':False});raise AssertionError('AI setup accepted missing approval')
        except urllib.error.HTTPError as error:assert error.code==400
        assert not (root/'data'/'local-ai').exists(),'AI assets appeared without setup consent'
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
        with request('/review.js') as response:assert b'burn-preview' in response.read()
        with request('/api/cases',{'title':'Browser review fixture','names':['Example Person'],'usernames':['example'],'urls':['https://twitch.tv/example'],'location':'City One; City Two','investigation':{'enabled':True,'max_searches':8,'max_followups':0}}) as response:review_case=json.load(response)
        with request('/api/cases/'+review_case['id']+'/browser-evidence',{'title':'Reviewed public evidence','reference':'https://example.org/about','excerpt':'Example Person uses example as a public handle.','query':'Example Person','consent':True}) as response:captured=json.load(response)
        assert captured['capture']['origin']=='browser-capture'
        with request('/api/cases/'+review_case['id']+'/account-decisions',{'reference':'https://steamcommunity.com/id/example','status':'Rejected','reason':'Synthetic known wrong-account fixture.'}) as response:assert json.load(response)['status']=='Rejected'
        with request('/api/cases/'+review_case['id']+'/run',{'consent':True}) as response:review_run=json.load(response)
        deadline=time.monotonic()+30
        while True:
            with request('/api/case-runs/'+review_run['id']) as response:review_report=json.load(response)
            if review_report['status']=='complete':break
            assert review_report['status'] in ('queued','running') and time.monotonic()<deadline,review_report
            time.sleep(.1)
        assert ('domain','twitch.tv') not in [(t['kind'],t['value']) for t in review_report['search_log']]
        assert [t['value'] for t in review_report['search_log'] if t['kind']=='context']==[['Example Person','City One'],['Example Person','City Two'],['https://twitch.tv/example']]
        assert any(r['origin']=='user-supplied' and r['reference']=='https://example.org/about' for r in review_report['records'])
        with request('/api/case-runs/'+review_run['id']+'?format=html') as response:assert 'Synthetic known wrong-account fixture.' in response.read().decode()
        with request('/api/case-runs/'+review_run['id']+'?format=markdown') as response:assert 'Synthetic known wrong-account fixture.' in response.read().decode()
        with request('/api/burn/preview',{'remove_executable':False}) as response:burn_preview=json.load(response)
        assert burn_preview['data_directory']==str((root/'data').resolve()) and burn_preview['files']
        try:
            request('/api/burn/execute',{'token':burn_preview['token'],'confirmation':'not confirmed'})
            raise AssertionError('Burn accepted an incorrect confirmation')
        except urllib.error.HTTPError as error:assert error.code==400
        assert (root/'data'/'workspace.sqlite3').exists()
        print('Frozen browser evidence, account decisions, location planning, relevance counts and non-destructive burn preview passed.')
        with request('/workbench.js') as response:assert b'Discovery workbench' in response.read()
        with request('/api/cases',{'title':'Synthetic discovery workbench','names':['Example Middle Person'],'urls':['https://example.org/bio'],'aliases':[{'handle':'oldexample','platform':'Example','last_seen':'2020-01-01'}],'investigation':{'enabled':True,'max_searches':6,'max_followups':0}}) as response:discovery_case=json.load(response)
        discovery_path='/api/cases/'+discovery_case['id']
        with request(discovery_path+'/query-plan',{}) as response:plan=json.load(response)
        assert any(q['terms']==['Example Person'] for q in plan['queries'])
        with request(discovery_path+'/link-import',{'mode':'browser','consent':True,'data':{'schema':'vidocq-browser-v1','reference':'https://example.org/bio','title':'Reviewed synthetic bio','excerpt':'Example Person publishes this public link.','links':['https://github.com/example']}}) as response:imported=json.load(response)
        assert imported['result']['edges'][0]['relation']=='browser-captured-link'
        with request(discovery_path+'/link-import',{'mode':'photon','consent':True,'reference':'https://example.org','data':{'external':['https://github.com/example']}}) as response:assert json.load(response)['result']['edges'][0]['relation']=='photon-aggregate-lead'
        class ModelFixture(OsintgramFixture):
            def do_POST(self):
                payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                assert self.path=='/v1/chat/completions' and 'tools' not in payload
                context=json.loads(payload['messages'][1]['content'])
                if 'queries' in context:result={'indexes':[0]}
                elif 'next_steps' in context:result={'comparisons':[],'next_step_indexes':[0]}
                elif 'links' in context:result={'link_ids':[]}
                else:result={'selection_ids':[context['selections'][0]['id']]}
                self.reply({'choices':[{'message':{'content':json.dumps(result)}}]})
        model_fixture=ThreadingHTTPServer(('127.0.0.1',0),ModelFixture);threading.Thread(target=model_fixture.serve_forever,daemon=True).start()
        try:
            with request('/api/local-drafts',{'enabled':True,'port':model_fixture.server_port,'model':'synthetic'}) as response:assert json.load(response)['enabled']
            with request(discovery_path+'/local-draft',{'mode':'queries','consent':True}) as response:assert json.load(response)['queries'][0]['terms']==['Example Middle Person']
            with request(discovery_path+'/run',{'consent':True}) as response:discovery_run=json.load(response)
            deadline=time.monotonic()+30
            while True:
                with request('/api/case-runs/'+discovery_run['id']) as response:discovery_report=json.load(response)
                if discovery_report['status']=='complete':break
                assert time.monotonic()<deadline;time.sleep(.1)
            assert len(discovery_report['link_evidence'])==2
            with request(discovery_path+'/local-draft',{'mode':'summary','run_id':discovery_run['id'],'consent':True}) as response:assert json.load(response)['claims'][0]['citation'] in {r['id'] for r in discovery_report['records']}
            with request('/api/case-runs/'+discovery_run['id']+'?format=html') as response:assert b'photon-aggregate-lead' in response.read()
            ai_case={**discovery_case,'usernames':['publicfixture'],'investigation':{'enabled':True,'ai_assisted':True,'max_searches':10,'max_followups':0}}
            with request(discovery_path,ai_case) as response:json.load(response)
            with request(discovery_path+'/run',{'consent':True}) as response:ai_run=json.load(response)
            deadline=time.monotonic()+45
            while True:
                with request('/api/case-runs/'+ai_run['id']) as response:ai_report=json.load(response)
                if ai_report['status']=='complete':break
                assert time.monotonic()<deadline;time.sleep(.1)
            assert ai_report['ai']['executed_queries']>0 and ai_report['ai']['summary']['claims'],ai_report['ai']
            assert any(t['origin']=='local-ai-approved-query-plan' for t in ai_report['search_log'])
            assert ai_report['coverage_assessment']['status']=='incomplete'
            with request('/api/case-runs/'+ai_run['id']+'?format=markdown') as response:assert b'AI-assisted findings' in response.read()
        finally:
            model_fixture.shutdown();model_fixture.server_close()
            with request('/api/local-drafts',{'enabled':False,'port':8080,'model':'local'}) as response:assert not json.load(response)['enabled']
        print('Frozen browser/Photon imports, historical aliases, link reports and local model fixture passed.')
        from automation_smoke import check as check_automation
        check_automation(request,root,exe,env)
        from guided_workflow_smoke import check as check_guided_workflow
        check_guided_workflow(request,root)
        with request('/api/workspace/backup',{'password':'synthetic backup password'}) as response:bundle=json.load(response)
        assert bundle['encrypted']
        with request('/api/workspace/restore',dict(bundle,password='synthetic backup password')) as response:preview=json.load(response)
        assert not preview['imported'] and all(n==0 for n in preview['counts'].values())
        print('Frozen investigation, screenshot/PDF OCR, encrypted backup and restore preview passed.')
        print('Actual frozen phone/case/report/HTML export API passed.')
    finally:
        subprocess.run(['taskkill','/PID',str(server.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
        server.wait(timeout=20)
    # App replacement/recovery must leave separately downloaded AI files/settings intact.
    from local_ai_assets import MODEL
    ai_fixture=root/'data'/'local-ai';ai_fixture.mkdir(exist_ok=True)
    (ai_fixture/MODEL['filename']).write_bytes(b'synthetic model preservation fixture')
    (root/'data'/'local-ai.json').write_text('{"enabled":false,"backend":"cpu"}')
    from credential_vault import Vault
    vault=Vault(root/'data');vault.save('synthetic-persistence-key-not-for-provider-calls')
    vault.save_instagram('operatorfixture',{'authorization_data':{'ds_user_id':'123456','sessionid':'synthetic-update-preservation-session'},'cookies':{'ds_user_id':'123456','sessionid':'synthetic-update-preservation-session'}})
    ai_snapshots={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ai_fixture/MODEL['filename'],root/'data'/'local-ai.json',root/'data/credentials.dpapi',root/'data/automations.json',root/'data/search-connection.json')}
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
        assert all(hashlib.sha256(p.read_bytes()).hexdigest()==value for p,value in ai_snapshots.items()),'App update altered installed AI data/settings'
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

    burn_folder=root/'disposable-burn';burn_folder.mkdir()
    burn_target=burn_folder/'Disposable-Vidocq.exe';shutil.copyfile(exe,burn_target)
    burn_backup=burn_target.with_name(burn_target.name+'.previous');shutil.copyfile(exe,burn_backup)
    burn_data=root/'disposable-burn-data';burn_data.mkdir()
    sentinel=burn_data/'unrelated-sentinel.txt';sentinel.write_text('Preserve unrelated files.')
    burn_env=dict(env,VIDOCQ_DATA=str(burn_data))
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0));burn_port=listener.getsockname()[1]
    burn_process=subprocess.Popen([str(burn_target),'--serve-only','--port',str(burn_port)],env=burn_env)
    burn_client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    burn_base='http://127.0.0.1:'+str(burn_port)
    def burn_request(path,payload=None):
        req=urllib.request.Request(burn_base+path,data=None if payload is None else json.dumps(payload).encode(),headers={} if payload is None else {'Content-Type':'application/json'})
        return burn_client.open(req,timeout=90)
    try:
        deadline=time.monotonic()+90
        while True:
            try:
                with burn_request('/') as response:assert response.status==200
                break
            except urllib.error.URLError:
                assert burn_process.poll() is None and time.monotonic()<deadline
                time.sleep(.5)
        with burn_request('/api/cases',{'title':'Disposable deletion fixture','usernames':['synthetic']}) as response:assert json.load(response)['id']
        with burn_request('/api/burn/preview',{'remove_executable':True}) as response:plan=json.load(response)
        assert plan['executable']==str(burn_target.resolve()) and set(plan['executable_files'])=={str(burn_target.resolve()),str(burn_backup.resolve())}
        assert all(Path(f['path']).parent==burn_data.resolve() for f in plan['files'])
        with burn_request('/api/burn/execute',{'token':plan['token'],'confirmation':'BURN VIDOCQ'}) as response:burn_result=json.load(response)
        assert burn_result['closing']
        failure_path=Path(burn_result['message'].split('details remain at ',1)[1].removesuffix('.'));helper_folder=failure_path.parent
        assert helper_folder.name.startswith('Vidocq-burn-')
        burn_process.wait(timeout=90)
        deadline=time.monotonic()+90
        expected_removed=[burn_target,burn_backup,helper_folder]+[Path(f['path']) for f in plan['files']]
        while any(p.exists() for p in expected_removed) and time.monotonic()<deadline:
            assert not failure_path.exists(),failure_path.read_text() if failure_path.exists() else ''
            time.sleep(.5)
        assert not any(p.exists() for p in expected_removed),'Disposable burn did not finish within its deadline'
        assert sentinel.read_text()=='Preserve unrelated files.' and exe.exists()
        print('Actual disposable Windows burn removed only its fixture database/logs, copied executable and copied backup; unrelated data and the build remained intact.')
    finally:
        if burn_process.poll() is None:
            subprocess.run(['taskkill','/PID',str(burn_process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
            burn_process.wait(timeout=20)
