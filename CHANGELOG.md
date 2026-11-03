# Changelog

Changes documented from the releases created for this repository.

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

For full download history, see [Releases](https://github.com/allen1versonfr/test/releases).
