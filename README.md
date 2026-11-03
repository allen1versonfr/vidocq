# Vidocq

Portable Windows research app with a local notebook, reviewed public-index adapters, reverse-image search through SauceNAO, and GitHub self-updates.

Download **Vidocq.exe** from [the latest release](https://github.com/allen1versonfr/test/releases/latest). Windows 10/11 x64. Native UI uses Microsoft Edge WebView2; the app can fall back to your default browser.

## Updating

Replace the original 2.2.1 executable with 2.3.0 once. Then open **Updates**:

1. Vidocq checks for newer stable releases when it starts.
2. For this private repository, enter a fine-grained GitHub token with **Contents: read** permission on `allen1versonfr/test`, then Check for updates. Tokens stay in memory and are never written to the notebook, logs, or update jobs. Optionally set `VIDOCQ_GITHUB_TOKEN` on your own machine for checks across launches. Public repositories need no token.
3. Choose Download update. Vidocq checks the file size and GitHub SHA-256 digest, then offers Install and restart.
4. Vidocq closes, replaces its executable, and restarts. If startup fails, it restores the previous executable. A `.previous` copy is retained beside the executable.

Use a writable folder. Notebook data remains in `%LOCALAPPDATA%\Vidocq\workspace.sqlite3`; legacy AllSeeingEyes and OSINTDesk notebooks are copied once when needed. Updating does not delete notebooks. SHA-256 validates downloaded bytes against GitHub metadata; it is not an independent code signature. Only publish trusted builds from this repository.

## Development and releases

Python 3.12. Install requirements, then run `python -m unittest discover -s tests -v`. Run `python app.py --browser` for development. `build_windows.bat` builds a single executable and runs Windows frozen-app and updater integration checks.

The Windows release workflow builds from source, runs tests, exercises the actual executable, verifies replacement/restart and failed-start rollback, uploads artifacts, then creates a versioned release with Vidocq.exe, SHA256SUMS.txt and BUILD_INFO.json. Publishing happens only after all checks pass. Future releases: update source/tests and release notes, bump `version.py` using a stable semantic version, and push to main (or run the workflow manually). Published versions cannot be overwritten by the pipeline. Draft releases may be retried.

The original bootstrap release is retained. Its encoded files under `.release-payload` are historical; new releases build directly from the source here.

## Research boundaries

Queries go only to reviewed third-party indexes; the app does not contact submitted profiles, domains, or IPs directly. Prepared search links open only after a click. SauceNAO requires your API key and explicit image-upload consent. Image metadata is stripped before upload. No remote thumbnails or original source pages load inside the app. Providers may log requests; passive research is not anonymous. Findings are stored locally in unencrypted SQLite. Images and SauceNAO keys are not persisted.

Inspired by OSINT Framework. `source-review.json` records the earlier directory review.
