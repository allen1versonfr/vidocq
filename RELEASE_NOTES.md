# Vidocq 2.15.0 - One-click local AI setup

- First-run/Updates entry points for optional managed Qwen3-4B-Instruct-2507 Q4_K_M and llama.cpp setup (about 2.54 GB, roughly 3 GB free disk space). No terminal/server configuration needed.
- Pinned hashes/revisions, progress, cancel/resume, repair and a synthetic startup check; Vulkan GPU mode with CPU fallback.
- Installed model/settings persist through app update, restart and rollback. The server loads on an approved draft and stops with the app. No silent replacement downloads or cloud fallback.
- Authenticated loopback-only inference, offline runtime, per-draft approval, Windows process lifecycle protection and exact managed-file Burn previews.

[Setup and licenses](docs/LOCAL_AI_SETUP.md). Existing GPU drivers/Windows runtime support are required; no driver installer is included. Vidocq remains portable: setup is offered inside the first launch and Updates screen.

## Previous release

# Vidocq 2.14.0 - Discovery workbench

- Chrome/Firefox active-tab helper exports reviewed selections and links to local JSON; import without repeated copy/paste.
- Photon aggregate JSON imports and a separately approved native bounded public-link crawler, with distinct provenance and coverage gaps.
- Full-name/first-last/alias/exact-URL query variants; dated historical alias records including supplied stable IDs and successor URLs.
- Cited page-to-page link observations in reports, kept separate from analyst ownership decisions.
- Unreliable bundled Instagram checker marked unavailable, plus an opt-in public GitHub checker canary.
- Optional local llama.cpp-compatible query suggestions and validated cited excerpt drafts. No model download, automatic execution or cloud fallback.

Setup and limits: [Discovery workbench](docs/DISCOVERY_WORKBENCH.md). The browser helper is user-installed (Firefox temporary add-on), Photon is import-only, and real local-model quality is hardware/model dependent. No private test-person data is included.

## Previous: 2.13.0

- Parse supported public profile links as handles, avoid shared-platform domain pivots and search location alternatives separately.
- Preserve each Maigret site's outcome and distinguish raw records, relevant candidates and analyst-confirmed accounts.
- Remember per-case account decisions/history, exclude known-rejected site/handle combinations and preserve immutable prior reports.
- Capture reviewed browser excerpts with their source/query as user-supplied case evidence.
- Add Burn Vidocq with exact-path preview and typed confirmation. It deletes named workspace/log files and optionally the current Windows executable/adjacent update backup after exit. Unrelated files are preserved. It does not promise forensic erasure or removal of external exports, backups or browser/OS records.

The local LLM assessment recommends an optional citation-validated drafting layer after deterministic fixes. No model is bundled or downloaded.

Guides: docs/REVIEW_AND_BURN.md and docs/LOCAL_LLM_ASSESSMENT.md. Deletion tests use disposable fixtures only; no personal investigation data is included in this release.
