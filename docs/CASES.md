# Phone analysis, cases and reports

[← Project overview](../README.md)

## Phone numbers

Open **Phone**, enter a number, and choose its two-letter region if you entered a national number rather than an international `+` number. The default region is US. Choose **Analyze locally**.

Vidocq uses bundled libphonenumber metadata to show E.164/international formatting, country calling code, numbering region, number type, numbering-plan validity, allocation region, original carrier allocation when available, and possible time zones. No call, text, account-existence test, live carrier check, owner lookup or location tracking is performed. A valid numbering-plan format does not establish whether a number is assigned, reachable or current. Carrier and allocation metadata can be stale after number portability or reassignment.

The Research tab also accepts **Phone number** explicitly and detects common numeric phone formats. Its national-number default is US; use the dedicated Phone tab or case region field for another country.

## Give Vidocq several details together

Open **Cases & reports** and create a case. You can supply:

- Up to three names or aliases.
- Up to five usernames, emails, phone numbers, domains, or public IPs per field.
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
| Phone | Offline numbering-plan metadata | No owner identification or live verification. |
| Username / email | Prepared index-search links | The report explicitly says these searches were not automatically run. |
| Notes / reference URLs | Preserved as supplied context | Not automatically searched, visited or scraped. |
| Selected notebook findings | Included with supplied-evidence labels | Not treated as independent verification or assumed to concern the same person. |

No original news articles, profiles, reference URLs or remote thumbnails are fetched. GDELT requests retrieve indexed article titles and source metadata only. Sources can log queries. Empty results, provider errors, and unsupported searches remain visible in the coverage section.

## Images and other evidence

For image evidence, use **Image search**, confirm the SauceNAO upload, save relevant results to Notebook, and select those findings in the case. The case form does not automatically upload files or identify people from faces. Preserve observations from other documents in the notes or notebook with their source references; binary document ingestion and automatic OCR are not included in this release.

## Read the report

Each report separates retrieved index records, offline metadata, and supplied notebook evidence. Evidence entries include citation IDs such as `R001`, provider, source request, optional source reference, matching supplied inputs, retrieval time, and an **Unverified relevance** label. Exact duplicate records can be consolidated across inputs; this is not an identity match or independent corroboration.

The summary lists processed inputs, record counts, provider failures and prepared searches that were not run. No AI-generated biography, identity confidence percentage, private-address discovery or “complete background check” claim is made. The report represents everything returned by the documented searches in that run, not everything that exists about a person.

## Export

Select a completed snapshot and export:

- **Printable HTML:** self-contained, with no scripts, images, remote resources or automatically opened source links. Open it and use your browser’s Print → Save as PDF.
- **Markdown:** readable text with source and evidence sections.
- **JSON:** the complete structured snapshot for inspection or later processing.

Exports contain the supplied identifiers and selected evidence. Cases, notes and report snapshots are not encrypted by the app. Protect the database and exports accordingly. Exports are not currently importable back into the case UI.

## Search connection and empty reports

Version 2.5.1 can retrieve Brave index snippets for names, usernames, emails and phones when you supply and enable your own API key in **Search connection**. Without it, those general web searches are not run. Wikipedia and news cover only some names. Brave may require payment-card signup and charges beyond its limited monthly credits; review the provider plan. Keys are held only in memory (or an environment variable managed by you), never in the case database. Original pages are not fetched.

A completed report means processing finished. Its outcome separately states whether online records were returned, sources failed, no search completed, or the completed indexes had no matches. Offline phone metadata is not an online match. Use **Check public sources** for canaries, then create a new report after fixing a connection; saved snapshots are immutable.
