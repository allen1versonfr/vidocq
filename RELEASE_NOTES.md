## Vidocq 2.6.0 — Social profiles and Windows identity

- Added Instagram, TikTok and VSCO input types in Research, including automatic detection of full profile URLs.
- Added separate platform fields in Cases & reports, normalized and deduplicated handles, saved profile context, per-platform source coverage and canonical supplied profile references in HTML/Markdown/JSON exports.
- VSCO accepts profile URLs ending in `/gallery` and handles with dashes. Short links, post/video URLs, unexpected hosts and unsafe URL forms are rejected without being visited.
- An enabled Brave Search API connection retrieves platform-scoped index snippets. Without your own key, prepared Google/Bing/DuckDuckGo queries remain available and no completed online search is claimed. No profile or media pages are fetched, no account is contacted and no ownership is inferred.
- Existing saved cases load with empty social fields; historical report snapshots remain unchanged. Up to five handles per platform count toward the fifteen-input case limit.
- Added an original navy/gold Vidocq magnifier icon, embedded as nine Windows ICO sizes in the executable, plus a matching app mark and browser icon. Stable taskbar grouping uses Vidocq.Desktop. The standalone ICO is included as a release asset.

### Use it
Update to 2.6.0. Choose Instagram, TikTok or VSCO in Research, or paste a full profile URL with Auto detect. For a combined report, add the profiles to their separate case fields, save and generate a new snapshot. Enable your own Brave key in Search connection for automatic indexed retrieval; provider limits and charges may apply.

### Validation and limits
98 automated tests cover profile input validation, URL normalization, query scoping, index-only requests, rejected unsafe links, disconnected states, case persistence/compatibility, exports and icon sizes. Live public Wikipedia/RDAP canaries and actual frozen Windows social/phone/case/report/export and updater recovery checks gate publication. Windows also verifies that the executable contains the exact generated Vidocq icon frames. Brave result parsing is tested with mocked responses; no live Brave request was run without a user key. Index coverage is incomplete and cannot establish identity, account availability or ownership.
