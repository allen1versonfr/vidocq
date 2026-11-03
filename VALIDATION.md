# Validation for Vidocq 2.5.1

83 automated tests pass locally. The additions verify full-name auto detection, unconfigured search making no requests, index snippet parsing without original page fetches, malformed responses versus true empty responses, API authentication/rate/outage failures, key redaction, redirect blocking, session limits, offline versus online search outcomes and preservation of phone index results in reports/exports. Existing case, image, catalog and updater tests remain.

Live local public canaries returned 8 Wikipedia records for Ada Lovelace and 1 RDAP record for 8.8.8.8. GDELT returned HTTP 503 in a separate live probe; failures remain visible. CI requires at least one nonempty live Wikipedia/RDAP canary before building. This does not prove every source is available. Brave API tests are mocked; live retrieval requires a user's own key and was not exercised.

The Windows pipeline additionally requires frozen imports/UI/catalog/phone metadata, offline phone/case/report/export HTTP checks, replacement/restart and failed-start rollback. BUILD_INFO.json records those gates. The native interactive window is not manually exercised; identity relevance and ownership are not established by these tests.
