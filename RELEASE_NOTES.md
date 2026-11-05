# Vidocq 2.21.0

Platform search planning now pairs supplied handle and name queries on each platform, prioritizing Instagram and TikTok before VSCO and LinkedIn. A four-query platform limit therefore covers both term types on the first two platforms instead of one term type across four. Reports list the remaining unsearched platform queries. Existing budgets are preserved.

With clue following and indexed-link following enabled, a relevant retrieved profile can supply a different observed handle for a bounded index-search hypothesis. Searches retain the parent citation, respect existing follow-up/depth/request limits, and never add the handle to confirmed case identifiers. Rejected profiles, generated link-only leads and opaque IDs cannot start this path. Hypothesis results remain subject to the original relevance rules and do not recursively expand.

Validation: 363 Python tests pass locally with one platform-capability skip. Synthetic engine tests cover execution, deduplication, provenance, opt-out, zero budgets, rejected profiles and no automatic ownership promotion. Live discovery-score improvement remains unmeasured. Windows packaging, update and rollback checks must pass before publication. Private subject data is excluded.

See docs/DISCOVERY_FOLLOWUPS.md for behavior and limits.

Previous release:

# Vidocq 2.20.1

Supplied public profile URLs now contribute reusable usernames to cross-platform search planning. Opaque account IDs, navigation URLs and content URLs are excluded, and repeated handles are deduplicated.

Reports recognize first-and-last-name matches when a supplied name includes a middle name, and accept analyst-approved spelling variants. Multiple spellings count as one name signal; name-only matches remain unverified and cannot alone enable clue expansion.

When adaptive searches are enabled, unrelated index results now trigger the existing bounded query variations. Previously, nonempty unrelated results could prevent a useful fallback. Existing search, request and adaptive-query limits still apply.

Validation: 359 Python tests pass locally with one platform-capability skip. A synthetic end-to-end case recovers a candidate missed by the previous implementation under identical clues and a four-search cap. This does not establish a live benchmark score improvement. No private test data is included. Windows packaging, update and rollback gates run before publication.

Previous release:

# Vidocq 2.20.0

New interface-created cases select 20 Brave results, with an option to use the connection setting or 10. Existing cases retain their settings. Optional extra Brave excerpts preserve more indexed context without fetching original pages; per-case depth/snippet choices have separate caches and do not change saved connections. Search/request/deadline limits still apply.

Cited profile URLs survive as unverified review leads even when approved followups return nothing or have no remaining followup budget. Optional index-snippet link following is limited to explicit account URLs from supplied/reviewed profiles. Excerpt windows retain verbatim evidence near late identifiers. Public metadata capture prioritizes bio URLs and sameAs links from a Person node matching the approved source URL, while keeping page anchors separate.

A simple historical-alias form supplies dated evidence and successor references to the bounded plan; no aliases or continuity are inferred. Review plans preserve platform scopes. Read-only GUI/CLI miss diagnosis separates original adapter loss, unmaterialized links, rejections, absent returned references and separately saved post-test controls. It makes no provider calls and never changes discovery credit. Explicit account URLs already in starting notes/alias assertions cannot earn withheld credit, and linked review leads remain distinct from index-returned matches.

Validation: 351-test suite passes locally (one Windows symlink-capability skip), including cache/context isolation, link provenance/limits, structured bio matching, exact windows, sealed input preservation, read-only API behavior and blind-key contamination checks. DOM case/alias fixtures pass. Real local Qwen synthetic planning, abstention, cited extraction near a late identifier and finite next-action outputs returned valid results. Packaged Windows gates verify the new options/diagnostic and repeat update, rollback and cleanup checks.

Private test data stays excluded. No fresh paid/private-person test ran for this release and no discovery-score improvement is claimed. Native visual QA and live operator Instagram login remain unvalidated. See docs/EVIDENCE_RECOVERY.md for controls and limits.

Previous release:

# Vidocq 2.19.0

Thirteen changes target discovery coverage and evidence quality. Directory/property listings no longer enter model evidence or automatic clue expansion; raw records remain reviewable. Model context must match supplied identifiers, complete names, account references or analyst-confirmed evidence. Name-only quotation drafts warn about namesakes, and syndicated identical excerpts cannot fill multiple context slots.

The engine skips equivalent context/AI queries and records the reason. Adaptive runs can spend remaining approved budget on platform-specific indexed searches, balancing supplied handles and name tokens. The platform-query limit is configurable from zero to eight, default four; total search/request/deadline limits still apply. Indexed TikTok/X content author paths become separate unverified profile leads with parent citations, preserving the original content URL. LinkedIn and Hudl profiles use exact-reference followups rather than fabricated usernames.

Search connection adds optional 20-result Brave retrieval, preserving ranks beyond ten, depth-specific caches and saved settings. Ten remains the default. No pagination, credit purchase or authenticated social login is added. AI phases and report exports expose filtering, duplicates and query-efficiency details. Terminal report status now waits for final ledger persistence and settings-lock release, correcting a completion race caught by the packaged gate.

Validation: 329 Python tests pass locally (one Windows symlink-capability skip), with synthetic source/relevance, platform-budget, provenance, namesake-label, query/cache and deep-rank regressions. DOM settings fixtures pass. Real local Qwen synthetic planning, abstention, quoted extraction and finite next actions returned valid outputs. Windows release gates repeat the suite and packaged update/recovery checks, including saved result-depth restoration.

No new paid or private-person searches were run for this update. Discovery-score improvements remain unmeasured. Private fixtures/results are excluded from GitHub. Native visual QA and live operator Instagram login are not claimed.

Previous release:

# Vidocq 2.18.1

Fixes repeated Brave key entry after restart or update. Saving a search connection now retains its provider and API key using Windows DPAPI by default. The Save checkbox starts checked; uncheck it for a session-only connection. Clear saved connection removes the stored key. Keys remain outside the executable in the current Windows user's Vidocq data directory.

Saving without retyping a key now keeps the active key, including a recently changed session key, rather than reverting to an older stored key. The UI no longer incorrectly says Brave keys stay only in memory. Older versions that never saved a key cannot recover it after exit; enter it once in this version to retain it going forward.

Validation: 310 Python tests pass locally (one Windows symlink-capability skip), including real Windows DPAPI restart, explicit session-only and key-rotation regressions. DOM fixtures verify persistence is checked by default. Windows release checks also verify a fresh updated executable restores the encrypted Brave key and disabled preference without provider requests.

Previous release:

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
