# Vidocq 2.8.0 — SpiderFoot import

Bring SpiderFoot collection results into Vidocq for evidence review and reporting.

- Investigation → SpiderFoot import accepts standard flat JSON scan-results exports from open-source SpiderFoot, up to 10 MB / 5,000 records.
- Preview records, counts and source-link gaps before confirming a local import.
- Preserve original JSON/hash, complete records, modules, source values, last-seen text and false-positive flags.
- Create type-aware entities and proposed discovery relationships, with optional case assignment.
- Re-importing identical records preserves analyst edits and avoids duplicate findings/links.
- Imported records and original files are included in workspace backup/restore.

No scans or source visits run during import. Standard exports omit event/scan IDs and timezone offsets; exact event ancestry and UTC timestamps cannot be recreated. Ambiguous/missing source values remain explicitly unresolved. Imported relationships are discovery leads, not proof of identity or ownership. HX-specific export formats are not validated.

See docs/SPIDERFOOT.md for the workflow, limits and privacy handling. Existing notebooks and reports remain compatible.
