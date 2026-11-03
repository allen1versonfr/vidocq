# Automatic investigations, Steam and Osintgram — 2.9.0

## From known clues to a report

Open Cases & reports. Supply names, phones, emails, usernames, Instagram/TikTok/VSCO profiles, Steam accounts, domains or public IPs. You can also provide employer/location context, notes, reference URLs and selected notebook evidence. Save up to 15 explicit searchable identifiers. Enable Automatic investigation, choose limits, confirm the selected source activity, then select Investigate and generate report.

The engine searches each supplied identifier, extracts explicit new identifiers from relevant returned evidence, and follows eligible clues within the selected depth/search budget. Every discovered clue retains its parent citation, depth, processing status and reason if it was not searched. Explicit identifiers in supplied notes, reference URLs and non-rejected selected notebook excerpts can enter the plan too (up to five such supplementary inputs). It does not send complete notes/documents to a provider or follow arbitrary reference pages. Supplied name/employer/location terms can be combined in a selected web-index context search.

Defaults are 25 identifier searches, up to 5 discovered identifiers, and one follow-up level. Limits can be set to 1–40 searches, 0–10 follow-ups, and 0–2 levels. Each identifier search can call several providers. These are work limits, not a dollar spending guarantee; review your provider account limits. Supplied inputs and supplementary/context searches consume the budget before new clues. The report explicitly lists inputs left unsearched.

The engine is deterministic; it does not execute instructions found in snippets, generate a biography, invent contact details or assign identity-confidence percentages. Common-name-only hits do not automatically expand. A returned record must match a supplied strong identifier (phone/email or supplied account reference), contain multiple distinct supplied identifiers, or explicitly contain a supported previously discovered identifier. Explicit profile results from the opted-in connectors can also supply follow-ups. Identical handles across platforms count once for co-occurrence, not as independent corroboration. Ordinary reference-page hostnames are not automatically treated as subject domains; explicit URLs in returned text can supply domain clues. CBL claims do not trigger automatic follow-ups.

## Read the generated report

The report includes:

- An executive summary tied to the returned evidence, without an unsupported identity conclusion.
- Stronger leads where multiple distinct supplied identifiers co-occur; this is relevance evidence, not ownership proof or independent corroboration.
- Leads needing review, results without a supplied-identifier match, and any previously rejected notebook evidence.
- Explicit profile-name differences for review (aliases can explain them; this is not comprehensive contradiction detection).
- Discovered identifiers, parent citations, follow-up trail, source coverage and unsearched inputs.
- Unanswered questions and the complete bounded evidence/citation sections.

Generate printable HTML, Markdown or JSON. HTML loads no remote resources; use your browser's Print → Save as PDF. Cancel investigation stops queued work and requests cancellation of active Osintgram work. An in-flight network request may finish before cancellation takes effect. Completed evidence is retained as a cancelled, exportable partial snapshot. It is not silently resumed after shutdown. Older reports and manually created notebook records remain unchanged.

Report evidence text is limited to 12,000 characters per record; truncation is labeled. Provider response and result-count limits also apply. A completed run means processing finished, not that the subject was identified or every source was searched. Enable free Mwmbl web search for automatic name/phone/handle index retrieval without an account or key. Its smaller index may miss profiles; Brave is an optional alternative with its own key and plan. Offline phone metadata cannot identify an owner or live location. The connection-readiness notice makes missing connections visible before a run.

## Steam-OSINT capabilities

Inspired by [Frontline-Femmes/Steam-OSINT](https://github.com/Frontline-Femmes/Steam-OSINT), Vidocq implements a separate native adapter against Valve's API. It does not run the upstream Google Apps Script or require Google Sheets. No third-party implementation code is bundled.

1. Obtain your own Steam Web API key using Valve's normal developer-key process. No Steam account or key is created by Vidocq.
2. In Search connection enter the key and enable Steam. Vidocq holds the key in process memory; it is excluded from cases, source references, reports and workspace bundles.
3. Enter a SteamID64, vanity name or full `steamcommunity.com/id/...` or `/profiles/...` URL in the case's Steam field. Auto detect in Research recognizes supplied Steam profile URLs/SteamID64; ordinary Research uses the index, while the case's direct-connector permission controls API collection.
4. Allow configured connectors for the case. Optionally provide a numeric Steam game AppID to check the returned library for that game.

The adapter resolves vanity names, retrieves disclosed profile fields, summarizes an available game library (up to 100 shown games) and recent games, and records playtime in minutes. Missing/private library data is an access gap, not proof that no games are owned. A game not listed in a response is described as not listed; visibility and completeness limits remain. Country/creation/name fields are reported only as supplied by Valve, without inferring a person's identity or gameplay location. Avatars and remote media are never loaded.

Requests go only to fixed HTTPS `api.steampowered.com` endpoints. Redirects are refused, network responses are capped at 2 MB, and failures/quota problems remain in coverage. The session cap is 100 API requests, including vanity resolution. A Steam account search typically uses 3 requests, or 4 with vanity resolution, plus an optional CBL request. Keys are sent only to Valve; they are not sent to CBL or Osintgram.

The optional Community Ban List switch queries only `https://communitybanlist.com/graphql` for the supplied/resolved SteamID. Returned provider reputation/risk labels and active/expired ban records are attributed claims, never a Vidocq risk verdict or identity match. Up to 20 returned records per list are shown, with truncation/completeness caveats. Service access and schema may change; unavailable responses are errors, not a clean-record conclusion. No live CBL result has been independently validated for this release.

## Osintgram connection

[Datalux/Osintgram](https://github.com/Datalux/Osintgram) 2.x provides a local web API. Vidocq interoperates over that API rather than copying GPL-3.0 source into its executable. Keep Osintgram separately installed and consult its [setup guide](https://github.com/Datalux/Osintgram/blob/master/doc/web-ui.md) for requirements and backend terms.

One-time setup outside Vidocq:

```powershell
git clone https://github.com/Datalux/Osintgram.git
cd Osintgram
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn src.web.app:app --host 127.0.0.1 --port 8000
```

Open Osintgram locally and configure your HikerAPI account/key or its supported Instagram backend there. Its credential storage, account/session behavior, access restrictions and any charges are controlled by Osintgram and its backend, not Vidocq. Do not expose the unauthenticated companion service beyond loopback. No Instagram password or HikerAPI key is requested or saved by Vidocq.

In Vidocq's Search connection, enable the Osintgram bridge and set its local port (default 8000). The hostname is fixed to `127.0.0.1`; remote/custom URLs are not accepted. In the case allow connectors and choose supported commands:

- Profile information and public bio links/contact fields (always included).
- About this account.
- Captions from up to five recent posts.
- Hashtags from up to five recent posts.

The bridge checks `/api/about`, then requests profile information through `/api/run`. Private or unknown-privacy profiles do not trigger further content requests. For explicitly public profiles, selected additional commands are submitted in a second bounded request. It does not use Osintgram's AI mode or send the full case/notes to a local or remote language model. The initial profile run passes `max_items=5`; additional commands receive the remaining budget after the reported profile request count. Both use bounded feed parameters, a one-hour cache lifetime and a cancellable run ID. Osintgram enforces its own upstream request budget; this is not a billing guarantee. Vidocq caps itself at 20 Osintgram profile runs per session. Transport reads have size/time limits; errors/timeouts request backend cancellation. The source coverage records the localhost bridge and the returned profile reference.

This integration does not expose all Osintgram commands: follower/following enumeration, bulk contact harvesting, location reverse-geocoding, comments, stories and media downloads are not included. Returned profile media URLs and precise address/coordinate fields are filtered out. Captions/hashtags can be unavailable on private profiles; no private-access bypass is attempted. Ownership of a supplied or discovered handle remains unverified.

## Research boundaries and privacy

Steam and Osintgram are **additional opt-in data connectors**, beyond the original third-party-index-only workflow. Enabling a connection alone does not authorize it in a case: the case must also allow connectors, and the run must be confirmed. Eligible discovered profiles share that bounded permission. The provider/platform can log requests; no anonymity or absence-of-notification guarantee is made.

The app never substitutes a clue into an unreviewed tool URL, runs arbitrary downloaded tools, fetches arbitrary original pages, performs password recovery, sends messages, performs active network scans or identifies faces. No search engine/provider can promise all information or definitive identity resolution. Reference matching and account resolution are attributed to sources and remain distinct from real-person ownership.

Reports, inputs, selected evidence, discovered identifiers and the non-secret connector-configuration snapshot are stored in the existing local SQLite workspace without encryption. Workspace bundles include them and optionally encrypt the export. Steam keys remain only in Vidocq process memory; other provider credentials stay where the user configures them. Existing case defaults stay in legacy mode; newly created cases in the UI enable Automatic investigation, with direct connectors off until explicitly selected.
