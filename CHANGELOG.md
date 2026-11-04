# 2.17.1 — Evidence quality and retrieval diagnosis

Separate discovery/category pages from account candidates; retain them in the evidence trail but prevent automatic clue expansion and AI association claims from them. Prioritize observed profiles and identifier matches before the model context limit. Distinguish candidate records from distinct candidate profile URLs. Apply bounded query variations to discovery-only results as well as empty searches. Replace model-written relationship explanations with neutral labels beside exact validated quotations. Add an offline control diagnostic with distinct not-searched, incomplete, empty, wrong-result and post-retrieval-loss stages.

# 2.17.0

Added guided instagrapi operator login with 2FA, encrypted session retention and explicit reconnect; optional encrypted Serper/SerpApi search connections; reviewed/direct public-profile metadata and platform-scoped ID/link graphs; bounded empty-result variations; guided new-report continuation; source-quoted AI comparisons/next evidence; paired dated checker controls with history/fingerprints. See docs/GUIDED_INSTAGRAM_LOGIN.md. Live account/provider authentication requires user-supplied credentials; private benchmarks are not shipped.

# 2.16.0

Added managed collector/startup setup, encrypted Osintgram provider credentials, native reviewed-browser relay, active bounded local-AI planning/search/link/synthesis, explicit-link follow-ups, dated checker quarantine and clearer incomplete-coverage reports. See docs/AUTOMATED_SETUP.md.

# 2.15.0

Added optional managed local AI setup in first-run/Updates flows, pinned resumable downloads, automatic authenticated runtime startup, Vulkan/CPU fallback, persisted settings/assets, real-model checks and guarded managed-file deletion. See docs/LOCAL_AI_SETUP.md.

# 2.14.0

Added reviewed Chrome/Firefox capture helper, Photon JSON import, separately approved bounded public-link capture, query variants and historical aliases, cited link evidence, an Instagram checker hold/public GitHub canary, and optional local query/excerpt drafting. See docs/DISCOVERY_WORKBENCH.md for setup and limits.

# 2.13.0

Added profile/location planning fixes, per-site diagnostics, persistent account decisions, browser evidence capture, meaningful report counts and scoped preview/confirmation-based local cleanup. Added local LLM assessment; no model download.

# 2.12.0

Added free anonymous Mwmbl web search with optional Brave, provider-specific coverage, caching/throttling/cooldowns and no automatic paid fallback. Removed noisy Wikipedia/news fallback from personal-name research. See docs/FREE_WEB_SEARCH.md.

# 2.11.0

Bundle Maigret and its site database; add one-click authenticated companion setup, automatic port/token selection, restart after child exit and lifecycle cleanup. Keep advanced manual-service configuration.

# 2.10.0

Added optional HIBP, passive HarvestView and scoped Maigret companion connections, case integration, attributed exports, cancellation and partial coverage. See docs/ADDITIONAL_COLLECTORS.md.

# 2.9.0 — Automatic investigations and profile connectors

- Add a bounded identifiers-to-report engine with queue/depth/follow-up limits, explicit clue extraction, relevance checks and parent citations.
- Generate deterministic executive summaries, relevance groups, profile-name differences, coverage gaps and unanswered questions in UI/HTML/Markdown/JSON reports.
- Add cancellation with preserved, exportable partial reports and legacy-case compatibility.
- Add Steam inputs and opt-in Valve profile/library/recent-game enrichment, game AppID filtering and attributed optional CBL provider records.
- Add an optional local Osintgram 2.x bridge for profile/about/captions/hashtags, bounded requests, no media loading, and separate backend credential handling.
- Show connection readiness before investigation and document the new opt-in collection boundaries.

# 2.8.0 — SpiderFoot JSON import

- Add local preview/confirm import of standard SpiderFoot JSON results.
- Preserve complete source records, original JSON/hash, modules, last-seen text and false-positive flags.
- Create typed entities and proposed discovery links; retain ambiguous/missing source values without asserting exact event ancestry.
- Keep repeat imports idempotent while preserving analyst edits, with optional case assignment and normal workspace backup support.
- Add parser, transaction, HTTP and packaged-executable regression checks.

# 2.7.0 — Investigation workspace

- Preserve structured evidence and attachments separately from editable assessments; retain notebook compatibility and assessment history.
- Add notebook editing, tags, case/entity filters, search and potential-duplicate review.
- Add evidence-backed relationships, explicit entity merge/split operations and event timelines.
- Compare completed report snapshots with source coverage and absence caveats.
- Import PDF/text/screenshots with local Windows OCR, original-file preservation and page/passage citations.
- Export encrypted or plain complete workspace bundles with validated, transactional restore.
- Snapshot case-linked analyst assertions in reports and include them in exports.

# Changelog

Changes documented from the releases created for this repository.

## 2.6.0 — 2026-11-03

- Added Instagram, TikTok and VSCO handles/profile links to Research and Cases & reports, with platform-scoped index retrieval and prepared searches.
- Added canonical supplied profile references in report snapshots and every export; preserved old cases/reports.
- Added a multi-resolution navy/gold Windows application icon, matching UI mark and stable taskbar identity.
- Expanded the frozen Windows smoke test for social profile APIs/exports and exact embedded icon verification.
- 98 automated tests plus frontend syntax, live public canaries and frozen Windows release gates.

## 2.5.1 — 2026-11-03

- Fixed full-name auto detection and misleading zero-result outcomes.
- Added optional Brave web-index retrieval and in-memory key configuration for names, usernames, emails and phones.
- Preserved phone web-index findings in case reports and exposed search outcomes in exports.
- Added public source diagnostics, malformed-response checks, API limits, redirect/key safety tests and live canaries before release.
- 83 automated tests; live Brave integration requires a user key and was not exercised.

## 2.5.0 — 2026-11-03

- Added offline international phone parsing, numbering-plan validation and allocation/type/carrier metadata, with explicit owner/location limitations.
- Added multi-input cases, selected notebook evidence, background report generation and immutable report snapshots.
- Added Wikipedia/GDELT name-index coverage, source/error/not-run accounting, citations and exact-record deduplication without identity assertions.
- Added self-contained printable HTML, Markdown and JSON report exports.
- Updated the canonical repository reference to `allen1versonfr/vidocq` after the repository rename.
- Added case persistence, consent, interrupted-run, export escaping and HTTP tests; 72 tests pass locally. The release workflow also exercises the actual frozen phone/case/report/export endpoints before publication.

## 2.4.0 — 2026-11-03

- Added the full 1,171-entry framework source catalog with free-tier, category, text and integration filters.
- Made all 1,040 upstream free-access entries discoverable, with index-only searches for unintegrated tools.
- Added Open Library results and additional reviewed search-index links.
- Added per-entry coverage decisions, source provenance and MIT attribution.
- Bundled the directory for offline browsing; no original-source visits or tool execution are performed by catalog actions.
- Expanded validation to 53 tests; Windows frozen executable and updater checks gate publication.

## 2.3.0 — 2026-11-03

### Added

- Updates tab with startup checks for newer stable GitHub releases.
- In-app download progress, expected-size and SHA-256 verification, and install/restart controls.
- Private-repository access using an in-memory token or optional `VIDOCQ_GITHUB_TOKEN` environment variable.
- Separate updater helper, retained previous executable, and failed-start recovery.
- Reproducible Windows source build, frozen-executable tests, and gated release publication.
- Release checksum and build-information assets.

### Changed

- Switched the self-extracting bootstrap to a single PyInstaller portable executable for replaceable installs.
- Closed notebook and migration database connections deterministically to avoid Windows file locks.

### Validation

45 automated tests, frontend syntax validation, and actual Windows executable startup/replacement/restart/failed-launch rollback checks passed before publication. The native window was not manually exercised by those checks.

## 2.2.1 — Bootstrap release

Published as `vidocq-windows`. Established the Vidocq name and portable Windows package with research, image-search, notebook, and legacy-data migration features. This executable predates the in-app updater and requires one manual replacement to reach 2.3.0.

For full download history, see [Releases](https://github.com/allen1versonfr/vidocq/releases).
