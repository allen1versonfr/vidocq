# Additional investigation sources

Configure these optional connections in Search connection, then allow each source in the case. Existing cases keep them off. Keys stay in memory and are excluded from reports and backups. Restarting Vidocq forgets them. Standalone lookups are also available.

## Have I Been Pwned

Obtain your own email-search subscription key from https://haveibeenpwned.com/API/Key and enable HIBP. Case runs submit only email addresses you explicitly supplied, not discovered addresses. The complete email goes to HIBP. The adapter retrieves public breach metadata with attribution in the app and exported reports. It excludes sensitive/retired records and does not request passwords, raw dumps, pastes or stealer logs. Data: [Have I Been Pwned](https://haveibeenpwned.com/), CC BY 4.0.

Results are cached for 15 minutes, requests are spaced at least six seconds apart and HTTP 429 cooldowns are respected. Your subscription may impose stricter limits. Failed or restricted requests appear as gaps; an empty public result does not establish safety. Maximum 100 requests per app session.

## theHarvester / HarvestView

Install current [theHarvester](https://github.com/laramies/theHarvester) separately following its upstream instructions, including HarvestView and provider credentials. Start its API with authentication enabled (`THEHARVESTER_API_KEY`) and keep it bound to loopback. Enter its port (default 5000) and matching X-API-Key in Vidocq. This integration targets `/api/v1/sources` and `/api/v1/runs`. Older CLI-only releases are incompatible.

Choose up to four sources. Only ready sources advertised as passive P0 are accepted. Defaults: crtsh and certspotter. Other choices: duckduckgo, otx, urlscan, github-code and rapiddns. Availability, keys and quotas depend on your installation. Runs request a limit of 50, one source worker, a 60-second deadline and no DNS, active scanning, screenshots, takeover or vhost actions. Case targets must be supplied domains or their subdomains. Findings are domain-relationship leads, not proof of person/account ownership. Partial results and source failures remain visible. Cancellation requests a backend stop and retrieves retained evidence. Maximum 20 runs per app session.

## Maigret

Maigret 0.6.6 and its local site database are included in the Windows executable. Open **Search connection → Maigret → Set up and enable Maigret**. Vidocq starts its bundled companion in the background, chooses an unused loopback port and creates an in-memory authentication token. No Python installation, terminal command, companion download, key entry or setup-time account query is required. Setup works offline; actual username checks need internet access.

Enable Maigret in each case and choose platforms before running the report. The service stops when disabled or when Vidocq closes, including forced parent-process exit. Session enablement is forgotten when the app closes; use the setup button on the next launch. If the child process exits unexpectedly, the next enabled lookup attempts a restart. A failed startup is shown as an error, not a no-match result.

The advanced settings still support a separately configured companion. Source checkout users install `requirements.txt` in their environment; the Windows download already contains the dependency. The legacy companion ZIP remains available for advanced installations. Maigret attribution and its MIT license are included in `docs/MAIGRET_LICENSE.txt` and the bundled executable.

Choose up to ten supported platforms; defaults are GitHub, Reddit and Steam. Each distinct supplied handle runs once per report; discovered handles are not recursively checked. Checks contact public platforms directly and can be logged or blocked. The companion uses the installed local database, at most three concurrent checks and a 60-second run deadline. It disables recursion, profile extraction, enrichment, cookies, proxies, activation and challenge-bypass features. The Windows executable bundles Maigret under its upstream license.

Claimed accounts remain unverified candidates. Matching handles do not establish common identity. Blocked, unavailable or missing checks remain gaps. Platform changes can cause failures and false positives. Maximum 20 runs per app session.

## Review

Additional collector findings require review even when several supplied identifiers co-occur. They do not automatically expand investigations. Inspect the source before making ownership or identity conclusions. Reports remain local; configured providers receive the identifiers their queries require. The setup button launches the included Maigret companion; theHarvester remains a separate service. Functional tests use synthetic contracts and do not measure investigation accuracy.
