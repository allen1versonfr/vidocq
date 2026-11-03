## Vidocq 2.5.0 — Phone analysis and case reports

- Added Phone analysis for international/national normalization, country calling code, numbering region, number type, allocation region and original carrier metadata. This is offline numbering-plan data, not an owner lookup or live location/carrier check.
- Added Cases & reports: supply names, usernames, emails, phones, domains, public IPs, reference URLs, notes and explicitly selected notebook evidence together.
- Added background report runs, progress, persistent cases, editable inputs and immutable report snapshots.
- Names search Wikipedia and GDELT’s recent news index. Existing domain/IP index adapters are retained. No original article, profile or reference URL is fetched.
- Reports separate retrieved records, offline metadata, supplied evidence, errors, empty results and searches not automatically run. Records have source citations and unverified identity relevance; exact duplicates are consolidated without claiming identity or independent corroboration.
- Export printable, self-contained HTML, Markdown and JSON. Open HTML and use Print → Save as PDF.
- Updated updater/repository references after the rename to allen1versonfr/vidocq.
- 72 automated tests plus actual Windows frozen app, phone/case/report/export and updater replacement/restart/rollback checks gate publication.

### Coverage limits
Email, username and phone web searches remain prepared browser links, not automatic owner/account searches. Phone metadata does not identify a person or live location. A report covers the listed supported searches and supplied context, not everything on the internet. Common names, number reassignment and stale indexes can cause false matches. No calls, SMS, account checks, live target scans, facial identification or unconsented image uploads are added.

### Use it
Update from the Updates tab, then open Cases & reports. Choose a phone region for national numbers, enter one identifier per line, save the case, confirm the listed index requests and generate a report. For image findings, use Image search, save relevant results to Notebook and select those findings in the case. Cases/reports and exported identifiers are not encrypted by the app.
