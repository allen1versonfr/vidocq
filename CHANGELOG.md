# Changelog

Changes documented from the releases created for this repository.

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
