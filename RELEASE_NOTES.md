# Vidocq 2.18.0

Repairs account/URL identity matching, supported-clue scheduling, canonicalization and report failure handling. A shared platform registry recognizes public profile shapes and aliases; supplied profiles, rediscoveries and new candidates are counted separately. Retrieval ranks, cache use and source observations survive into reports.

The local model selects finite excerpt and link IDs instead of reconstructing evidence. Empty selections are valid; unsupported items are isolated; comparisons distinguish source independence. Mode-level timing, usage and rejection details remain visible. Runtime setup includes a separate synthetic task check.

Adds opt-in encrypted Brave persistence, provider-preserving startup, provider-specific cooldowns, duplicate-request sharing, per-run API caps, cooperative deadlines, bounded HTTP workers, frozen active-run configuration and nested import validation. Checker controls must match the current database/runtime fingerprint. Lightweight progress and history metadata reduce repeated full-report loads.

Build dependencies are hash-locked and scanned in an isolated tool environment. Pillow 13.0.0, pypdf 6.21.4 and cryptography 50.0.2 replace versions flagged by that scan. The release adds a main-Python CycloneDX inventory; native and collector dependencies have separate manifests and are outside that inventory's scope.

See docs/AUDIT_FIXES.md for all audit items and remaining validation limits. Software tests and synthetic local-model checks do not establish a discovery-score improvement. Private benchmarks were not rerun or published. Native visual verification and live operator Instagram login are not claimed.

Previous release:

# Vidocq 2.17.2

Repeated Brave queries now use a copy-safe 15-minute session cache, including when the network request cap is reached. Quota errors pause further requests for a minute. Requests use the fixed Brave endpoint without system proxies or redirects. Each completed response records provider/retained counts, original rank and reasons for filtering; report exports show those counts. Offline diagnostics distinguish an empty provider response from rows discarded by the adapter. Approved adaptive searches try separate supplied first/last name tokens before adding more constraints, within the original search budget.

Validation: 278 Python tests pass locally (one Windows symlink skip), including synthetic cache/cap/quota, rank/filter/redaction and query-order regressions. No paid provider or private benchmark queries were made for this patch. Windows packaging validation runs in CI; no discovery-score improvement claimed.

Previous release:

# Vidocq 2.17.1

This patch addresses noisy discovery results rather than adding providers. Generic social discovery pages remain visible as context but no longer inflate candidate counts, seed follow-ups, or enter AI claim/comparison context. Observed profiles and identifier matches get priority before the AI context limit. Reports distinguish candidate records from distinct candidate profile URLs. Empty and discovery-only searches can trigger approved bounded query variations. AI explanations use neutral labels beside validated quotations to avoid publishing model-inferred associations as source facts.

An offline diagnostic can inspect sealed controls without spending API credit: `python scripts/diagnose_retrieval.py --answer-sheet LOCAL_KEY.json --controls LOCAL_CONTROLS --output LOCAL_DIAGNOSIS.json`. All paths are operator-selected; keep private inputs and outputs outside version control. A missing target is not labeled absent from the index.

Local validation: 273 Python tests pass (one Windows symlink skip), including synthetic discovery-page, AI-context ranking, unsupported-association and retrieval-stage regressions. Offline replay of existing private reports is local only. No new live personal queries were made for this patch. No discovery-score improvement is claimed; the patch improves evidence handling and exposes retrieval failures. Windows release validation runs separately in CI.

Previous release:

# Vidocq 2.17.0 - Guided operator login and broader research

- Included instagrapi 3.2.2 operator login, 2FA, encrypted saved sessions, cancel/forget and explicit reconnect. No OAuth claim or silent reauthentication during target lookups.
- Optional Serper/SerpApi Google-result adapters with encrypted remembered keys, session request caps, bounded responses/cache and explicit quota/error handling. No automatic paid fallback.
- Reviewed public bios, explicit links and platform-scoped stable IDs; separately approved one-page metadata capture and cited profile graphs without automatic ownership confirmation.
- Opted-in empty-result query variations inside case budgets, using only supplied clues/approved spellings.
- Guided browser review and continuation into a new immutable report with a fresh approved budget.
- Local AI source-quoted comparisons and finite next-evidence proposals; boilerplate ownership cautions do not count as substantive synthesis.
- Dated positive AND negative checker controls to clear quarantine, with recent outcome history and response/checker fingerprints.

[Setup and limits](docs/GUIDED_INSTAGRAM_LOGIN.md). Supply your own operator credentials/2FA or provider key inside Vidocq. Login/security notices can reach the operator account. No live Instagram login or paid-provider accuracy guarantee is implied by synthetic tests. Private-person benchmark data is excluded.

## Previous release

# Vidocq 2.16.0 - Managed tools and evidence-driven AI

- Included pinned theHarvester, Photon and Osintgram companions, alongside Maigret. One setup panel enables free Mwmbl and remembers local-service startup choices; setup runs no target queries.
- Osintgram startup credential prompt, encrypted Windows-user-bound HikerAPI key storage, change/forget controls and update preservation. No automated Instagram password login; paid provider access still requires your working key.
- AI-assisted case planning now adds and attempts validated searches, proposes explicit cited profile links and writes source-quoted review drafts, all within case permissions/budgets. No unrestricted model tools or cloud fallback.
- Reviewed browser evidence can flow through a native Windows relay from a generated case-specific bookmark or optional Chrome/Firefox extension. Browser permission remains required; pending captures enter cases only after review.
- Follow explicit public links to different handles, preserving parent citations without promoting ownership. Linked Maigret checks stay on the approved linked platform.
- Dated public checker controls with persistent mismatch quarantine, plus explicit incomplete-coverage reporting. Expanded exact-file cleanup for companion artifacts, settings and encrypted credentials.
- Separate collector source/build archive and license notices included in release assets.

[Setup, credentials, permissions and limits](docs/AUTOMATED_SETUP.md). Mwmbl remains a small index. Live paid Osintgram provider calls require your key; service startup alone does not validate quota or provider access. No private-person benchmark data is included.

## Previous release

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
