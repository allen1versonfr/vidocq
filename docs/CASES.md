# Phone analysis, cases and reports

For the new identifier-to-report workflow, search budgets, cancellation, Steam and Osintgram setup, see [Automatic investigations (2.9.0)](AUTOMATIC_INVESTIGATIONS.md). The original index-only workflow below remains available when Automatic investigation is disabled. In automatic mode, notes/reference URLs and selected evidence can contribute explicit identifier clues, while original pages are not arbitrarily fetched.


[← Project overview](../README.md)

## Phone numbers

Open **Phone**, enter a number, and choose its two-letter region if you entered a national number rather than an international `+` number. The default region is US. Choose **Analyze locally**.

Vidocq uses bundled libphonenumber metadata to show E.164/international formatting, country calling code, numbering region, number type, numbering-plan validity, allocation region, original carrier allocation when available, and possible time zones. No call, text, account-existence test, live carrier check, owner lookup or location tracking is performed. A valid numbering-plan format does not establish whether a number is assigned, reachable or current. Carrier and allocation metadata can be stale after number portability or reassignment.

The Research tab also accepts **Phone number** explicitly and detects common numeric phone formats. Its national-number default is US; use the dedicated Phone tab or case region field for another country.

## Give Vidocq several details together

Open **Cases & reports** and create a case. You can supply:

- Up to three names or aliases.
- Up to five usernames, emails, phone numbers, domains, or public IPs per field.
- Up to five Instagram, TikTok and VSCO handles/profile URLs in each separate platform field.
- Up to fifteen searchable identifiers total, after normalization and deduplication.
- Up to ten reference URLs and 20,000 characters of notes as additional context.
- Up to thirty explicitly selected notebook findings as supplied evidence.

Enter one identifier per line. Save the case, confirm the listed public-index searches, then select **Save and generate report**. Generation runs in the background with input-by-input progress. Cases and report snapshots are stored in the existing local SQLite workspace. Editing a saved case does not rewrite earlier reports. A report interrupted by an app shutdown is marked interrupted when its owning process is no longer running; it is not silently rerun.

### What is searched automatically?

| Input | Automatic handling | Coverage limits |
| --- | --- | --- |
| Names | Wikipedia name index and GDELT’s recent news index | Shared names and unrelated people can match. GDELT searches the last three months, with up to ten records per name; Wikipedia returns up to eight. |
| Domain | Certificate Transparency and Internet Archive metadata | Existing records only; no live scan or archive submission. |
| Public IP | Reviewed registry metadata | Allocation information does not identify an individual. |
| Instagram / TikTok / VSCO | Platform-scoped Brave snippets if connected; prepared index queries otherwise | No profile visits, account-existence checks, media downloads or ownership verification. |
| Phone | Offline numbering-plan metadata and optional Brave index snippets | No owner identification or live verification. |
| Username / email | Brave index snippets when connected; prepared links otherwise | The report shows disconnected searches explicitly; no mailbox/account validation. |
| Notes / reference URLs | Preserved as supplied context | Not automatically searched, visited or scraped. |
| Selected notebook findings | Included with supplied-evidence labels | Not treated as independent verification or assumed to concern the same person. |

No original news articles, profiles, reference URLs or remote thumbnails are fetched. GDELT requests retrieve indexed article titles and source metadata only. Sources can log queries. Empty results, provider errors, and unsupported searches remain visible in the coverage section.

## Images and other evidence

For image evidence, use **Image search**, confirm the SauceNAO upload, save relevant results to Notebook, and select those findings in the case. The case form does not automatically upload files or identify people from faces. Preserve observations from other documents in the notes or notebook with their source references; local PDF/text/screenshot ingestion and Windows OCR are available under Investigation; see [the investigation guide](INVESTIGATION.md).

## Read the report

Each report separates retrieved index records, offline metadata, and supplied notebook evidence. Evidence entries include citation IDs such as `R001`, provider, source request, optional source reference, matching supplied inputs, retrieval time, and an **Unverified relevance** label. Exact duplicate records can be consolidated across inputs; this is not an identity match or independent corroboration.

The summary lists processed inputs, record counts, provider failures and prepared searches that were not run. No AI-generated biography, identity confidence percentage, private-address discovery or “complete background check” claim is made. The report represents everything returned by the documented searches in that run, not everything that exists about a person.

## Export

Select a completed snapshot and export:

- **Printable HTML:** self-contained, with no scripts, images, remote resources or automatically opened source links. Open it and use your browser’s Print → Save as PDF.
- **Markdown:** readable text with source and evidence sections.
- **JSON:** the complete structured snapshot for inspection or later processing.

Exports contain the supplied identifiers and selected evidence. Cases, notes and report snapshots are not encrypted by the app. Protect the database and exports accordingly. Individual report exports are not importable. Use Investigation → Backup for complete, restorable workspace bundles.

## Search connection and empty reports

Enable free Mwmbl or configure your optional Brave/Serper/SerpApi connection for general web-index snippets. Wikipedia and news cover only some names. Paid providers use your own key and plan; review their current quotas and charges. Search keys save with Windows encryption by default and restore after restart/update; uncheck Save for session-only use. Keys are never placed in the case database. Original result pages are not fetched by index searches.

A completed report means processing finished. Its outcome separately states whether online records were returned, sources failed, no search completed, or the completed indexes had no matches. Offline phone metadata is not an online match. Use **Check public sources** for canaries, then create a new report after fixing a connection; saved snapshots are immutable.

## Social profile inputs

Use the Instagram, TikTok or VSCO field for a handle (optionally beginning with `@`) or a full profile URL. Auto detect in Research recognizes supported profile URLs. VSCO `vsco.co/example-name/gallery` normalizes to `example-name`. Shared short links and individual post/video links must be replaced with full profile addresses. Profile URLs pasted only into **Reference URLs** stay context; use the platform field to run index searches.

Each platform uses its own search scope and retains supplied canonical references in the report, without treating those addresses as retrieved evidence. Identical handles across platforms are separate inputs and do not establish common ownership. Older saved cases load with empty new fields. Previous report snapshots remain unchanged; generate a new one to include new profiles.
