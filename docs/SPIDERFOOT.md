# Import SpiderFoot JSON

Vidocq 2.8.0 imports the standard flat JSON scan-results export from open-source SpiderFoot 4.0 and the compatible upstream exporter. Format reference: [`scanexportjsonmulti` in SpiderFoot](https://github.com/smicallef/spiderfoot/blob/v4.0/sfwebui.py). This is an offline file adapter; SpiderFoot does not need to be installed or running on the Vidocq computer.

1. In SpiderFoot, export scan results as JSON. Choose the scan-results export, not scan options, logs, correlation-only output, CSV or graph JSON. HX-specific formats have not been validated.
2. In Vidocq open Investigation → SpiderFoot import.
3. Choose the JSON file and optionally assign the imported records to an existing case.
4. Select Preview SpiderFoot import. Review the record counts, sample, false-positive count and unresolved-source counts.
5. Select Import reviewed results. Review findings in Notebook and the proposed discovery links under Relationships.

Each file is limited to 10 MB and 5,000 records. Split larger exports into separate valid arrays. UTF-8 with or without a BOM is accepted. Invalid or incompatible input fails without importing partial records. A new preview is required after changing the file or destination case.

## What is preserved

The original JSON file and SHA-256 are retained as a local attachment. Each finding preserves its complete original record, data value, event type, module, source value, scan name/target, last-seen text, false-positive flag, original export row and import timestamp. Unknown extra fields are retained in the original record. Original evidence remains separate from editable analyst assessments. Download the original JSON from the finding's evidence details.

False-positive records are retained with Rejected status and their original SpiderFoot flag. Other records start as Unverified lead. Discovered values become type-aware entities, scoped to the export's scan name/target and destination case. Identical text with different event types is kept separate.

For a result whose `source_data` matches exactly one typed value in the same scan scope, Vidocq creates a source → result discovery link supported by that finding. If there is no matching source or several possible source types, an explicitly unresolved source node is retained. Self-links are omitted from the relationship list and counted in preview; their source fields remain in the finding. Links start Proposed (or Rejected when SpiderFoot flagged the supporting result).

These links describe exported discovery provenance. They are not verified identity/ownership assertions and do not establish independent corroboration.

## Limits of the export

SpiderFoot's standard JSON export omits event IDs, source event hashes, scan IDs and timestamp timezone offsets. Vidocq cannot recreate exact event ancestry or convert its last-seen text reliably to UTC. It preserves that text without filling in a retrieval timestamp. Import time is recorded separately. The app does not create timeline event dates from these values automatically.

Different scans with identical names and targets cannot be distinguished by this format. Use distinct scan names when exporting. Matching a unique value indicates a discovery-value connection, not an exact event-parent reconstruction. Ambiguous and missing sources remain visible.

Stable import IDs prevent repeat imports of the same original records into the same destination case from overwriting assessments or duplicating findings and links, including when rows are reordered. A changed original record is retained as a distinct observation. Importing into a different destination case creates separate scoped records. Later manual edits, merges and splits remain intact; re-import does not reverse them.

## Cases, reports and backups

Case assignment organizes the imported notebook evidence. Explicitly select relevant findings in Cases & reports to include them in a report snapshot. Existing per-report selection limits still apply. Proposed relationships are analyst-review context, not new online verification. Workspace bundles include the original JSON, all imported records, discovery links and subsequent assessments; existing validated/encrypted backup and restore work normally.

## Privacy

Import, preview and confirmation are local operations. They do not connect to SpiderFoot, launch scans, execute modules, resolve DNS, visit source URLs or transmit records to any provider. Imported URLs and markup are displayed as escaped text. Choosing a local file does not automatically start research. Files and records are stored in the existing unencrypted SQLite workspace; optional bundle encryption protects exported backups only.
