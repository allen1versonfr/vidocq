## Vidocq 2.4.0 — Framework source catalog

- Added a searchable, categorized OSINT Framework snapshot: 1,171 entries, including 1,040 labeled free/freemium by upstream. Paid entries and unknown pricing are separate filters.
- Every catalog entry shows actual integration state, upstream status, registration/local-install flags, and limitations. A catalog listing is not a functioning provider integration.
- Added Search indexed pages for the free-access entries: a Google site-index search, with no original-source visit, tool execution, scan submission, or account checks.
- Added integrated Open Library topic/book metadata and prepared DuckDuckGo, Google Scholar, PubMed, Open Library, and Google Patents searches. No book covers or result-page assets load automatically.
- Replaced the old blanket-exclusion report with a per-entry coverage report. Included the upstream revision, checksum, sync script, and MIT license.
- Bundled the catalog with the executable for offline directory browsing. GitHub self-updates and notebook migration are preserved.
- 53 automated tests plus Windows frozen executable/replacement/restart/rollback checks gate publication.

### Coverage boundary
The framework labels 784 entries free, 249 freemium, 7 mixed free/freemium, 30 paid, and 101 unknown. These labels are not individual live pricing or availability verification. Vidocq does not automatically run all of these tools. Only its reviewed adapters retrieve results internally; other catalog entries offer index searches. This preserves the requested restriction against target-contact/notification-prone sources.

### Updating
Use Updates in Vidocq 2.3.0 or newer, with a Contents: read token while the repository is private. The original 2.2.1 executable still requires one manual replacement.
