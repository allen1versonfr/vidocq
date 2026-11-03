# Validation for Vidocq 2.6.0

98 automated tests pass locally. New coverage includes Instagram/TikTok/VSCO handle and profile URL normalization, VSCO gallery URL and dash support, auto detection, wrong hosts/credentials/ports/control characters/post/short-link rejection, scoped Google/Bing/DuckDuckGo queries, fixed Brave scopes, returned-host filtering, disconnected searches making no requests, social-only cases, per-platform deduplication/limits, old-case compatibility, canonical references in exports, and transparent multi-resolution ICO generation. Existing cases, research, images, catalogs and updater recovery remain covered.

Frontend syntax and HTML field/structure checks pass. Live public Wikipedia and RDAP canaries returned records. CI requires at least one nonempty public canary. No live Brave request was made without a user's API key; scoped API responses are mocked in tests. No social profiles are visited by these tests or by the feature.

The Windows pipeline builds the ICO, embeds it in Vidocq.exe, checks exact PE icon frame bytes, and runs the actual frozen social/phone/case/report/export endpoints and updater replacement/restart/failed-start rollback. BUILD_INFO.json records those gates before publication. The native window is not manually exercised; Windows shell icon caching and identity relevance are not established by these tests.
