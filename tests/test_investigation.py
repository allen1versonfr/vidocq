import base64
import copy
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import app
from investigation import InvestigationService, compare_reports, local_ocr

class InvestigationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'workspace.sqlite3'
        def database():
            db=sqlite3.connect(self.path,factory=app.NotebookConnection)
            db.execute('CREATE TABLE IF NOT EXISTS findings (id TEXT PRIMARY KEY,data TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY,data TEXT NOT NULL,updated_at TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS case_runs (id TEXT PRIMARY KEY,case_id TEXT NOT NULL,data TEXT NOT NULL)')
            return db
        self.db=database;self.service=InvestigationService(database);self.service.initialize()
    def tearDown(self):self.temp.cleanup()
    def finding(self,**fields):
        return self.service.save_finding(dict(title='Example evidence',source='https://index.example/search',notes='Assessment',capture={'provider':'Example index','excerpt':'Preserved text','reference':'https://example.com/item'},**fields))
    def entity(self,label='Example entity'):
        return self.service.save_item({'kind':'entity','label':label})
    def bundle(self):return self.service.export_bundle()['content']
    def mutate_bundle(self,content,change):
        raw=json.loads(base64.b64decode(content));change(raw['tables']);return base64.b64encode(json.dumps(raw).encode()).decode()
    def test_legacy_and_immutable_capture_with_assessment_history(self):
        legacy={'id':'a'*24,'title':'Legacy','notes':'Original notes','source':'index','date':'2020-01-01','status':'Unverified lead'}
        with self.db() as db:db.execute('INSERT INTO findings VALUES (?,?)',(legacy['id'],json.dumps(legacy)))
        self.assertEqual(self.service.findings()[0]['capture']['origin'],'legacy')
        f=self.finding();edited=self.service.save_finding(dict(f,notes='Updated',status='Corroborated',capture={'excerpt':'tampered'},source='tampered'))
        self.assertEqual(edited['capture'],f['capture']);self.assertEqual(edited['source'],f['source']);self.assertEqual(edited['history'][0]['notes'],'Assessment')
        self.assertEqual(edited['id'],f['id'])
    def test_relationship_requires_real_distinct_entities_and_evidence(self):
        a,b=self.entity(),self.entity('Other');f=self.finding()
        p={'kind':'relationship','label':'mentions','entity_ids':[a['id'],b['id']],'evidence_ids':[f['id']],'status':'Supported'}
        r=self.service.save_item(p);self.assertEqual(r['status'],'Supported')
        for changes in [{'entity_ids':[a['id'],a['id']]},{'evidence_ids':[]},{'evidence_ids':['b'*24]},{'status':'Certain identity'}]:
            with self.assertRaises(ValueError):self.service.save_item(dict(p,**changes))
    def test_event_dates_separate_from_discovery_and_reject_reversed_range(self):
        f=self.finding();p={'kind':'event','label':'Publication','start':'2021-01-01','end':'2021-02-01','precision':'Range','evidence_ids':[f['id']]}
        event=self.service.save_item(p);self.assertEqual(event['start'],'2021-01-01');self.assertNotEqual(event['created_at'][:10],event['start'])
        for changes in [{'end':'2020-01-01'},{'start':'2021-02-30'},{'precision':'Certain'}]:
            with self.assertRaises(ValueError):self.service.save_item(dict(p,**changes))
    def test_merge_and_split_preserve_audit(self):
        a,b=self.entity(),self.entity('Other');f=self.finding(entity_ids=[a['id']]);g=self.finding(entity_ids=[a['id']])
        self.service.reorganize({'mode':'split','source':a['id'],'target':b['id'],'evidence_ids':[f['id']]})
        rows={x['id']:x for x in self.service.findings()};self.assertEqual(rows[f['id']]['entity_ids'],[b['id']]);self.assertEqual(rows[g['id']]['entity_ids'],[a['id']])
        self.service.reorganize({'mode':'merge','source':a['id'],'target':b['id']})
        self.assertTrue(all(x['entity_ids']==[b['id']] for x in self.service.findings()));self.assertEqual(len(self.service.items()),2)
    def test_local_text_ingestion_duplicate_hash_and_page_citation(self):
        p={'name':'example.txt','content':base64.b64encode(b'Example document').decode()}
        doc=self.service.ingest(p);again=self.service.ingest(p);self.assertEqual(doc['id'],again['id']);self.assertEqual(doc['pages'],['Example document'])
        f=self.service.save_finding({'title':'Page 1','source':'local','capture':{'attachments':[doc['id']],'reference':'attachment:'+doc['id']+'#page=1','excerpt':'Example'}})
        self.assertEqual(self.service.ingest(p)['duplicates'],[f['id']]);self.assertEqual(self.service.attachment(doc['id'])[-1],b'Example document')
    def test_bad_file_and_unknown_attachment_rejected(self):
        for p in [{'name':'bad.exe','content':'QQ=='},{'name':'bad.txt','content':'bad encoding'},{'name':'bad.pdf','content':'QQ=='},{'name':'bad.png','content':'QQ=='}]:
            with self.assertRaises(ValueError):self.service.ingest(p)
        with self.assertRaises(ValueError):self.service.save_finding({'title':'Bad','capture':{'attachments':['a'*24]}})
    def test_pdf_and_screenshot_ocr_stay_local(self):
        from PIL import Image
        from pypdf import PdfWriter
        out=io.BytesIO();writer=PdfWriter();writer.add_blank_page(width=300,height=200);writer.write(out)
        with patch('investigation.local_ocr',return_value='Example OCR') as ocr:
            doc=self.service.ingest({'name':'scan.pdf','content':base64.b64encode(out.getvalue()).decode()})
            self.assertEqual(doc['pages'],['Example OCR']);ocr.assert_called_once()
        out=io.BytesIO();Image.new('RGB',(100,100),'white').save(out,format='PNG')
        with patch('investigation.local_ocr',return_value='Screenshot text'):
            doc=self.service.ingest({'name':'screen.png','content':base64.b64encode(out.getvalue()).decode()})
            self.assertEqual(doc['pages'],['Screenshot text'])
    def test_ocr_failure_preserves_original(self):
        from PIL import Image
        out=io.BytesIO();Image.new('RGB',(100,100),'white').save(out,format='PNG')
        with patch('investigation.local_ocr',side_effect=ValueError('No language')):
            doc=self.service.ingest({'name':'screen.png','content':base64.b64encode(out.getvalue()).decode()})
        self.assertIn('unavailable',doc['notice']);self.assertEqual(self.service.attachment(doc['id'])[-1],out.getvalue())
    def test_encrypted_roundtrip_preview_and_idempotent_import(self):
        entity=self.entity();self.finding(entity_ids=[entity['id']])
        doc=self.service.ingest({'name':'example.txt','content':'RXhhbXBsZQ=='})
        self.service.save_finding({'title':'Document','capture':{'attachments':[doc['id']]}})
        bundle=self.service.export_bundle('a strong example password');self.assertTrue(bundle['encrypted']);self.assertNotIn(b'Preserved text',base64.b64decode(bundle['content']))
        with self.assertRaises(ValueError):self.service.restore({'content':bundle['content'],'password':'wrong'})
        with self.db() as db:
            for table in ('findings','investigation_items','attachments'):db.execute('DELETE FROM '+table)
        p={'content':bundle['content'],'password':'a strong example password'}
        preview=self.service.restore(p);self.assertEqual(preview['counts']['findings'],2);self.assertEqual(self.service.findings(),[])
        self.service.restore(dict(p,confirm=True));self.assertEqual(len(self.service.findings()),2);self.assertEqual(self.service.attachment(doc['id'])[-1],b'Example')
        self.assertTrue(all(n==0 for n in self.service.restore(p)['counts'].values()))
    def test_corrupted_attachment_and_conflicts_are_atomic(self):
        f=self.finding();bundle=self.bundle()
        corrupted=self.mutate_bundle(bundle,lambda tables:tables['findings'][0].__setitem__(1,json.dumps(dict(f,notes='Conflict'))))
        with self.assertRaises(ValueError):self.service.restore({'content':corrupted,'confirm':True})
        self.assertEqual(self.service.findings()[0]['notes'],'Assessment')
        doc=self.service.ingest({'name':'example.txt','content':'RXhhbXBsZQ=='})
        corrupted=self.mutate_bundle(self.bundle(),lambda tables:tables['attachments'][0].__setitem__(-1,'QQ=='))
        with self.assertRaises(ValueError):self.service.restore({'content':corrupted,'confirm':True})
    def test_dangling_references_and_future_schema_rejected(self):
        f=self.finding();content=self.bundle()
        bad=self.mutate_bundle(content,lambda tables:tables['findings'][0].__setitem__(1,json.dumps(dict(f,entity_ids=['b'*24]))))
        with self.assertRaises(ValueError):self.service.restore({'content':bad,'confirm':True})
        raw=json.loads(base64.b64decode(content));raw['schema']=99
        with self.assertRaises(ValueError):self.service.restore({'content':base64.b64encode(json.dumps(raw).encode()).decode()})
    def test_active_report_blocks_backup(self):
        with self.db() as db:db.execute('INSERT INTO case_runs VALUES (?,?,?)',('a'*24,'b'*24,json.dumps({'status':'running'})))
        with self.assertRaises(ValueError):self.bundle()

class ReportComparisonTests(unittest.TestCase):
    def test_changes_absence_and_coverage(self):
        def record(title,detail,ref):return {'title':title,'detail':detail,'reference':ref,'provider':'Index','origin':'retrieved','matched_inputs':['names: Example']}
        before={'case_id':'a','status':'complete','records':[record('Original','Old','https://example.com/1'),record('Absent','X','https://example.com/2')],'coverage':[{'status':'ok'}]}
        after={'case_id':'a','status':'complete','records':[record('Original','New','https://example.com/1'),record('Added','X','https://example.com/3')],'coverage':[{'status':'error'}]}
        result=compare_reports(before,after);self.assertEqual(len(result['changed']),1);self.assertEqual(len(result['added']),1);self.assertEqual(len(result['absent']),1);self.assertIn('does not establish deletion',result['notice'])
        self.assertEqual(result['coverage_after'][0]['status'],'error')
        with self.assertRaises(ValueError):compare_reports(before,dict(after,case_id='b'))
    def test_multiple_records_from_same_index_are_not_overwritten(self):
        r={'provider':'Index','source':'query','matched_inputs':['example'],'title':'One','detail':'First'}
        run={'case_id':'a','status':'complete','records':[r,dict(r,title='Two',detail='Second')]}
        result=compare_reports(run,copy.deepcopy(run));self.assertEqual(result['added'],[]);self.assertEqual(result['changed'],[]);self.assertEqual(result['absent'],[])
