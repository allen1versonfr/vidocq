# Discovery workbench (2.14)

Save/select a case, then use Discovery workbench above the report. These features work without a paid search key. Normal case runs never start the crawler or model.

## Chrome and Firefox capture

Download `Reviewed-Evidence-Extension.zip` from the same release as Vidocq and extract it to a local folder. Chrome: open `chrome://extensions`, enable Developer mode, choose Load unpacked and select that folder. Firefox: open `about:debugging#/runtime/this-firefox`, choose Load Temporary Add-on and select manifest.json. Firefox's temporary install lasts until restart; this helper is not a signed store extension. No automatic browser installation is attempted.

On a public HTTPS page/search result list, select the text/results you reviewed. Click the extension action, then **Capture selection to local JSON**. It downloads the selected text, page URL/title/time and links within the selection. It reads only the active tab after your click, has no background collection, and sends no network requests. Browser-protected pages cannot be captured. Some search engines use redirect links; these remain captured URLs, not verified destinations.

In Vidocq choose Browser JSON, select the downloaded file, review the preview, check approval and import. Evidence stays in the local notebook and is attached automatically to future reports from this case. User-captured links remain assertions about the captured page, not independently fetched evidence or ownership proof. The JSON download is an external copy and remains outside Burn Vidocq's deletion scope.

## Photon integration

[Photon](https://github.com/s0md3v/Photon) is GPLv3 upstream software. Vidocq does not bundle, download or execute Photon. Export JSON with your separately installed Photon (`-e json`), then choose Photon JSON, enter the actual approved crawl root and import the reviewed file. Supports URL entries in internal, external, intel, scripts, files and endpoints; ignores non-URL data and other datasets. At most 300 links and a 150 KB input; saved evidence must fit 99 KB. Empty imports are rejected.

Photon's aggregate datasets lack per-page link provenance. Reports label these `photon-aggregate-lead`, not proof that the root page published each link. Import time is recorded, not invented original collection time. Importing makes no network requests. These imported URLs are not automatically searched or crawled.

## Public links and bounded crawling

The separate direct-capture button runs Vidocq's own small collector, not Photon. Approve one public HTTPS hostname and choose 1–5 pages, depth 0–2. Reads robots.txt first; stops if unavailable/disallowed. Uses public DNS only, pins the validated address for TLS, follows no redirects, sends no cookies/auth/proxies, and does not execute JavaScript. Starts without query parameters; does not follow external or obvious account/action links. One-second minimum spacing (or the site's crawl delay), eight-second socket timeout, 1 MB pages, 100 outgoing edges and a 60-second loop budget. Final in-flight request can finish after the loop budget. The 100-edge cap is stated in results; truncated evidence is not full-site coverage.

Each edge preserves source page, target, observed date and source content hash. Reports cite the notebook snapshot containing that observation. A published link is corroborating linkage, not proof of account ownership. Analyst ownership decisions remain separate. Sites can log or alert on visits: use browser-reviewed imports when direct requests are inappropriate. Errors, redirects and blocks are coverage gaps, not absent accounts. This is not a search-engine index or a way to access private content.

## Queries, aliases and checker coverage

Preview deterministic query variants: supplied full names, first+last names, usernames, dated historical aliases, exact supplied reference URLs and separate location/employer combinations. Automatic investigations add the extra variants within existing 40-search/budget limits. Search logs preserve each variant's origin. Historical handles enter context/index searches only; they do not automatically enter current-account checker queues. Alias records retain platform, first/last seen dates, supporting URL, stable ID and successor URL as supplied unverified assertions. Vidocq does not automatically prove that IDs/redirects match or that an old handle is still owned by the same person.

The bundled Maigret Instagram public checker is held unavailable because it is unreliable. Use browser evidence or the separately configured Osintgram connector. Other sites can be unsupported/blocked; diagnostics retain each selected site's outcome. An opt-in GitHub/octocat positive canary checks that specific configured checker now; it does not certify other checkers or establish account ownership. Broader independently verified positive/negative platform fixtures remain future evaluation work.

## Optional local model

Run your own [llama.cpp-compatible local server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server) with a model you selected for your hardware/license, bound to 127.0.0.1. Set port/model in Search connection and enable for the session. Vidocq calls only `http://127.0.0.1:<port>/v1/chat/completions`; proxy environment variables and redirects are disabled. No model or runtime is bundled/downloaded, no cloud fallback, no model tools.

Approve each draft. Query mode selects up to five entries from the deterministic case query list and rejects unknown indexes. It executes nothing. Cited excerpt mode sends up to 12 non-rejected report excerpts (1,500 characters each); accepts at most six 10–600-character verbatim quotes with existing citation IDs. Unknown citations or unsupported quotations reject the entire draft. Source content can itself be wrong; quotation validation does not validate its claims. Drafts are shown separately and never alter evidence, ownership decisions or immutable reports. Settings and draft output are session-only unless you explicitly copy/export them. Do not run a local runtime configured to forward to a cloud service. Real model quality/latency varies; automated validation uses a deterministic loopback fixture rather than downloading weights.
