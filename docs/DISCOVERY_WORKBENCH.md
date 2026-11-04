# Discovery workbench (2.14)

**Version 2.16:** the Windows release includes managed theHarvester, Photon and Osintgram services, saved setup choices, a native reviewed-browser relay and an active bounded AI case pipeline. Start with [Automatic setup](AUTOMATED_SETUP.md); manual-service instructions below remain optional alternatives.

Save/select a case, then use Discovery workbench above the report. These features work without a paid search key. The crawler needs separate direct-request approval. The model participates when an AI-assisted case or manual draft is approved.

## Chrome and Firefox capture

Download `Reviewed-Evidence-Extension.zip` from the same release as Vidocq and extract it to a local folder. Chrome: open `chrome://extensions`, enable Developer mode, choose Load unpacked and select that folder. Firefox: open `about:debugging#/runtime/this-firefox`, choose Load Temporary Add-on and select manifest.json. Firefox's temporary install lasts until restart; this helper is not a signed store extension. No automatic browser installation is attempted.

On a public HTTPS page/search result list, select the text/results you reviewed. Click the extension action, then **Capture selection to local JSON**. It downloads the selected text, page URL/title/time and links within the selection. It reads only the active tab after your click, has no background collection, and sends no network requests. Browser-protected pages cannot be captured. Some search engines use redirect links; these remain captured URLs, not verified destinations.

In Vidocq choose Browser JSON, select the downloaded file, review the preview, check approval and import. Evidence stays in the local notebook and is attached automatically to future reports from this case. User-captured links remain assertions about the captured page, not independently fetched evidence or ownership proof. The JSON download is an external copy and remains outside Burn Vidocq's deletion scope.

## Photon integration

[Photon](https://github.com/s0md3v/Photon) is GPLv3 upstream software. The Windows release includes a pinned separately executed Photon companion with strict public HTTPS/robots/scope budgets. Choose included Photon or the native collector in the website collector selector. You can also export JSON from a separately installed Photon (`-e json`) and import it with the actual crawl root. Imports support URL entries in internal, external, intel, scripts, files and endpoints; other data is ignored. At most 300 links and a 150 KB input; saved evidence must fit 99 KB. Empty imports are rejected.

Photon's aggregate datasets lack per-page link provenance. Reports label these `photon-aggregate-lead`, not proof that the root page published each link. Import time is recorded, not invented original collection time. Importing makes no network requests. These imported URLs are not automatically searched or crawled.

## Public links and bounded crawling

The separate direct-capture button runs Vidocq's own small collector, not Photon. Approve one public HTTPS hostname and choose 1–5 pages, depth 0–2. Reads robots.txt first; stops if unavailable/disallowed. Uses public DNS only, pins the validated address for TLS, follows no redirects, sends no cookies/auth/proxies, and does not execute JavaScript. Starts without query parameters; does not follow external or obvious account/action links. One-second minimum spacing (or the site's crawl delay), eight-second socket timeout, 1 MB pages, 100 outgoing edges and a 60-second loop budget. Final in-flight request can finish after the loop budget. The 100-edge cap is stated in results; truncated evidence is not full-site coverage.

Each edge preserves source page, target, observed date and source content hash. Reports cite the notebook snapshot containing that observation. A published link is corroborating linkage, not proof of account ownership. Analyst ownership decisions remain separate. Sites can log or alert on visits: use browser-reviewed imports when direct requests are inappropriate. Errors, redirects and blocks are coverage gaps, not absent accounts. This is not a search-engine index or a way to access private content.

## Queries, aliases and checker coverage

Preview deterministic query variants: supplied full names, first+last names, usernames, dated historical aliases, exact supplied reference URLs and separate location/employer combinations. Automatic investigations add the extra variants within existing 40-search/budget limits. Search logs preserve each variant's origin. Historical handles enter context/index searches only; they do not automatically enter current-account checker queues. Alias records retain platform, first/last seen dates, supporting URL, stable ID and successor URL as supplied unverified assertions. Vidocq does not automatically prove that IDs/redirects match or that an old handle is still owned by the same person.

The bundled Maigret Instagram public checker is held unavailable because it is unreliable. Use browser evidence or the separately configured Osintgram connector. Other sites can be unsupported/blocked; diagnostics retain each selected site's outcome. An opt-in GitHub/octocat positive canary checks that specific configured checker now; it does not certify other checkers or establish account ownership. Broader independently verified positive/negative platform fixtures remain future evaluation work.

## Optional local model

Run your own [llama.cpp-compatible local server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server) with a model you selected for your hardware/license, bound to 127.0.0.1. Set port/model in Search connection and enable for the session. Vidocq calls only `http://127.0.0.1:<port>/v1/chat/completions`; proxy environment variables and redirects are disabled. Alternatively use the [managed installer added in 2.15](LOCAL_AI_SETUP.md), which downloads the recommended model/runtime after approval and manages their lifecycle. No cloud fallback or model tools.

The manual workbench differs from the active [AI case pipeline](AUTOMATED_SETUP.md#the-ai-now-participates-in-a-case). Approve each manual draft. Query mode selects up to five entries from the deterministic case query list and rejects unknown indexes; this manual mode executes nothing. Cited excerpt mode sends up to 12 non-rejected report excerpts (1,500 characters each) and accepts at most six 10–600-character verbatim quotes with existing citation IDs. Unknown citations or unsupported quotations reject the draft. Source content can itself be wrong; quotation validation does not validate its claims. Drafts never alter evidence or ownership decisions. Manual runtime settings and standalone drafts are session-only; managed preferences and case-report snapshots persist. Do not configure a local runtime to forward to a cloud service. Model quality/latency varies. CI uses deterministic fixtures; separate local validation exercises the real pinned model on synthetic content.
