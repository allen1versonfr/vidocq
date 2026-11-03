## Vidocq 2.3.0 — GitHub updates

- Added an Updates tab and automatic checks for newer stable GitHub releases at launch.
- Download updates inside Vidocq with progress, then choose Install and restart.
- Verifies the exact download size and GitHub SHA-256 digest before replacing the executable.
- Uses a separate updater process; keeps the previous executable and restores it if the new app fails to start.
- Preserves notebooks and existing legacy-data migration.
- Supports private-repository updates using an optional Contents: read GitHub token kept only in memory, or VIDOCQ_GITHUB_TOKEN on your computer. No token is bundled in the app.
- Replaced the temporary self-extracting launcher with a single portable Windows executable that can replace itself reliably.
- Added a repeatable Windows build and release pipeline with frozen-app, replacement/restart, and rollback tests.

### First upgrade
The old 2.2.1 executable predates the updater: download this Vidocq.exe once and replace the old one. Future stable releases can be installed from Updates. This repository is private, so authenticated read access is required for update checks and downloads.

### Requirements
Windows 10/11 x64; Microsoft Edge WebView2 Runtime for the native window. Browser fallback is supported. Keep the portable executable in a writable folder. Unsigned executable; no administrator permission is requested by the updater.
