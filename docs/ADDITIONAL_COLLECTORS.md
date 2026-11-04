# Additional investigation sources

**Version 2.16:** the Windows release includes managed theHarvester, Photon and Osintgram services, saved setup choices, a native reviewed-browser relay and an active bounded AI case pipeline. Start with [Automatic setup](AUTOMATED_SETUP.md); manual-service instructions below remain optional alternatives.

Configure these optional connections in Search connection, then allow each source in the case. Existing cases keep them off. Manually entered HIBP/collector keys stay in memory and are excluded from reports and backups. Managed local tokens are regenerated on startup. The Osintgram provider key is separately encrypted and retained as described in the setup guide. Standalone lookups are also available.

## Have I Been Pwned

Obtain your own email-search subscription key from https://haveibeenpwned.com/API/Key and enable HIBP. Case runs submit only email addresses you explicitly supplied, not discovered addresses. The complete email goes to HIBP. The adapter retrieves public breach metadata with attribution in the app and exported reports. It excludes sensitive/retired records and does not request passwords, raw dumps, pastes or stealer logs. Data: [Have I Been Pwned](https://haveibeenpwned.com/), CC BY 4.0.

Results are cached for 15 minutes, requests are spaced at least six seconds apart and HTTP 429 cooldowns are respected. Your subscription may impose stricter limits. Failed or restricted requests appear as gaps; an empty public result does not establish safety. Maximum 100 requests per app session.

## theHarvester / HarvestView

The Windows release includes pinned [theHarvester](https://github.com/laramies/theHarvester) and starts it from Automatic setup. No separate Python/service installation is needed. For an optional external service, install it following upstream instructions, start its API with authentication enabled (`THEHARVESTER_API_KEY`) on loopback, and enter its port (default 5000) and matching key. The adapter uses `/api/v1/sources` and `/api/v1/runs`. Older CLI-only releases are incompatible.

Choose up to four sources. Only ready sources advertised as passive P0 are accepted. Defaults: crtsh and certspotter. Other choices: duckduckgo, otx, urlscan, github-code and rapiddns. Availability, keys and quotas depend on your installation. Runs request a limit of 50, one source worker, a 60-second deadline and no DNS, active scanning, screenshots, takeover or vhost actions. Case targets must be supplied domains or their subdomains. Findings are domain-relationship leads, not proof of person/account ownership. Partial results and source failures remain visible. Cancellation requests a backend stop and retrieves retained evidence. Maximum 20 runs per app session.

## Maigret

Maigret 0.6.6 and its local site database are included in the Windows executable. Open **Search connection → Maigret → Set up and enable Maigret**. Vidocq starts its bundled companion in the background, chooses an unused loopback port and creates an in-memory authentication token. No Python installation, terminal command, companion download, key entry or setup-time account query is required. Setup works offline; actual username checks need internet access.

Enable Maigret in each case and choose platforms before running the report. The service stops when disabled or when Vidocq closes, including forced parent-process exit. Automatic setup preferences persist across launches; the older standalone setup button remains session-only. If the child exits unexpectedly, the next enabled lookup attempts a restart. Failed startup is an error, not a no-match result.

The advanced settings still support a separately configured companion. Source checkout users install `requirements.txt` in their environment; the Windows download already contains the dependency. The legacy companion ZIP remains available for advanced installations. Maigret attribution and its MIT license are included in `docs/MAIGRET_LICENSE.txt` and the bundled executable.

Choose up to ten supported platforms; defaults are GitHub, Reddit and Steam. Supplied handles run within the report budget. Explicit published links can permit a different handle to be checked on its specifically linked, case-approved platform; arbitrary recursive checking stays disabled. Checks contact public platforms and can be logged or blocked. The companion uses the local database, at most three concurrent checks and a 60-second deadline. It disables recursion, profile extraction, enrichment, cookies, proxies, activation and challenge bypass. Maigret is bundled under its upstream license.

Claimed accounts remain unverified candidates. Matching handles do not establish common identity. Blocked, unavailable or missing checks remain gaps. Platform changes can cause failures and false positives. Maximum 20 runs per app session.

## Review

Additional findings require review even when supplied identifiers co-occur. Only eligible explicit identifiers/profile links can expand an opted-in investigation within its budgets; results do not prove ownership. Inspect sources before making identity conclusions. Reports remain local; providers receive the identifiers their queries require. The setup panel launches included Maigret and theHarvester companions. Functional tests do not measure investigation accuracy.
