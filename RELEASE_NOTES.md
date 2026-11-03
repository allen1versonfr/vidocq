# Vidocq 2.13.0 - Reviewable investigations and scoped burn

- Parse supported public profile links as handles, avoid shared-platform domain pivots and search location alternatives separately.
- Preserve each Maigret site's outcome and distinguish raw records, relevant candidates and analyst-confirmed accounts.
- Remember per-case account decisions/history, exclude known-rejected site/handle combinations and preserve immutable prior reports.
- Capture reviewed browser excerpts with their source/query as user-supplied case evidence.
- Add Burn Vidocq with exact-path preview and typed confirmation. It deletes named workspace/log files and optionally the current Windows executable/adjacent update backup after exit. Unrelated files are preserved. It does not promise forensic erasure or removal of external exports, backups or browser/OS records.

The local LLM assessment recommends an optional citation-validated drafting layer after deterministic fixes. No model is bundled or downloaded.

Guides: docs/REVIEW_AND_BURN.md and docs/LOCAL_LLM_ASSESSMENT.md. Deletion tests use disposable fixtures only; no personal investigation data is included in this release.
