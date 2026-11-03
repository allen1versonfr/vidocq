"""Offline adapter for SpiderFoot's scanexportjsonmulti flat JSON export.

Schema reference: smicallef/spiderfoot sfwebui.py, scanexportjsonmulti.
No SpiderFoot code is executed and no exported URL is visited.
"""
import base64
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from investigation import identifier, now, text, key, MAX_FILE

FIELDS = ('data', 'event_type', 'module', 'source_data', 'last_seen', 'scan_name', 'scan_target')
MAX_ROWS = 5000
NOTICE = ('Imported SpiderFoot results are supplied, unverified leads. Discovery links describe '
          'what SpiderFoot reported, not ownership or identity. Standard JSON omits event IDs '
          'and timestamp offsets; exact event ancestry and UTC times cannot be reconstructed. '
          'Scans with identical names and targets cannot be distinguished by this export.')

def stable(*parts):
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()[:24]

def parse_export(payload):
    name = text(payload.get('name', ''), 200)
    if Path(name).suffix.lower() != '.json': raise ValueError('Choose a SpiderFoot JSON results export.')
    content = payload.get('content', '')
    if not isinstance(content, str) or len(content) > 14_000_000: raise ValueError('Choose a JSON export up to 10 MB.')
    try:
        raw = base64.b64decode(content, validate=True)
        if not raw or len(raw) > MAX_FILE: raise ValueError()
        # Duplicate keys and non-finite numbers are rejected rather than silently altered.
        def pairs(values):
            result = {}
            for k, v in values:
                if k in result: raise ValueError()
                result[k] = v
            return result
        def invalid(value): raise ValueError()
        rows = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs, parse_constant=invalid)
    except (ValueError, TypeError, RecursionError):
        raise ValueError('Invalid UTF-8 JSON export. Nothing was imported.')
    if not isinstance(rows, list) or not rows or len(rows) > MAX_ROWS:
        raise ValueError('Use a flat SpiderFoot results array with 1–5,000 records. Split larger exports.')
    for number, row in enumerate(rows, 1):
        if not isinstance(row, dict) or any(k not in row for k in FIELDS) or 'false_positive' not in row:
            raise ValueError(f'Record {number} is not a standard SpiderFoot JSON result. Export scan results as JSON, not scan options, logs or graph data.')
        for field in FIELDS:
            text(row[field], 100000 if field in ('data', 'source_data') else 2000)
        if not row['data'] or not row['event_type']: raise ValueError(f'Record {number} has no data or event type.')
        if type(row['false_positive']) not in (int, str, bool) or str(row['false_positive']).lower() not in ('0', '1', 'true', 'false'):
            raise ValueError(f'Record {number} has an invalid false-positive flag.')
        if len(json.dumps(row, ensure_ascii=False)) > 150000:
            raise ValueError(f'Record {number} exceeds the preserved-record size limit.')
    return name, raw, rows

def import_spiderfoot(service, payload):
    name, raw, rows = parse_export(payload)
    service.initialize()
    case_id = payload.get('case_id', '')
    if not isinstance(case_id, str): raise ValueError('Choose an existing destination case or no case assignment.')
    if case_id: key(case_id)
    timestamp = now()
    attachment_id = identifier()
    digest = hashlib.sha256(raw).hexdigest()
    entities, findings, relationships = {}, {}, {}
    candidates = defaultdict(set)
    # Type-aware nodes remain distinct even when their text is identical.
    def scope(row): return (row['scan_name'], row['scan_target'])
    def entity(row, event_type, value, unresolved=False):
        eid = stable('spiderfoot-entity-v1', case_id, scope(row), event_type, value)
        if eid not in entities:
            entities[eid] = {'id': eid, 'label': (event_type + ': ' + value)[:500],
                             'notes': 'Imported SpiderFoot value; not a verified identity.' + (' Source event type/parent is unresolved.' if unresolved else ''),
                             'case_ids': [case_id] if case_id else [], 'created_at': timestamp, 'updated_at': timestamp,
                             'spiderfoot': {'scan_name': row['scan_name'], 'scan_target': row['scan_target'], 'event_type': event_type, 'value': value, 'unresolved_source': unresolved}}
        return eid
    for row in rows:
        eid = entity(row, row['event_type'], row['data'])
        candidates[(scope(row), row['data'])].add(eid)
    ambiguous = missing = self_links = duplicates = 0
    for row_number, row in enumerate(rows, 1):
        eid = entity(row, row['event_type'], row['data'])
        fid = stable('spiderfoot-finding-v1', case_id, row)
        if fid in findings:
            duplicates += 1
            continue
        source = row['source_data']
        parent = None
        if source:
            matches = candidates.get((scope(row), source), set())
            if len(matches) == 1: parent = next(iter(matches))
            else:
                ambiguous += bool(matches)
                missing += not matches
                parent = entity(row, 'Unresolved source', source, True)
        flagged = str(row['false_positive']).lower() in ('1', 'true')
        origin = {'scan_name': row['scan_name'], 'scan_target': row['scan_target'],
                  'module': row['module'], 'event_type': row['event_type'], 'last_seen': row['last_seen'],
                  'false_positive': row['false_positive'], 'source_data': source, 'record': row,
                  'export_row': row_number, 'imported_at': timestamp, 'timestamp_timezone': 'Not provided by SpiderFoot export'}
        findings[fid] = {'id': fid, 'title': ('SpiderFoot · ' + row['event_type'] + ' · ' + row['data'])[:500],
                         'source': 'SpiderFoot export · ' + name, 'notes': ('SpiderFoot marked this result false positive; retained for review.' if flagged else 'Imported lead; relevance has not been verified.'),
                         'status': 'Rejected' if flagged else 'Unverified lead', 'tags': ['spiderfoot', row['event_type'][:60]],
                         'case_ids': [case_id] if case_id else [], 'entity_ids': [eid], 'history': [], 'date': timestamp, 'updated_at': timestamp,
                         'capture': {'provider': 'SpiderFoot / ' + row['module'], 'reference': 'attachment:' + attachment_id + '#row=' + str(row_number),
                                     'query': row['scan_target'], 'retrieved_at': '', 'excerpt': row['data'],
                                     'origin': 'spiderfoot-import', 'attachments': [attachment_id], 'spiderfoot': origin}}
        if parent == eid: self_links += 1
        elif parent:
            rid = stable('spiderfoot-relationship-v1', case_id, fid)
            relationships[rid] = {'id': rid, 'label': 'SpiderFoot discovery via ' + row['module'][:200],
                                  'notes': 'Reported source → result. This is discovery provenance, not proof of ownership. ' + ('SpiderFoot flagged the supporting result false positive.' if flagged else ''),
                                  'case_ids': [case_id] if case_id else [], 'created_at': timestamp, 'updated_at': timestamp,
                                  'entity_ids': [parent, eid], 'evidence_ids': [fid], 'status': 'Rejected' if flagged else 'Proposed',
                                  'spiderfoot': {'record_id': fid, 'source_data': source}}
    summary = {'records': len(rows), 'unique_records': len(findings), 'duplicate_rows': duplicates,
               'entities': len(entities), 'relationships': len(relationships), 'ambiguous_sources': ambiguous,
               'missing_sources': missing, 'self_links_omitted': self_links,
               'false_positives': sum(f['status']=='Rejected' for f in findings.values())}
    with service.database() as db:
        db.execute('BEGIN IMMEDIATE')
        if case_id: service._exists(db, 'cases', [case_id])
        existing_attachment = db.execute('SELECT id FROM attachments WHERE sha256=?', (digest,)).fetchone()
        if existing_attachment:
            previous = attachment_id; attachment_id = existing_attachment[0]
            for f in findings.values():
                f['capture']['attachments'] = [attachment_id]
                f['capture']['reference'] = f['capture']['reference'].replace(previous, attachment_id, 1)
        counts = {'findings': 0, 'entities': 0, 'relationships': 0}
        for label, table, records, kind in [('findings','findings', findings, None), ('entities','investigation_items', entities, 'entity'), ('relationships','investigation_items', relationships, 'relationship')]:
            for iid, record in records.items():
                existing = db.execute(f'SELECT * FROM {table} WHERE id=?', (iid,)).fetchone()
                if existing:
                    # Analyst changes are retained. Never replace pre-existing records.
                    stored = json.loads(existing[-1])
                    if 'spiderfoot' not in (stored.get('capture', {}) if kind is None else stored):
                        raise ValueError('An imported record ID conflicts with a local record. Nothing was imported.')
                    continue
                counts[label] += 1
                if payload.get('confirm') is True:
                    if kind: db.execute('INSERT INTO investigation_items VALUES (?,?,?)', (iid, kind, json.dumps(record)))
                    else: db.execute('INSERT INTO findings VALUES (?,?)', (iid, json.dumps(record)))
        if payload.get('confirm') is True and not existing_attachment:
            db.execute('INSERT INTO attachments VALUES (?,?,?,?,?)', (attachment_id, name, 'application/json', digest, raw))
    return {'imported': payload.get('confirm') is True, 'summary': summary, 'new_records': counts,
            'sha256': digest, 'notice': NOTICE,
            'message': 'Imported locally. Existing evidence and analyst assessments were preserved.' if payload.get('confirm') is True else 'Validated. Review the counts, then confirm import.',
            'sample': [{'event_type': r['event_type'], 'data': r['data'][:300], 'module': r['module'], 'source_data': r['source_data'][:300]} for r in rows[:5]]}
