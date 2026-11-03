# Data and privacy

Browser-reviewed excerpts and account decisions/history stay in the local SQLite workspace and user-created exports/backups. Captures are user-supplied, never silently fetched. Burn deletes only previewed paths after typed confirmation; external exports and browser/OS/provider records remain outside its scope. See [review and burn scope](REVIEW_AND_BURN.md). This release does not download or run a language model.

[← Project overview](../README.md)

## Local data

| Item | Handling |
| --- | --- |
| Cases and report snapshots | Stored in the existing SQLite workspace, including supplied identifiers, notes, selected evidence and report results; not encrypted. |
| Saved findings | Stored in `%LOCALAPPDATA%\Vidocq\workspace.sqlite3`; unencrypted SQLite. |
| Text queries | Not automatically saved as findings. Saving a returned record includes query context in the finding. |
| JSON exports | Written where your browser or native download dialog saves them; contain saved findings and source references. |
| Image files and SauceNAO keys | Not intentionally persisted by the app. Image-search source references can be saved as notebook findings. |
| Brave Search API key | Held in process memory only; optional `VIDOCQ_BRAVE_API_KEY` environment variable is managed by you. Sent only to the fixed Brave API host, never included in cases/reports. |
| GitHub token entered in Updates | Kept in process memory for the session; not written into the notebook or update jobs. |
| `VIDOCQ_GITHUB_TOKEN` | Optional OS environment variable managed by you; persistent storage, if configured, is outside the app. |
| Diagnostics | `startup.log` and `update-result.json` in the data folder. Review before sharing. |
| Update files | Temporary downloads/helper files, plus a `.previous` executable beside the app for recovery. |

There is no built-in notebook cloud sync or analytics. The default data directory can be overridden with `VIDOCQ_DATA`; older `ALL_SEEING_EYES_DATA` and `OSINT_DESK_DATA` variables are supported for compatibility. When no current notebook exists, the app can copy an earlier AllSeeingEyes or OSINTDesk notebook without deleting the original.

## Network activity

| Action | Who receives data |
| --- | --- |
| Domain research | Internet Archive and crt.sh receive the submitted domain. |
| IP research | The reviewed registry endpoint receives the submitted public IP. |
| Name / case research | The enabled web index receives the supplied name. Unrelated Wikipedia/news fallback queries are no longer used for personal-name research. No original result page is fetched. |
| Instagram / TikTok / VSCO | Supplied handles and canonical references stay in the local case/report. With web search enabled, platform-scoped handle queries go to the selected index only. Prepared browser links go to the chosen search engine when clicked. No profile, post, image or video is fetched and no account availability or ownership is tested. |
| Optional general web search | When enabled, free anonymous Mwmbl or optional Brave receives exact-phrase name, username, email or phone queries and scoped Instagram/TikTok/VSCO handle queries, including case inputs. Only API snippets are retrieved; no original page or thumbnail is fetched. |
| Public source health check | Wikipedia receives Ada Lovelace and ARIN receives 8.8.8.8; no case details are sent. |
| Phone analysis | Offline metadata only; no calls, texts or owner/account checks. Prepared search URLs include the number, but are not automatically opened. |
| Topic research | Wikipedia receives the search term. |
| Prepared browser search | The chosen search/index provider receives the query when you open it. |
| Image search | SauceNAO receives a metadata-stripped image and API key after upload consent. |
| Update check | GitHub receives an update request at app launch or when you check manually. A token is included if supplied. |
| Update download | GitHub and its allowed asset hosts serve the executable. |

Providers also see ordinary connection information, such as your IP address, and may log requests. Passive research is not a promise of anonymity or zero notification. Opening original pages from an external browser can contact those sites.

Default index mode does not resolve supplied accounts or fetch original pages. Opt-in Steam/Osintgram connectors can resolve supplied and eligible discovered accounts through their reviewed APIs. Vidocq does not scan submitted IPs/domains, query their DNS servers, attempt logins or account recovery; Osintgram manages its separately configured backend access. No remote result thumbnails, third-party scripts, or external fonts are loaded by the app UI. This repository’s README uses external badge images when viewed on GitHub; those are separate from the application.

## Protecting your workspace

Use device encryption and operating-system access controls if your findings are sensitive. Back up the database while Vidocq is closed. Do not include API keys, GitHub tokens, personal queries, or private notebook records in bug reports. Use only images and information you have permission to process, and assess returned evidence before acting on it.

## Investigation evidence and backups (2.7.0)

Imported documents/screenshots, original bytes and hashes, extracted text, entities, relationships, timeline events and assessment history are stored locally in SQLite without encryption. OCR uses Windows locally; no OCR service receives files. Complete workspace bundles optionally use password encryption. This does not encrypt local SQLite data or report/notebook exports. Bundle passwords are never persisted. See [the investigation guide](INVESTIGATION.md) for limits and restore behavior.

## SpiderFoot imports (2.8.0)

JSON imports preserve original files and records locally. No SpiderFoot server, source URL or index provider is contacted by preview/import. Imported connections are unverified discovery leads. Original files and metadata remain unencrypted in SQLite and are included in workspace bundles. See [SpiderFoot import](SPIDERFOOT.md).

## Automatic investigations and optional direct connectors (2.9.0)

Confirmed automatic runs can send discovered identifiers to the existing index providers within selected limits; name/employer/location context can be combined in selected web-index queries. The complete notes/documents are not sent. Opt-in Steam requests go to Valve, optionally CBL; its key stays in Vidocq memory and is excluded from stored/exported source references. The Osintgram bridge sends only the selected Instagram handle and fixed bounded commands to a user-configured loopback port. Osintgram's backend handles its credentials, billing and platform access, which can involve HikerAPI or Instagram. No remote media is loaded by Vidocq.

These connectors require both session enablement and per-case permission. They go beyond third-party-index-only collection. Logs, charges, access restrictions and platform visibility are provider-dependent. Case snapshots retain discovered clues, citations and non-secret connector settings; local SQLite remains unencrypted. See [the setup and privacy details](AUTOMATIC_INVESTIGATIONS.md).

## Included Maigret service

The setup button starts bundled Maigret locally without installing software, downloading a runtime or querying accounts. Vidocq chooses a loopback port and keeps its generated key in memory. The service stops on disable/app exit. Each case still needs permission before selected public platforms receive a supplied handle. Advanced manual-service settings remain available.

## Free web search

Mwmbl anonymous mode uses the fixed api.mwmbl.org/api/v2/search/ endpoint without a key, account or billing authorization. Queries and connection information go to that provider. Repeated results are cached in memory for 15 minutes; requests are spaced at least 1.1 seconds apart and capped at 100 per app session. HTTP 429 stops queries during a cooldown. Provider monthly/IP quotas also apply. No paid provider is contacted as an automatic fallback. Brave credentials, if separately configured, are never forwarded to Mwmbl.
