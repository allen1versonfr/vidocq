# Investigation workspace — 2.7.0

## Evidence and notebook

Save a returned search record to preserve its provider, source request, reference URL, query, retrieval time, original excerpt and stable evidence ID. Analyst assessments, tags, evidence status, assigned cases and entities can be edited independently. Assessment history remains available. Original captures and attachments cannot be changed by editing an assessment. Earlier notebooks load without rewriting their notes; missing historical provenance is marked unknown rather than inferred.

Notebook search covers titles, excerpts, assessments, references, IDs and tags. Filter by status, case and entity, or show potential duplicates. Duplicate suggestions compare provider, reference/source and captured excerpt; they do not assert independent corroboration or automatically delete findings. Assigning a finding to a case organizes it; explicitly select it in Cases & reports to include it in a generated report.

## Entities, relationships and timeline

Open Investigation. Create named entities representing people, organizations or identifiers. Select a case filter before creating a record to assign it to that case. Each relationship requires two distinct entities and one or more saved findings. Choose Proposed, Supported or Rejected, and record the reasoning. These are analyst assertions, not automatic identity matches.

Merge moves all source evidence assignments to a destination entity. Split moves selected evidence assignments to a separate entity created beforehand. Both retain source entities and an audit record. Existing relationship endpoints and event assertions are retained for explicit review; merging assignments does not silently rewrite past assertions.

Timeline events have exact, approximate or ranged event dates, supporting evidence and optional entities. Event dates are separate from evidence retrieval/saving dates. Filter by case, entity, source and overlapping date range. Reports snapshot investigation records explicitly assigned to the case or supported by selected notebook findings; exports label them as supplied analyst assertions. Editing these records does not change older report snapshots.

## Compare snapshots

In Cases & reports choose two completed snapshots from the same case. The comparison lists newly returned records, changed titles/snippets and records absent from the later run, alongside both coverage logs. Matching uses provider, source/reference, origin and matched inputs, retaining multiple records per source. Different inputs, result limits and provider errors can explain differences. Absence from an index response does not establish removal from the original source. Comparisons do not run searches automatically.

## Local document evidence

Import PDFs, UTF-8 text, PNG, JPEG or WebP files up to 10 MB. Original bytes, original filename and SHA-256 are stored locally in the existing SQLite database. Files are deduplicated by hash. Text is extracted locally; no document, screenshot or OCR text is sent to a provider. PDF text extraction is bounded to 100 pages and one million extracted characters. PDFs must be unlocked; a page's decompressed content stream is limited to 5 MB.

Scanned PDF pages use a bundled PDF renderer and Windows OCR, on up to 20 scanned pages per import. Screenshot OCR uses Windows' installed OCR language support and a copy resized to at most 1800 pixels per side. Import images up to 20 megapixels. Each OCR operation has a 60-second timeout. If OCR is unavailable or fails, the original is preserved and the app reports the extraction gap. Review OCR against the original: recognition can be wrong. Unsupported/oversized inputs are rejected.

Choose a page, highlight a passage in the extracted text, and save it as evidence. With no selection the page text is saved. The finding cites the attachment and page; the preserved excerpt stays separate from later assessments. Download original attachments from Notebook. Downloads use an inert binary response; the app never embeds or executes imported documents. Opening a downloaded original in another application is outside Vidocq.

## Backup and restore

Download a complete workspace bundle under Investigation → Backup. It contains findings, history, captures, original attachments, cases, report snapshots, entities, relationships and timeline events. The bundle schema is versioned. It excludes in-memory provider keys and update tokens. Finish active report runs before backup.

Optional encryption uses AES-256-GCM with a random nonce and salt, and a password-derived scrypt key (N=16384, r=8, p=1). Use a password of at least 12 characters. The password is not stored; losing it makes the encrypted backup unrecoverable. Encryption protects the exported bundle, not the working SQLite database or ordinary report exports.

Restore accepts bundles up to 50 MB. Select the bundle, enter its password if encrypted, then Validate and preview restore. Review the counts and select Import validated records. The server revalidates the bundle and imports the complete transaction. Existing identical records are skipped. Conflicting IDs, unsupported schema versions, invalid hashes and missing linked records abort the import without changes. Restore a conflicting historical bundle into a separate empty workspace using `VIDOCQ_DATA`; existing local edits are never overwritten.

Do not confuse the older notebook JSON export or individual report JSON with a workspace bundle. Those remain readable exports; only workspace bundles support full restoration. Protect unencrypted exports and originals with device access controls.
