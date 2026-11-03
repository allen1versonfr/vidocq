# Framework source coverage

[← Project overview](../README.md)

## Snapshot

Vidocq bundles 1,171 source entries from OSINT Framework’s `public/arf.json`, revision `08720d5b594cb7513d7ec81f8e70c400375a85fc`, retrieved 2026-11-03. The normalized catalog preserves duplicate listings in their original categories. Its provenance records the upstream file SHA-256. The framework’s MIT license is included in this repository and executable.

| Upstream pricing | Entries | Default visibility |
| --- | ---: | --- |
| Free | 784 | Included |
| Freemium | 249 | Included; free-tier limits may apply |
| Free/freemium | 7 | Included; mixed label retained |
| Paid | 30 | Excluded by the default filter |
| Unknown | 101 | Separate filter; no free-access claim |

These are directory labels, not individual live verification of pricing, availability, APIs, terms, or notification behavior. Upstream’s passive/active labels are also not treated as proof that a tool will not contact or notify a target.

## What “using a source” means here

- **Integrated:** reviewed adapters fetch existing records and render their metadata inside Vidocq. Framework entries for crt.sh, Wayback, and Open Library map to such adapters. The existing Wikipedia, registry and SauceNAO features remain available too.
- **Prepared search:** reviewed external index-query links are available for selected search providers. Results are viewed in your default browser.
- **Index only:** a source’s public domain can be searched through Google using `site:domain` and your research term. This searches indexed pages and does not run the provider’s tool, query its API, visit its original URL, or imply that its database contents are indexed.
- **Unverified / excluded:** pricing is unknown or upstream marks the source paid. These entries are retained for coverage transparency rather than enabled as free services.

All 1,040 entries labeled as offering free access are represented in the catalog. They are **not 1,040 automated integrations**. Registration, local installations, quotas, service outages, template URLs, and provider-specific behavior remain real limitations. Potentially active tools are never executed from the catalog.

## Updating the directory

Check out the official upstream repository, review its new source metadata, and normalize the selected JSON snapshot:

```powershell
python scripts/sync_framework.py path/to/arf.json --revision UPSTREAM_COMMIT --output source-catalog.json
```

Review the generated counts, reasons, metadata and license; refresh the coverage report/docs and run the catalog tests before publishing. Synchronization reads JSON only and never installs or executes directory entries. The desktop app uses the bundled snapshot; it does not crawl all providers or automatically download unreviewed framework changes.

## Optional connectors in 2.9.0

Automatic investigations add separately configured Steam/CBL API adapters and a local Osintgram 2.x bridge. These are explicit, per-case opt-in integrations, not execution of arbitrary catalog entries. Destinations, transmitted data, credentials, limits, failures and platform-contact behavior are documented in [Automatic investigations](AUTOMATIC_INVESTIGATIONS.md).

## Free web search in 2.12.0

Mwmbl anonymous v2 search is an integrated free web index requiring no account or key. It has a smaller index and provider quotas. Brave remains optional. Case reports include buttons for manually opening prepared searches in the default browser. See [free search and browser review](FREE_WEB_SEARCH.md). These are separate from the bundled framework directory.
