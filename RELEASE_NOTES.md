# Vidocq 2.7.0 — Investigation workspace

This update adds all seven investigation workflow improvements:

- Structured, preserved evidence captures with stable IDs and separate editable assessments.
- Notebook editing, assessment history, tags, search, case/entity filters and duplicate review.
- Evidence-backed entity relationships with Proposed/Supported/Rejected assessments and explicit merge/split workflows.
- Timelines with event dates, approximate dates/ranges, source/entity/case filters and separate discovery dates.
- Report snapshot comparisons with newly returned, changed and absent records plus source coverage.
- Local PDF, text and screenshot imports, Windows OCR, original-file hashes and page/passage citations.
- Complete workspace backup and restore, optional authenticated encryption, preview, hash/reference validation and atomic import.

Existing notebooks and immutable reports remain compatible. New report snapshots retain relevant analyst relationship/timeline assertions.

OCR requires Windows 10/11 and installed OCR language support; review extracted text against originals. Imports are limited to 10 MB, 100 PDF pages and up to 20 scanned pages for OCR. Workspace bundles are limited to 50 MB. Bundle encryption does not encrypt the local working database. Conflicting restore records are rejected rather than overwritten; use a separate empty workspace for an older conflicting backup.

Download Vidocq.exe for Windows 10/11 x64. The source-code archive is for development. See docs/INVESTIGATION.md for the workflows and limits.
