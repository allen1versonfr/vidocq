import base64
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
import urllib.request
import urllib.error

import app
from investigation import InvestigationService
from spiderfoot_import import import_spiderfoot, parse_export, stable

def event(**changes):
    row={'data':'example.com','event_type':'DOMAIN_NAME','module':'sfp_example',
         'source_data':'','false_positive':0,'last_seen':'2026-01-02 03:04:05',
         'scan_name':'Example scan','scan_target':'example.com'}
    row.update(changes);return row

def payload(rows,**changes):
    p={'name':'example-SpiderFoot.json','content':base64.b64encode(json.dumps(rows).encode()).decode()}
    p.update(changes);return p

class SpiderFootTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'workspace.sqlite3'
        def database():
            db=sqlite3.connect(self.path,factory=app.NotebookConnection)
            for sql in ['CREATE TABLE IF NOT EXISTS findings (id TEXT PRIMARY KEY,data TEXT NOT NULL)',
                        'CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY,data TEXT NOT NULL,updated_at TEXT NOT NULL)',
                        'CREATE TABLE IF NOT EXISTS case_runs (id TEXT PRIMARY KEY,case_id TEXT NOT NULL,data TEXT NOT NULL)']:db.execute(sql)
            return db
        self.db=database;self.service=InvestigationService(database);self.service.initialize()
    def tearDown(self):self.temp.cleanup()
    def test_preview_makes_no_records_and_preserves_native_shape(self):
        rows=[event(),event(data='192.0.2.1',event_type='IP_ADDRESS',source_data='example.com')]
        p=payload(rows);preview=import_spiderfoot(self.service,p)
        self.assertFalse(preview['imported']);self.assertEqual(preview['new_records'],{'findings':2,'entities':2,'relationships':1})
        self.assertEqual(self.service.findings(),[]);self.assertEqual(self.service.items(),[])
        with self.db() as db:self.assertEqual(db.execute('SELECT count(*) FROM attachments').fetchone()[0],0)
        result=import_spiderfoot(self.service,dict(p,confirm=True));self.assertTrue(result['imported'])
        finding=next(f for f in self.service.findings() if f['capture']['excerpt']=='192.0.2.1')
        capture=finding['capture'];self.assertEqual(capture['spiderfoot']['record'],rows[1]);self.assertEqual(capture['retrieved_at'],'')
        self.assertEqual(capture['spiderfoot']['last_seen'],'2026-01-02 03:04:05');self.assertIn('#row=2',capture['reference'])
        self.assertEqual(self.service.attachment(capture['attachments'][0])[-1],base64.b64decode(p['content']))
        relationship=next(i for i in self.service.items() if i['kind']=='relationship')
        self.assertEqual(relationship['status'],'Proposed');self.assertEqual(relationship['evidence_ids'],[finding['id']])
    def test_reimport_and_reordered_rows_preserve_analyst_changes(self):
        rows=[event(),event(data='192.0.2.1',event_type='IP_ADDRESS',source_data='example.com')]
        import_spiderfoot(self.service,payload(rows,confirm=True));f=self.service.findings()[0]
        self.service.save_finding(dict(f,notes='Analyst review',status='Corroborated'))
        preview=import_spiderfoot(self.service,payload(list(reversed(rows))))
        self.assertTrue(all(n==0 for n in preview['new_records'].values()))
        import_spiderfoot(self.service,payload(rows+rows,confirm=True));self.assertEqual(len(self.service.findings()),2)
        self.assertEqual(next(x for x in self.service.findings() if x['id']==f['id'])['notes'],'Analyst review')
    def test_ambiguous_and_missing_sources_stay_unresolved(self):
        rows=[event(data='shared',event_type='DOMAIN_NAME'),event(data='shared',event_type='USERNAME'),
              event(data='child',source_data='shared'),event(data='other',source_data='missing')]
        result=import_spiderfoot(self.service,payload(rows,confirm=True))
        self.assertEqual(result['summary']['ambiguous_sources'],1);self.assertEqual(result['summary']['missing_sources'],1)
        unresolved=[i for i in self.service.items() if i['kind']=='entity' and i['spiderfoot']['unresolved_source']]
        self.assertEqual(len(unresolved),2)
        for relationship in [i for i in self.service.items() if i['kind']=='relationship']:
            self.assertIn(relationship['entity_ids'][0],[i['id'] for i in unresolved])
    def test_false_positive_and_self_link_preserved_without_identity_claim(self):
        r=import_spiderfoot(self.service,payload([event(source_data='example.com',false_positive='1')],confirm=True))
        self.assertEqual(r['summary']['self_links_omitted'],1);self.assertEqual(r['summary']['relationships'],0)
        self.assertEqual(self.service.findings()[0]['status'],'Rejected');self.assertEqual(self.service.findings()[0]['capture']['spiderfoot']['false_positive'],'1')
    def test_scan_scopes_and_entity_types_remain_separate(self):
        rows=[event(),event(scan_name='Another scan'),event(event_type='USERNAME')]
        result=import_spiderfoot(self.service,payload(rows,confirm=True));self.assertEqual(result['summary']['entities'],3)
    def test_case_assignment_and_backup_restore_roundtrip(self):
        case_id='c'*24
        with self.db() as db:db.execute('INSERT INTO cases VALUES (?,?,?)',(case_id,json.dumps({'id':case_id,'title':'Example case','notebook_ids':[]}), '2026-01-01'))
        result=import_spiderfoot(self.service,payload([event(),event(data='child',source_data='example.com')],case_id=case_id,confirm=True))
        self.assertTrue(all(f['case_ids']==[case_id] for f in self.service.findings()))
        content=self.service.export_bundle()['content']
        self.assertTrue(all(n==0 for n in self.service.restore({'content':content})['counts'].values()))
        with self.db() as db:
            for table in ('findings','cases','case_runs','investigation_items','attachments'):db.execute('DELETE FROM '+table)
        self.service.restore({'content':content,'confirm':True});self.assertEqual(len(self.service.findings()),2)
        self.assertEqual(len([i for i in self.service.items() if i['kind']=='relationship']),1)
    def test_invalid_rows_and_nonstandard_exports_rejected(self):
        for rows in [[],{},[{'data':'example'}],[event(data=3)],[event(false_positive=2)],[event(module=None)],[event(data='')],[event()]*5001]:
            with self.assertRaises(ValueError):import_spiderfoot(self.service,payload(rows,confirm=True))
        self.assertEqual(self.service.findings(),[])
        with self.assertRaises(ValueError):parse_export({'name':'test.json','content':'bad'})
        with self.assertRaises(ValueError):parse_export(payload([event()],name='test.csv'))
        with self.assertRaises(ValueError):parse_export({'name':'test.json','content':base64.b64encode(b'[{"data":"a","data":"b"}]').decode()})
    def test_missing_case_and_late_collision_roll_back_everything(self):
        rows=[event(),event(data='child',source_data='example.com')]
        with self.assertRaises(ValueError):import_spiderfoot(self.service,payload(rows,case_id='a'*24,confirm=True))
        fid=stable('spiderfoot-finding-v1','',rows[1])
        with self.db() as db:db.execute('INSERT INTO findings VALUES (?,?)',(fid,json.dumps({'id':fid,'title':'Existing','source':'local','date':'2026-01-01','notes':'Untouched','status':'Unverified lead'})))
        with self.assertRaises(ValueError):import_spiderfoot(self.service,payload(rows,confirm=True))
        self.assertEqual(len(self.service.findings()),1);self.assertEqual(self.service.items(),[])
        with self.db() as db:self.assertEqual(db.execute('SELECT count(*) FROM attachments').fetchone()[0],0)
    def test_imported_markup_is_preserved_as_data(self):
        value='<script>alert(1)</script>'
        import_spiderfoot(self.service,payload([event(data=value)],confirm=True))
        self.assertEqual(self.service.findings()[0]['capture']['excerpt'],value)

class SpiderFootHTTPTests(unittest.TestCase):
    def test_local_api_auth_preview_import_and_script(self):
        with tempfile.TemporaryDirectory() as folder:
            old=app.DATA;app.DATA=Path(folder)
            app.CASES.initialize();app.INVESTIGATION.initialize()
            server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
            def request(path,p=None,auth=True):
                headers={'Cookie':'desk='+app.COOKIE} if auth else {}
                if p is not None:headers['Content-Type']='application/json'
                return urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+path,data=json.dumps(p).encode() if p is not None else None,headers=headers))
            try:
                p=payload([event()])
                with self.assertRaises(urllib.error.HTTPError) as error:request('/api/import/spiderfoot',p,False)
                self.assertEqual(error.exception.code,403)
                with request('/api/import/spiderfoot',p) as response:self.assertFalse(json.load(response)['imported'])
                with request('/api/import/spiderfoot',dict(p,confirm=True)) as response:self.assertTrue(json.load(response)['imported'])
                with request('/spiderfoot.js') as response:self.assertEqual(response.status,200)
            finally:server.shutdown();server.server_close();app.DATA=old
