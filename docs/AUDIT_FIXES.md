# Audit fixes in Vidocq 2.18.0

This release repairs the demonstrated identity, scheduling, evidence and reliability defects. It adds evaluation tools without claiming that a passing software suite improves real-world discovery scores. Private benchmarks and answer keys are not part of the repository.

## Status against the audit

| Findings | Status | Result and limits |
|---|---|---|
| F01–F04 | Implemented | Complete profile identity comparisons, complete URL-token validation, reconsidered clue state and explicit seed anchors. |
| F05 | Implemented with a narrow scope | Unicode/name-formatting similarities enter a manual-review lane. They do not confirm ownership or automatically authorize expansion. |
| F06–F09 | Implemented | Shared profile registry and mobile aliases; content URLs remain distinct; VSCO account aliases match decisions; invalid rows cannot abort account counting. |
| F10–F12 | Implemented | Resource IDs and diverse model context; per-query rank/cache observations; separate seed, rediscovery and new-candidate account counts. |
| F13 | Implemented | Supported pivots have queue priority and bounded followup capacity; budget-exhausted inputs remain visible. |
| F14–F18 | Implemented | Valid empty answers, item-level rejection, source-independence labels and finite excerpt/link selections. Legacy quoted-output validation remains supported for compatibility. |
| F19–F21 | Implemented with validation limits | Bounded mode-specific output, truncation detection, phase/token/rejection telemetry and a synthetic task check. Runtime readiness and task checking are separate; neither proves investigative accuracy. |
| F22–F25 | Implemented | Configuration mutations are serialized against active cases; sanitized run manifests, cooperative deadlines, bounded I/O, partial reports and separate processing/source outcomes. |
| F26–F31 | Implemented | Single-flight search requests, provider-specific cooldowns, opt-in DPAPI Brave storage, provider-preserving setup, visible next-start preference and filtering diagnostics across adapters. |
| F32 | Implemented with scope labels | Per-run external parent-API request caps and a ledger, separate from session caps. Loopback polling is excluded; collector backends retain separate bounded operations. Counts are not a billing receipt. |
| F33–F35 | Implemented | Current database/runtime fingerprint pairing, serialized checker history writes and nested bundle-schema validation before transactional restore. Legacy context-only folders remain restorable but need clues before running. |
| F36 | Implemented | Lightweight progress polling, paginated report metadata and transient pre-task progress avoid full report transfers and duplicate pre-task snapshot writes. Completed evidence still persists after each task. |
| F37 | Implemented for new reports | Process creation identity prevents PID reuse from owning a new-version report. Older reports have no creation identity; legacy live-PID ambiguity cannot be reconstructed automatically. |
| F38–F39 | Implemented | Bounded loopback request workers/read timeouts and allowlisted child environments. Same-bundle Maigret retains only required PyInstaller runtime variables. |
| F40 | Implemented in part | Main dependency hash lock, isolated security-scan gate and a main-Python CycloneDX inventory. Updated Pillow, pypdf and cryptography after advisories were reported. A complete native/collector SBOM and independently signed releases are not claimed. |
| F41–F43 | Implemented infrastructure | Audit regressions and synthetic integration gates; offline key preflight, explicit eligibility/exclusions, seed/negative/unresolved scoring and comparison of sealed conditions. The private held-out dataset still needs independently dated ownership/visibility labels. |
| F44–F47 | Experiment support added; measurements pending | Offline condition comparison supports fixed-clue comparisons of query strategies, rank depth, reviewed bios and model modes. No new paid or private-person experiment was run. Defaults were not changed on an unmeasured score claim. |
| F48 | API and DOM checks implemented; native visual validation pending | Packaged API, model/session/provider, update/recovery and DOM fixtures cover the workflow. Native visual/browser interaction has not been validated; previously denied browser UI access was not retried. |

## Operator changes

In Search connection, choose Brave and check the save option to retain the key using Windows DPAPI. A session-only key still disappears at restart. The next-start provider is shown explicitly. Research settings cannot be changed while a report is active.

Assisted cases expose a total time limit and an external request cap per provider. Ongoing work is bounded and partial evidence survives interruption; collector backends have separate operation caps. These controls do not change provider billing settings.

Reports distinguish supplied profiles, rediscoveries and new candidates. Weak name-formatting matches require manual review. Model-selected quotations and actions remain review drafts; valid abstentions earn no discovery credit.

## Local benchmark tools

Keep keys and results in an ignored/private directory. Validate a key before a paid run:

```powershell
python scripts/evaluate_benchmark.py --key LOCAL_KEY.json --output LOCAL_VALIDATION.json
```

Score sealed reports as separate conditions without contacting a provider:

```powershell
python scripts/evaluate_benchmark.py --key LOCAL_KEY.json --report REPORT_A.json --report REPORT_B.json --output LOCAL_COMPARISON.json
```

Keys contain an accounts list. Each entry needs a unique id, role, platform and canonical_url, or an explicit exclude_reason. Roles are seed, withheld, previously-confirmed, supplied-handle-control and negative. Public-account recall requires ownership confirmed, public_visibility public and public_verified_on within 30 days. Supply explicit reference_variants for known URL aliases. Unknown ownership stays unresolved; no total grade is invented.

Changing clues or adding reviewed evidence creates a different condition. The comparison flags changed starting clues. Keep current/historical accounts separate and reserve held-out subjects for final evaluation.

## Build and validation scope

The main Windows build uses requirements-lock.txt with hashes. The scanner is isolated from the build environment. Main-Python-SBOM.json inventories that environment, not every native library or separate collector. Collector source ZIPs and locks remain separate.

New runtime and source controls were verified with synthetic fixtures. A real local Qwen check selected a quoted source excerpt and finite next actions; it also abstained from some tasks. This verifies the response contract, not account discovery or semantic accuracy. Real operator Instagram authentication still requires an operator account and has not been live-tested here.
