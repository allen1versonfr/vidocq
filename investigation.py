"""Local investigation records, evidence preservation and portable workspace bundles."""
import base64
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
from datetime import date, datetime, timezone

MAX_FILE = 10 * 1024 * 1024
MAX_BUNDLE = 50 * 1024 * 1024
STATUSES = ('Unverified lead', 'Corroborated', 'Rejected')
TABLES = {'findings': ('id', 'data'), 'cases': ('id', 'data', 'updated_at'),
          'case_runs': ('id', 'case_id', 'data'), 'investigation_items': ('id', 'kind', 'data'),
          'attachments': ('id', 'name', 'media_type', 'sha256', 'content')}

def now():
    return datetime.now(timezone.utc).isoformat()

def validate_imported_case(value):
    from case_reports import clean_case,FIELDS
    from app import normalize
    for field in FIELDS:
        if field in value and not isinstance(value[field],(list,str)):raise ValueError('Invalid imported '+field+'.')
    # Older context-only case folders remain restorable, but cannot run until edited.
    payload=dict(value)
    if not any(payload.get(f) for f in FIELDS if f!='urls'):payload['names']=['Imported context only']
    clean_case(payload,normalize)

def text(value, limit=10000):
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError('Invalid or oversized text field.')
    return value

def key(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{24}', value):
        raise ValueError('Invalid record identifier.')
    return value

def identifier():
    return secrets.token_hex(12)

def date_value(value):
    value = text(value, 10)
    if value:
        try: date.fromisoformat(value)
        except ValueError: raise ValueError('Use an ISO date: YYYY-MM-DD.')
    return value

def upgraded(finding):
    """Legacy notes remain untouched; missing provenance is explicitly unknown."""
    f = copy.deepcopy(finding)
    f.setdefault('capture', {'provider': '', 'reference': '', 'query': '', 'retrieved_at': '',
                             'excerpt': '', 'origin': 'legacy', 'attachments': []})
    for name, default in [('tags', []), ('case_ids', []), ('entity_ids', []), ('history', [])]:
        f.setdefault(name, default)
    return f

class InvestigationService:
    def __init__(self, database):
        self.database = database

    def initialize(self):
        with self.database() as db:
            db.execute('CREATE TABLE IF NOT EXISTS investigation_items (id TEXT PRIMARY KEY, kind TEXT NOT NULL, data TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS attachments (id TEXT PRIMARY KEY, name TEXT NOT NULL, media_type TEXT NOT NULL, sha256 TEXT NOT NULL, content BLOB NOT NULL)')

    def _exists(self, db, table, ids, kind=None):
        if not isinstance(ids, list) or len(ids) > 100:
            raise ValueError('Choose up to 100 related records.')
        result = list(dict.fromkeys(key(i) for i in ids))
        for i in result:
            row = db.execute(f'SELECT * FROM {table} WHERE id=?', (i,)).fetchone()
            if not row or (kind and row[1] != kind):
                raise ValueError('A related record does not exist.')
        return result

    def findings(self):
        with self.database() as db:
            return [upgraded(json.loads(r[0])) for r in db.execute('SELECT data FROM findings ORDER BY rowid DESC')]

    def save_finding(self, payload):
        self.initialize()
        with self.database() as db:
            db.execute('BEGIN IMMEDIATE')
            fid = key(payload['id']) if payload.get('id') else identifier()
            row = db.execute('SELECT data FROM findings WHERE id=?', (fid,)).fetchone()
            if payload.get('id') and not row: raise ValueError('Finding not found.')
            previous = upgraded(json.loads(row[0])) if row else None
            title = text(payload.get('title', ''), 500).strip()
            if not title: raise ValueError('A title is required.')
            status = payload.get('status', 'Unverified lead')
            if status not in STATUSES: raise ValueError('Invalid evidence status.')
            tags = payload.get('tags', [])
            if not isinstance(tags, list) or len(tags) > 30: raise ValueError('Use up to 30 tags.')
            item = dict(previous or {}, id=fid, title=title, notes=text(payload.get('notes', '')),
                        status=status, tags=list(dict.fromkeys(text(t, 60).strip() for t in tags if t)),
                        date=previous['date'] if previous else now(), updated_at=now())
            item['source'] = previous['source'] if previous else text(payload.get('source', ''), 2000)
            item['case_ids'] = self._exists(db, 'cases', payload.get('case_ids', []))
            item['entity_ids'] = self._exists(db, 'investigation_items', payload.get('entity_ids', []), 'entity')
            if previous:
                item['history'] = previous['history'] + [{k: previous.get(k) for k in ('title', 'notes', 'status', 'tags', 'case_ids', 'entity_ids', 'updated_at')}]
            else:
                capture = payload.get('capture', {})
                if not isinstance(capture, dict): raise ValueError('Invalid evidence capture.')
                item['capture'] = {k: text(capture.get(k, ''), 100000 if k == 'excerpt' else 2000)
                                   for k in ('provider', 'reference', 'query', 'retrieved_at', 'excerpt', 'origin')}
                item['capture']['attachments'] = self._exists(db, 'attachments', capture.get('attachments', []))
                item['history'] = []
            db.execute('INSERT OR REPLACE INTO findings VALUES (?,?)', (fid, json.dumps(item)))
            return item

    def items(self):
        self.initialize()
        with self.database() as db:
            return [dict(json.loads(r[1]), kind=r[0]) for r in db.execute('SELECT kind,data FROM investigation_items ORDER BY rowid')]

    def save_item(self, p):
        self.initialize()
        kind = p.get('kind')
        if kind not in ('entity', 'relationship', 'event'): raise ValueError('Invalid investigation record type.')
        with self.database() as db:
            db.execute('BEGIN IMMEDIATE')
            iid = key(p['id']) if p.get('id') else identifier()
            previous = db.execute('SELECT kind,data FROM investigation_items WHERE id=?', (iid,)).fetchone()
            if p.get('id') and (not previous or previous[0] != kind): raise ValueError('Record not found.')
            item = {'id': iid, 'label': text(p.get('label', ''), 500).strip(), 'notes': text(p.get('notes', '')),
                    'case_ids': self._exists(db, 'cases', p.get('case_ids', [])),
                    'updated_at': now(), 'created_at': json.loads(previous[1])['created_at'] if previous else now()}
            if not item['label']: raise ValueError('A label is required.')
            if kind != 'entity':
                item['evidence_ids'] = self._exists(db, 'findings', p.get('evidence_ids', []))
                if not item['evidence_ids']: raise ValueError('Select supporting evidence.')
            if kind == 'relationship':
                item['entity_ids'] = self._exists(db, 'investigation_items', p.get('entity_ids', []), 'entity')
                if len(item['entity_ids']) != 2: raise ValueError('Choose two distinct entities.')
                item['status'] = p.get('status', 'Proposed')
                if item['status'] not in ('Proposed', 'Supported', 'Rejected'): raise ValueError('Invalid relationship status.')
            if kind == 'event':
                item['entity_ids'] = self._exists(db, 'investigation_items', p.get('entity_ids', []), 'entity')
                item['start'] = date_value(p.get('start', ''))
                item['end'] = date_value(p.get('end', '')) or item['start']
                if not item['start'] or item['end'] < item['start']: raise ValueError('Enter a valid event date range.')
                item['precision'] = p.get('precision', 'Exact')
                if item['precision'] not in ('Exact', 'Approximate', 'Range'): raise ValueError('Invalid date precision.')
            db.execute('INSERT OR REPLACE INTO investigation_items VALUES (?,?,?)', (iid, kind, json.dumps(item)))
            return dict(item, kind=kind)

    def reorganize(self, p):
        """Explicit merges/splits retain the source entity and an audit trail."""
        self.initialize()
        with self.database() as db:
            db.execute('BEGIN IMMEDIATE')
            ids = self._exists(db, 'investigation_items', [p.get('source'), p.get('target')], 'entity')
            if len(ids) != 2: raise ValueError('Choose two distinct entities.')
            source, target = ids
            mode = p.get('mode')
            if mode not in ('merge', 'split'): raise ValueError('Choose merge or split.')
            selected = self._exists(db, 'findings', p.get('evidence_ids', []))
            if mode == 'split' and not selected: raise ValueError('Choose evidence to move to the separate entity.')
            changed = []
            for fid, raw in db.execute('SELECT id,data FROM findings').fetchall():
                f = upgraded(json.loads(raw))
                if source not in f['entity_ids'] or (mode == 'split' and fid not in selected): continue
                f['history'].append({'entity_ids': f['entity_ids'][:], 'updated_at': f.get('updated_at'), 'action': mode})
                f['entity_ids'] = list(dict.fromkeys(target if x == source else x for x in f['entity_ids']))
                f['updated_at'] = now()
                db.execute('UPDATE findings SET data=? WHERE id=?', (json.dumps(f), fid)); changed.append(fid)
            # Existing asserted relationships/events retain their original endpoints as history.
            raw = db.execute('SELECT data FROM investigation_items WHERE id=?', (source,)).fetchone()[0]
            entity = json.loads(raw)
            entity.setdefault('reorganizations', []).append({'mode': mode, 'target': target, 'evidence_ids': changed, 'at': now()})
            if mode == 'merge': entity['merged_into'] = target
            db.execute('UPDATE investigation_items SET data=? WHERE id=?', (json.dumps(entity), source))
            return {'moved': len(changed), 'message': 'Evidence assignments updated; original relationships and event assertions retained for review.'}

    def attachment(self, aid):
        self.initialize()
        with self.database() as db:
            r = db.execute('SELECT name,media_type,sha256,content FROM attachments WHERE id=?', (key(aid),)).fetchone()
        if not r: raise ValueError('Attachment not found.')
        return r

    def ingest(self, p):
        self.initialize()
        name = text(p.get('name', ''), 200)
        try: raw = base64.b64decode(p.get('content', ''), validate=True)
        except Exception: raise ValueError('Invalid file encoding.')
        if not raw or len(raw) > MAX_FILE: raise ValueError('Choose a file up to 10 MB.')
        suffix = Path(name).suffix.lower()
        media = {'.pdf': 'application/pdf', '.txt': 'text/plain', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}.get(suffix)
        if not media: raise ValueError('Choose PDF, UTF-8 text, PNG, JPEG or WebP.')
        pages, notice = [], ''
        if suffix == '.txt':
            try: pages = [raw.decode('utf-8-sig')]
            except UnicodeDecodeError: raise ValueError('Text files must use UTF-8.')
        elif suffix == '.pdf':
            from pypdf import PdfReader
            try:
                reader = PdfReader(io.BytesIO(raw))
                if reader.is_encrypted: raise ValueError('Unlock the PDF before importing it.')
                if len(reader.pages) > 100: raise ValueError('Use a PDF with at most 100 pages.')
                scanned = []
                for number, page in enumerate(reader.pages):
                    contents = page.get_contents()
                    if contents and len(contents.get_data()) > 5 * 1024 * 1024:
                        raise ValueError('A PDF page is too large to extract.')
                    pages.append((page.extract_text() or '')[:100000])
                    if not pages[-1].strip(): scanned.append(number)
                notice = 'PDF text extracted locally.'
                if scanned:
                    import pypdfium2 as pdfium
                    pdf = pdfium.PdfDocument(raw)
                    try:
                        with tempfile.TemporaryDirectory() as folder:
                            for number in scanned[:20]:
                                page = pdf[number]
                                try:
                                    width, height = page.get_size()
                                    bitmap = page.render(scale=min(2, 1800 / max(width, height)))
                                    try:
                                        image_path = Path(folder) / 'page.png'
                                        bitmap.to_pil().save(image_path)
                                        pages[number] = local_ocr(image_path)[:100000]
                                    finally: bitmap.close()
                                finally: page.close()
                    except (ValueError, subprocess.SubprocessError, OSError):
                        notice += ' Some scanned pages could not be OCRed; original retained. Check Windows OCR language support.'
                    finally: pdf.close()
                    notice += ' Local OCR attempted on up to 20 scanned pages; review extracted text against the original.'
            except ValueError: raise
            except Exception: raise ValueError('The PDF could not be read.')
        else:
            from PIL import Image
            try:
                with Image.open(io.BytesIO(raw)) as image:
                    if image.width * image.height > 20000000: raise ValueError('Use images up to 20 megapixels.')
                    image.load()
                    with tempfile.TemporaryDirectory() as folder:
                        image_path = Path(folder) / 'ocr.png'
                        prepared = image.convert('RGB'); prepared.thumbnail((1800,1800)); prepared.save(image_path)
                        try: pages = [local_ocr(image_path)]
                        except (ValueError, subprocess.SubprocessError, OSError) as error:
                            pages = ['']; notice = 'Original preserved. Local OCR unavailable: ' + str(error)[:300]
            except (Image.DecompressionBombError, OSError): raise ValueError('The image could not be read safely.')
        if sum(map(len, pages)) > 1000000: raise ValueError('Extracted text exceeds 1 million characters; split the document.')
        aid = identifier(); digest = hashlib.sha256(raw).hexdigest()
        with self.database() as db:
            existing = db.execute('SELECT id FROM attachments WHERE sha256=?', (digest,)).fetchone()
            if existing: aid = existing[0]
            else: db.execute('INSERT INTO attachments VALUES (?,?,?,?,?)', (aid, name, media, digest, raw))
        return {'id': aid, 'name': name, 'sha256': digest, 'pages': pages, 'notice': notice,
                'duplicates': [f['id'] for f in self.findings() if aid in f['capture'].get('attachments', [])]}

    def export_bundle(self, password=''):
        self.initialize()
        with self.database() as db:
            db.execute('BEGIN')
            tables = {}
            for table in TABLES:
                rows = [list(r) for r in db.execute(f'SELECT * FROM {table}')]
                if table == 'attachments':
                    for row in rows: row[-1] = base64.b64encode(row[-1]).decode()
                tables[table] = rows
            if any(json.loads(r[2]).get('status') in ('queued','running') for r in tables['case_runs']):
                raise ValueError('Wait for active report generation before backing up.')
        raw = json.dumps({'format': 'vidocq-workspace', 'schema': 1, 'created_at': now(), 'tables': tables}).encode()
        if len(raw) > MAX_BUNDLE: raise ValueError('Workspace exceeds the 50 MB bundle limit.')
        if password:
            if len(password) < 12: raise ValueError('Use a backup password of at least 12 characters.')
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
            derived = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
            raw = b'VIDOCQ1\n' + salt + nonce + AESGCM(derived).encrypt(nonce, raw, b'vidocq-workspace-v1')
        return {'content': base64.b64encode(raw).decode(), 'encrypted': bool(password)}

    def _bundle(self, content, password):
        try:
            raw = base64.b64decode(content, validate=True)
            if len(raw) > MAX_BUNDLE + 100: raise ValueError()
            if raw.startswith(b'VIDOCQ1\n'):
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                salt, nonce = raw[8:24], raw[24:36]
                derived = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
                raw = AESGCM(derived).decrypt(nonce, raw[36:], b'vidocq-workspace-v1')
            bundle = json.loads(raw)
            if bundle['format'] != 'vidocq-workspace' or bundle['schema'] != 1: raise ValueError()
            tables = bundle['tables']
            if set(tables) != set(TABLES): raise ValueError()
            for table, columns in TABLES.items():
                if not isinstance(tables[table], list) or len(tables[table]) > 100000: raise ValueError()
                seen = set()
                for row in tables[table]:
                    if not isinstance(row, list) or len(row) != len(columns): raise ValueError()
                    key(row[0])
                    if row[0] in seen: raise ValueError()
                    seen.add(row[0])
                    if table == 'attachments':
                        row[-1] = base64.b64decode(row[-1], validate=True)
                        if len(row[-1]) > MAX_FILE or hashlib.sha256(row[-1]).hexdigest() != row[3]: raise ValueError()
                        text(row[1], 200); text(row[2], 100)
                    else:
                        parsed = json.loads(row[columns.index('data')])
                        if not isinstance(parsed, dict) or parsed.get('id') != row[0]: raise ValueError()
                        if table == 'findings':
                            if not all(isinstance(parsed.get(k),str) for k in ('title','notes','source','date')): raise ValueError()
                            if parsed.get('status') not in STATUSES: raise ValueError()
                            f = upgraded(parsed)
                            if not isinstance(f['capture'],dict) or not isinstance(f['history'],list): raise ValueError()
                            if any(not isinstance(t,str) for t in f['tags']): raise ValueError()
                            if any(not isinstance(f['capture'].get(k,''),str) for k in ('provider','reference','query','retrieved_at','excerpt','origin')): raise ValueError()
                        elif table == 'cases':
                            if not isinstance(parsed.get('title'), str) or not isinstance(parsed.get('notebook_ids', []), list): raise ValueError()
                            validate_imported_case(parsed)
                            for decision in parsed.get('account_decisions',[]):
                                from discovery_review import canonical_reference
                                canonical_reference(decision['reference'])
                                if decision.get('status') not in ('Confirmed','Rejected','Unverified') or not isinstance(decision.get('reason'),str):raise ValueError()
                        elif table == 'case_runs':
                            if parsed.get('case_id') != row[1] or parsed.get('status') not in ('complete', 'cancelled', 'interrupted', 'error', 'failed'): raise ValueError()
                            if not isinstance(parsed.get('records'), list) or not isinstance(parsed.get('case'), dict): raise ValueError()
                            validate_imported_case(parsed['case'])
                            from restore_schema import validate_report
                            validate_report(parsed)
                            if len(parsed['records'])>10000:raise ValueError()
                            for record in parsed['records']:
                                if not isinstance(record,dict) or any(not isinstance(record.get(k),str) for k in ('id','title','detail')):raise ValueError()
                                if not re.fullmatch(r'R[0-9]{1,8}',record['id']):raise ValueError()
                                if not isinstance(record.get('reference',''),str) or not isinstance(record.get('matched_inputs',[]),list):raise ValueError()
                            for field in ('coverage','prepared_searches','supplied_findings'):
                                if not isinstance(parsed.get(field,[]),list) or any(not isinstance(r,dict) for r in parsed.get(field,[])):raise ValueError()
                        elif table == 'investigation_items':
                            if row[1] not in ('entity', 'relationship', 'event') or not isinstance(parsed.get('label'), str): raise ValueError()
                            if not isinstance(parsed.get('notes'),str) or not isinstance(parsed.get('created_at'),str): raise ValueError()
                            if row[1] == 'relationship' and (len(parsed.get('entity_ids',[])) != 2 or parsed.get('status') not in ('Proposed','Supported','Rejected')): raise ValueError()
                            if row[1] == 'event':
                                start,end=date_value(parsed.get('start','')),date_value(parsed.get('end',''))
                                if not start or end<start or parsed.get('precision') not in ('Exact','Approximate','Range'): raise ValueError()
            return tables
        except Exception: raise ValueError('Invalid bundle, unsupported schema, or incorrect password. Nothing was imported.')

    def restore(self, p):
        self.initialize()
        tables = self._bundle(p.get('content', ''), p.get('password', ''))
        conflicts, added = [], {}
        with self.database() as db:
            db.execute('BEGIN IMMEDIATE')
            # Never overwrite local records. Exact repeats are idempotent.
            for table, columns in TABLES.items():
                added[table] = 0
                for row in tables[table]:
                    existing = db.execute(f'SELECT * FROM {table} WHERE id=?', (row[0],)).fetchone()
                    if existing and list(existing) != row: conflicts.append(table + ':' + row[0])
                    elif not existing: added[table] += 1
            if conflicts: raise ValueError('Bundle conflicts with existing records. Restore into a separate empty workspace. No records changed.')
            # Validate the complete reference graph before writing any rows.
            available = {t: {r[0] for r in tables[t]} | {r[0] for r in db.execute(f'SELECT id FROM {t}')} for t in TABLES}
            entities = {r[0] for r in tables['investigation_items'] if r[1]=='entity'} | {r[0] for r in db.execute("SELECT id FROM investigation_items WHERE kind='entity'")}
            def refs(values, table):
                if not isinstance(values, list) or any(key(v) not in available[table] for v in values): raise ValueError('Bundle contains missing related records.')
            for table in ('findings', 'cases', 'case_runs', 'investigation_items'):
                for row in tables[table]:
                    item = json.loads(row[TABLES[table].index('data')])
                    refs(item.get('case_ids', []), 'cases')
                    refs(item.get('entity_ids', []), 'investigation_items')
                    if any(i not in entities for i in item.get('entity_ids', [])): raise ValueError('A linked entity has the wrong record type.')
                    refs(item.get('evidence_ids', item.get('notebook_ids', [])), 'findings')
                    if table == 'findings': refs(upgraded(item)['capture'].get('attachments', []), 'attachments')
                    if table == 'case_runs': refs([row[1]], 'cases')
            if p.get('confirm') is True:
                for table, columns in TABLES.items():
                    db.executemany(f'INSERT OR IGNORE INTO {table} VALUES ({",".join("?" for _ in columns)})', tables[table])
        return {'counts': added, 'imported': p.get('confirm') is True, 'message': 'Imported without overwriting existing records.' if p.get('confirm') is True else 'Validated. Confirm to import these records.'}

def local_ocr(path):
    if os.name != 'nt': raise ValueError('Windows OCR requires Windows 10/11 and an installed OCR language.')
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                             '-File', str(root / 'scripts/local_ocr.ps1'), '-ImagePath', str(path)],
                            capture_output=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode: raise ValueError('Windows OCR could not extract text. Check installed language support.')
    return result.stdout.decode('utf-8-sig').strip()

def compare_reports(before, after):
    if before['case_id'] != after['case_id']: raise ValueError('Choose snapshots from the same case.')
    if before['status'] != 'complete' or after['status'] != 'complete': raise ValueError('Choose two completed snapshots.')
    def identity(r): return (r.get('provider'), r.get('reference') or r.get('source'), tuple(sorted(r.get('matched_inputs', []))), r.get('origin'))
    def index(run):
        result = {}
        for r in run['records']: result.setdefault(identity(r), []).append(r)
        return result
    old, new = index(before), index(after)
    added, changed, absent = [], [], []
    for k, rows in new.items():
        prior = old.get(k, [])
        unmatched = prior[:]
        fresh = []
        for row in rows:
            match = next((x for x in unmatched if (x.get('title'), x.get('detail')) == (row.get('title'), row.get('detail'))), None)
            if match is not None: unmatched.remove(match)
            else: fresh.append(row)
        for left, right in zip(unmatched, fresh): changed.append({'before': left, 'after': right})
        added.extend(fresh[len(unmatched):])
        absent.extend(unmatched[len(fresh):])
    for k, rows in old.items():
        if k not in new: absent.extend(rows)
    return {'added': added, 'changed': changed, 'absent': absent, 'coverage_before': before.get('coverage', []),
            'coverage_after': after.get('coverage', []), 'notice': 'Absent means not returned in this run; it does not establish deletion. Compare coverage failures and input changes before interpreting differences.'}
