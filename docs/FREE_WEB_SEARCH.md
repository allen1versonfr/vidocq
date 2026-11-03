# Web search without a paid service

Open Search connection and click **Enable free web search**. Mwmbl anonymous mode needs no signup, key, payment card or subscription. Then run Research or a confirmed case report. Enablement is session-only; no query is sent just by selecting/enabling the provider.

Vidocq uses Mwmbl's documented v2 search API. Its published anonymous allowance is currently 1,000 requests/month per public IP, at one request/second. Shared networks share the allowance. Vidocq adds a 100-request session cap, 1.1-second request spacing, 15-minute in-memory cache and cooldown after rate/quota errors. It never adds a Mwmbl API key, authorizes billing or silently switches to a paid service. Quotas and service availability can change: [provider details](https://developer.mwmbl.org/).

Mwmbl's index is smaller than major commercial indexes, so a successful empty search does not prove that an account or public mention is absent. Searches retrieve index titles, snippets and source URLs. Original result pages and thumbnails are not loaded. Malformed responses, access failures and quota limits remain errors/coverage gaps rather than no-match results.

Brave is an optional provider in the same menu. Existing keys and VIDOCQ_BRAVE_API_KEY remain supported. Its charges/plan are under your provider account. Choosing free Mwmbl never forwards the Brave key.

## Chrome and Firefox

Prepared Google, Bing and DuckDuckGo links open through your default browser. Case reports now include an Open search in default browser button beside each prepared query. Review those results and save selected evidence in Notebook; saved findings can be attached to a case. Browser searches are useful when the free index misses something. Vidocq does not silently automate your logged-in browser, bypass CAPTCHAs, or count manually opened searches as automatically retrieved results.

DuckDuckGo's non-JavaScript public search returned an HTTP 202 challenge in local validation. It was not added as a supposedly working automatic provider. No challenge was solved or bypassed.

Personal-name research now uses the selected web index instead of padding reports with unrelated Wikipedia/news fallback records. Topics and explicit news research keep their existing sources. Matching names/handles remain leads, not proof of identity.
