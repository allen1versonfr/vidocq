## Vidocq 2.5.1 — Search results and diagnostics

- Fixed Auto detect treating full names as usernames.
- Added an optional Brave Search API connection to retrieve actual indexed snippets for names, usernames, emails and phone numbers, including case reports. Original result pages are never fetched.
- Added clear disconnected, failed, incomplete and no-match outcomes in research, case reports and exports. Offline phone metadata is not counted as an online search.
- Added Search connection settings and public Wikipedia/RDAP health checks. Keys remain in memory, are sent only to the fixed API endpoint, and are never included in reports. Redirects are blocked. Requests are capped at 100 per app session.
- Reject malformed encyclopedia/registry/search responses instead of showing false empty results.
- Added a live public-index canary gate before the Windows build and release.

### Set up general web search
Open **Search connection**, enter your own Brave Search API key, enable it, then rerun research or generate a new report. Brave requires signup and a payment card. Its current $5 monthly credits are limited; check provider pricing and usage. This optional integration is not unlimited free search. No account or key is included. Without it, Wikipedia/news/registry adapters still work where applicable; email/username/phone web searches remain prepared links.

83 automated tests, frontend syntax, live public canaries and actual Windows executable/report/updater checks gate publication. Brave response/error/security tests use mocked responses; no live Brave request was tested because no user API key was supplied. Matching index mentions do not verify identity or phone ownership. Source outages and incomplete indexing remain possible.
