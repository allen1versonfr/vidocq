# Development and releases

[← Project overview](../README.md) · [Contributing](../CONTRIBUTING.md)

## Run from source

The release pipeline uses Python 3.12 on Windows. From an authenticated checkout:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py --browser
```

Use `python app.py` for the native window when the necessary GUI runtime is available. The distributed and tested desktop target is Windows 10/11 x64; running source on another OS is not a released macOS or Linux port.

## Source map

| Path | Responsibility |
| --- | --- |
| `app.py` | Local HTTP API, reviewed text adapters, notebook persistence, data migration, and window lifecycle. |
| `image_search.py` | SauceNAO requests, image preparation, and response normalization. |
| `updater.py` | GitHub release selection, downloads, verification, helper replacement, and rollback. |
| `version.py` | Current version and update repository. |
| `launch.py` | Packaged application entry point, startup logging, and updater-helper entry point. |
| `ui/` | HTML/CSS/JavaScript interface. |
| `tests/` | Research-policy, server, image, migration, and updater tests. |
| `scripts/windows_smoke.py` | Tests the actual frozen Windows executable and replacement/recovery. |
| `scripts/publish_release.py` | Creates or resumes a draft, uploads assets, verifies GitHub’s asset digest, and publishes. |
| `.github/workflows/windows.yml` | Current Windows build/test/release pipeline. |
| `.release-payload/` and `publish-vidocq.yml` | Historical bootstrap publication; not the current source-build path. |

## Validate and build

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --check ui/app.js
.\build_windows.bat
```

The build script installs the pinned runtime dependencies and PyInstaller, runs the Python suite, builds `dist\Vidocq.exe`, and runs Windows smoke checks. Node.js is needed for the separate frontend syntax command and is present in the GitHub runner.

The 2.3.0 release passed 45 automated tests. Frozen Windows checks validate bundled imports/UI assets/database access, executable replacement and restart, and recovery after an invalid replacement cannot launch. They do not manually exercise the interactive native window. See [VALIDATION.md](../VALIDATION.md).

Use `VIDOCQ_DATA` pointing to a disposable directory for development so tests and manual experiments do not use your everyday notebook.

## Publish a version

1. Update source, relevant tests, and release notes. Update `RELEASE_NOTES.md`, which supplies the release body, and `CHANGELOG.md`.
2. Set a newer stable version in `version.py`, such as `2.4.0`. Keep user-facing version strings and Windows smoke-test expectations consistent with the version change.
3. Push the completed change to `main`. A change to `version.py` or `.github/workflows/windows.yml` triggers the release workflow. The workflow can also be run manually from Actions on the intended branch.
4. Check the run: dependency installation → tests → frontend syntax → Windows build → frozen executable checks → artifact upload → release publication.
5. Confirm the release assets: `Vidocq.exe`, `SHA256SUMS.txt`, and `BUILD_INFO.json`. Future in-app updates require the exact executable name and a GitHub SHA-256 asset digest.

Source or documentation changes alone do not automatically publish a new version unless one of the workflow’s trigger paths changes. Do not dispatch concurrent publication attempts. The workflow uses a concurrency group, refuses to overwrite a published version, and can resume a draft after a publishing failure. Bump the version for a replacement to an already published release.

`BUILD_INFO.json` includes the test/build gates and executable hash. When changing the suite, keep its recorded test count accurate. Do not commit tokens, local findings, virtual environments, or generated executables into the source tree.
