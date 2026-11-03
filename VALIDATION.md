# Validation for Vidocq 2.13.0

The 205-test suite passes locally (one symlink-capability test skipped). All six frontend scripts pass syntax checks. The suite covers profile/shared-host parsing, alternative locations, rejected-account persistence/exclusions, analyst-confirmation history, immutable browser captures, diagnostic outcomes, relevance counts and guarded deletion. Burn tests use isolated folders and assert preservation of unrelated files and refusal of out-of-scope manifests. A Windows symlink test can skip when link creation is unavailable. Local Windows smoke checks passed browser/review APIs and exports, non-destructive burn preview, update/restart/rollback and disposable copied-executable removal. The burn fixture removed its named data/log files, executable and adjacent backup while preserving an unrelated sentinel and the actual build. No live user workspace/executable is deleted. Visual browser validation remains unavailable after the prior access denial. No local LLM inference or real-person discovery accuracy evaluation is claimed for this release.

Previous validation:

# Validation for Vidocq 2.12.0

182 automated tests cover existing features plus free-provider configuration, anonymous requests with no key forwarding, query/scoped filtering, cache isolation, rate/quota cooldowns, malformed/empty distinction, outages, optional Brave compatibility and removal of unrelated name-index fallback. The anonymous Mwmbl API returned live public Ada Lovelace results both from source and the actual Windows executable, with no API key/account. All five frontend scripts pass syntax checks. A direct DuckDuckGo HTML canary returned a challenge and was not adopted as an automatic provider. Visual browser checks were not repeated after the earlier access denial.

Previous validation:

# Validation for Vidocq 2.11.0

170 automated tests pass. New lifecycle checks exercise the real installed Maigret companion without account queries: authenticated setup, repeat setup, child restart, stop on disable, manual-service switching and startup-error cleanup. The Windows bundle includes Maigret and its database/license. Local frozen checks passed automatic setup, repeat setup, authentication and shutdown without querying accounts. Source lifecycle tests also cover re-enablement and forced parent exit. Visual browser validation was not repeated; it remains unavailable after the prior browser approval denial.

Previous validation:

# Validation for Vidocq 2.10.0

164 automated tests pass, including 17 new collector tests for opt-ins, destinations, response contracts, attribution, cooldowns, cancellation, partial coverage and companion authentication. Maigret 0.6.6 was separately installed to inspect its interface and database. New upstream results use synthetic contracts; live authenticated HarvestView and real-account Maigret investigations were not evaluated.

The official HIBP reserved integration-test account returned the expected public breach fixture using its test key. No personal email was queried. All five frontend scripts pass syntax checks. The local Windows executable passed prior smoke checks plus the new collector asset, defaults and missing-connection coverage. A visual browser check was blocked by the browser approval gate and was not completed.

Previous validation:

# Validation for Vidocq 2.9.0

147 automated tests pass locally, including 25 assisted-investigation/connector tests alongside all 122 prior tests. New coverage includes legacy notebook loading, immutable captured evidence, editable assessments/history, relationship/evidence validation, event date ranges, explicit merge/split assignments, text and PDF/screenshot extraction, unavailable-OCR preservation, attachment hashing/deduplication, encrypted round trips, restore preview/idempotence, conflict atomicity, invalid schema/hash/reference rejection, active-run backup rejection, and report comparison with multiple records per source.

`node --check ui/app.js` and `node --check ui/investigation.js` pass. Browser checks against a disposable workspace verified entity creation, notebook save/entity assignment, assessment editing without changing the captured excerpt, filtering and timeline creation with separate event/discovery dates. The native window was not manually exercised.

Actual local Windows OCR read a generated synthetic screenshot. The built Windows executable passed screenshot OCR, scanned-PDF rendering/OCR, structured evidence/attachment saving, encrypted workspace backup and restore preview, phone/social/case/report/export APIs, exact embedded icon verification, executable replacement/restart and failed-start rollback. OCR depends on installed Windows language support; the frozen smoke checks also accept and verify its explicit unavailable state on machines without that capability.

CI repeats the Python suite, both frontend syntax checks, live public source canaries, Windows build and frozen checks before publication. No user API keys or real investigation data are used. Release publication remains a separate workflow step; local validation does not establish that a GitHub release has been published.

SpiderFoot coverage validates the native 4.0/upstream flat JSON shape, preview without record creation, complete raw metadata/attachment preservation, proposed discovery links, ambiguity/missing-source handling, false positives, scan/type isolation, duplicate/reordered imports preserving assessments, case assignment, full workspace backup roundtrip, rejected malformed exports, late-collision rollback and authenticated HTTP routes. Browser checks verified preview counts, confirmed import and preserved source metadata in Notebook using a synthetic export. Frozen checks exercise preview/import/re-import and the bundled frontend asset. Real user scans and SpiderFoot HX exports were not tested.

Automatic investigation coverage checks strong/weak relevance, same-handle deduplication, explicit identifier extraction, supported second-level follow-ups, supplied-context queries, budgets, cancellation, source gaps, source-text escaping and profile-name review flags. Connector tests cover opt-in/default-off behavior, fixed destinations, redacted keys, private/malformed Steam libraries, vanity resolution, game filters, quota enforcement, bounded CBL claims, Osintgram command/target validation, media/address filtering, local-service identity checking, private-profile content gating, remaining-budget enforcement and cancellation. HTTP checks cover authentication, connector consent and completed-run cancellation behavior.

A browser run against a disposable workspace and synthetic Osintgram-compatible loopback server verified the one-click phone/Instagram-to-report workflow, cited co-occurrence grouping, discovered email follow-up and explicit missing-Brave coverage. Frozen Windows checks also exercise the assisted engine with that synthetic API contract and Steam-not-configured coverage. All four frontend scripts receive syntax checks. No live authenticated Steam, CBL, HikerAPI or Instagram requests were made; upstream API contracts are tested using synthetic responses. The actual Osintgram process/backend was not installed or authenticated during validation.
