<p align="center">
  <img src="docs/assets/vidocq-banner.svg" alt="Vidocq — Follow the evidence. Public indexes, local workspace." width="100%">
</p>

<p align="center">
  <strong>A portable research workspace for Windows.</strong><br>
  Search public indexes, trace image sources, and keep your findings together.
</p>

<p align="center">
  <a href="https://github.com/allen1versonfr/vidocq/releases/latest"><strong>Download Vidocq.exe</strong></a> ·
  <a href="docs/USER_GUIDE.md">User guide</a> ·
  <a href="docs/UPDATES.md">Updates &amp; recovery</a> ·
  <a href="https://github.com/allen1versonfr/vidocq/issues">Report an issue</a>
</p>

<p align="center">
  <a href="https://github.com/allen1versonfr/vidocq/actions/workflows/windows.yml"><img src="https://github.com/allen1versonfr/vidocq/actions/workflows/windows.yml/badge.svg" alt="Windows build and release status"></a>
  <img src="https://img.shields.io/badge/platform-Windows_10%2F11_x64-172638?style=flat-square" alt="Windows 10/11 x64">
  <img src="https://img.shields.io/badge/interface-pywebview-d4b170?style=flat-square" alt="Python and pywebview interface">
</p>

## Meet Vidocq

Vidocq brings a focused set of research tools into one desktop app: public-record searches, image-source matches, a local evidence notebook, and verified GitHub updates. It keeps the source and context attached to each saved finding so you can distinguish a lead from a conclusion.

The current Windows release is **2.13.0**. Its automated tests and Windows executable checks cover startup, replacement, restart, and failed-start rollback. See [validation](VALIDATION.md) and the [release history](CHANGELOG.md).

## Reviewable investigations and local cleanup

Profile links supply handle clues, locations are searched separately, and Maigret preserves per-site outcomes. Capture reviewed browser excerpts and remember case-specific ownership decisions. Reports distinguish raw records, relevant candidates and analyst confirmations. A preview-and-confirm Burn control removes named local app files and optionally the current Windows executable/adjacent update backup; it does not promise forensic erasure or remove external exports, backups or browser/OS records. [Review and burn guide](docs/REVIEW_AND_BURN.md). [Local LLM assessment](docs/LOCAL_LLM_ASSESSMENT.md).

## Free web search and browser review

In Search connection, click **Enable free web search** to use anonymous Mwmbl without an account, key or payment. Its smaller index and quotas limit coverage. Brave remains optional. Prepared searches can also open in your default Chrome, Firefox or other browser for manual review. [Free search guide](docs/FREE_WEB_SEARCH.md).

## Automatic investigations with Steam and Osintgram

Enter known identifiers and context, set search/depth limits, and generate a report with an evidence-linked summary, discovered clues, relevance groups and coverage gaps. Optional Steam API and local Osintgram 2.x connectors can enrich supplied or eligible discovered profiles when explicitly allowed. Free Mwmbl web search needs no account or key; optional Brave remains available. Steam needs your key, and Osintgram requires its separate configured local service. [Setup and investigation guide →](docs/AUTOMATIC_INVESTIGATIONS.md)

## Additional collectors

Optional HIBP email breach metadata, passive theHarvester domain research and selected-site Maigret username checks now feed case reports. Each requires setup and a case permission. HIBP needs your subscription key; theHarvester needs a separate local service; Maigret is included and starts with the setup button. [Setup and limits](docs/ADDITIONAL_COLLECTORS.md).

## SpiderFoot import

Import standard SpiderFoot JSON results locally with preview, original evidence preservation, typed entities and proposed discovery links. [SpiderFoot import guide →](docs/SPIDERFOOT.md)

## New investigation workspace

Structured evidence, editable/searchable notebooks, evidence-backed entity relationships, timelines, snapshot comparisons, local PDF/screenshot OCR, and encrypted workspace backup/restore are now included. [Investigation guide →](docs/INVESTIGATION.md)

## What you can do

| Workspace | What it offers |
| --- | --- |
| **Cases & reports** | Investigate supplied identifiers/context, follow supported new clues within limits, separate stronger/uncertain leads, and export cited HTML, Markdown or JSON reports. |
| **Social profiles** | Instagram/TikTok/VSCO index searches, Steam API enrichment, and an optional Osintgram 2.x public-profile bridge in explicitly enabled case runs. |
| **Phone** | Normalize numbers and inspect offline numbering-plan metadata without calling, messaging or identifying an owner. |
| **Research** | Look up domains, public IPs, and topics through reviewed third-party indexes. Retrieve indexed mentions with an optional Brave API connection. |
| **Image search** | Search SauceNAO for possible image-source matches, with similarity scores and source references. |
| **Notebook** | Save returned records or your own observations, add context and an evidence status, and export findings as JSON. |
| **Source catalog** | Browse 1,171 framework entries; filter the 1,040 with upstream free-access metadata, inspect integration limits, and search indexed pages. |
| **Source policy** | Review the providers used, the research boundaries, and what is stored locally. |
| **Updates** | Check stable GitHub releases, download with progress, verify the file, and install with a restart. |

### Search coverage

| Input | Integrated results | Optional browser searches |
| --- | --- | --- |
| Domain | Certificate Transparency records from crt.sh; Internet Archive snapshot metadata | Google, Bing, ICANN registration lookup, indexed pages |
| Public IP | ARIN RDAP network-allocation records; provider redirects are restricted to the reviewed registry hosts | Google, Bing, RIPEstat |
| Topic / organization | Wikipedia and Open Library catalog results | Google, Bing, DuckDuckGo, Wikipedia, Google Scholar, PubMed, Open Library, Google Patents |
| Username | Optional Brave web-index snippets; no account-existence checks | Google, Bing, and Google queries scoped to GitHub, Reddit, Instagram, or TikTok |
| Email | Optional Brave web-index snippets; no mailbox or account validation | Google and Bing |
| Instagram / TikTok / VSCO | Optional Brave snippets; explicitly enabled cases can additionally use Osintgram for Instagram public data | Google, Bing, DuckDuckGo platform searches |
| Person | Wikipedia, GDELT recent news, optional Brave web-index snippets | Google, Bing, DuckDuckGo |
| Phone | Offline numbering metadata and optional Brave indexed mentions; no owner verification | Google, Bing, DuckDuckGo |
| Steam | Brave index snippets; opt-in Valve profile/library/recent-game data and optional CBL provider records | Google, Bing, DuckDuckGo |
| Image | SauceNAO visual matches after upload consent | Returned source addresses are displayed as references |

Providers can return incomplete data, errors, or no results. A match is a lead to evaluate, not proof of identity or ownership.

## From a few identifiers to a sourced report

Use **Cases & reports** to supply names, usernames, Instagram/TikTok/VSCO profiles, emails, phones, domains, public IPs, reference URLs, notes and selected notebook findings together. Vidocq searches supported indexes, tracks failures and gaps, deduplicates exact records and produces a report with source citations. Names use Wikipedia and GDELT’s recent news index; phone analysis is offline. An enabled **Search connection** retrieves Brave web-index snippets for names, usernames, Instagram/TikTok/VSCO profiles, emails and phone numbers; without it, email/username/phone web searches remain prepared links. The app cannot establish identity or promise everything on the internet.

[Case workflow, phone limits and report exports →](docs/CASES.md)

## If you get zero results

Open **Search connection** and run **Check public sources**. Source errors, no matches and missing search connections are shown separately. Auto detect recognizes multi-word names. Wikipedia and news indexes do not cover most people. For general indexed mentions, enter your own Brave Search API key and enable it, then rerun the research or create a new report snapshot. Keys stay in memory for the session; optional `VIDOCQ_BRAVE_API_KEY` configuration is managed by you. Index searches request snippets and never follow original result URLs. Direct Steam/Osintgram APIs are separate, explicitly enabled connectors.

Brave is optional and is not unlimited free search. Its current plan provides $5 monthly credits, requires a payment card at signup, and charges for usage beyond credits. Review [current pricing and signup conditions](https://api-dashboard.search.brave.com/documentation/resources/help-feedback) before enabling. Vidocq limits requests to 100 per app session; this is not a billing guarantee. No Brave account or key is included.

## Social profiles and Windows icon

In **Research**, choose Instagram, TikTok or VSCO and enter a handle, or paste a full profile URL with Auto detect. In **Cases & reports**, each platform has a separate field. Up to five handles per platform count toward the existing fifteen-identifier total. VSCO profile links ending in `/gallery` are supported. Post/video/short links are rejected; supply the full profile address instead. The app keeps platform identity and canonical supplied references in report snapshots and all exports. Older cases continue to load.

With Brave enabled, the app searches `site:instagram.com`, `site:tiktok.com` or `site:vsco.co` and returns index snippets and source references. Without a key, it offers prepared index queries and reports that no online search ran. Supplied profiles and returned mentions are unverified; the app does not infer that handles across platforms belong to one person. Default index mode does not resolve profiles or fetch their pages. Explicitly permitted Steam/Osintgram connectors can retrieve API data; see the automatic investigation guide. No remote thumbnails or media are loaded.

The portable executable includes a new navy/gold Vidocq magnifier icon in Windows sizes from 16–256 pixels, with a stable taskbar app identity. A standalone `Vidocq.ico` is also attached to releases. The Windows gate verifies the exact generated icon frames inside the executable.

## Framework coverage

The Source catalog includes the full OSINT Framework snapshot at upstream revision `08720d5b594cb7513d7ec81f8e70c400375a85fc`. Its default view includes 784 free, 249 freemium, and 7 mixed free/freemium entries. Thirty paid entries and 101 entries without pricing metadata are separated. Pricing and status labels come from upstream and can be outdated.

**Catalog coverage is not automatic integration.** Reviewed adapters return data inside Vidocq. The other free-access entries can be searched with Google’s `site:` index search; Vidocq never substitutes a subject into their original URLs, runs local tools, submits scans, or performs account checks. Source actions send the research term only to Google. This preserves the restriction against contacting a target directly. See [source coverage](docs/SOURCES.md) for the audit and limitations.

## Get started

1. Open the [latest release](https://github.com/allen1versonfr/vidocq/releases/latest) and download **Vidocq.exe** under **Assets**. The source-code ZIP is for development.
2. Put the executable in a writable folder, such as `Documents\Vidocq`, and run it. The release includes its Python runtime; you do not need to install Python.
3. In **Research**, choose an input type or use Auto detect, enter a query, and select **Research**.
4. Save useful records to **Notebook**, add your context, and export a copy when needed.

**Requirements:** Windows 10/11 x64 and an internet connection for online searches and updates. The native window uses Microsoft Edge WebView2 Runtime; Vidocq can fall back to your default browser. Releases are currently unsigned.

Text research does not require API keys. Image search requires your own SauceNAO API key and explicit upload consent. See the [user guide](docs/USER_GUIDE.md) for the full workflow.

## Updates that stay inside the app

Vidocq checks for newer stable releases when it starts. In **Updates**, choose **Download update**, then **Install and restart**. Downloads are checked against GitHub’s SHA-256 digest and expected size before the executable is replaced. A previous executable is retained for recovery; notebooks stay in their existing data folder.

> **First upgrade:** the original 2.2.1 executable has no updater. Replace it with the latest Vidocq.exe once. Subsequent supported releases can update inside the app.
>
> **Private repository:** this repository currently requires authenticated access. Enter a fine-grained GitHub token with **Contents: read** permission on `allen1versonfr/vidocq` in the Updates tab. Vidocq keeps it in memory for that session. Public repositories do not need a token.

[Update setup, token handling, and recovery →](docs/UPDATES.md)

## Your notebook stays on your computer

By default, findings live at:

```text
%LOCALAPPDATA%\Vidocq\workspace.sqlite3
```

No cloud notebook sync or analytics are built in. The database is **not encrypted**. Providers receive the queries sent to them, and GitHub receives update requests. SauceNAO receives a metadata-stripped image only after your confirmation. [Read the data and privacy notes](docs/PRIVACY.md).

## Build and contribute

The app uses Python, a loopback HTTP backend, an HTML/CSS/JavaScript interface, pywebview, and SQLite. Windows releases are packaged as one executable with PyInstaller.

```powershell
git clone https://github.com/allen1versonfr/vidocq.git
cd vidocq
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py --browser
```

Repository access is required while the project is private. See [development and release instructions](docs/DEVELOPMENT.md) for tests, source layout, and Windows builds. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## Need help?

- [First steps, image search, notebook exports, and troubleshooting](docs/USER_GUIDE.md)
- [Private-repository update setup and rollback](docs/UPDATES.md)
- [Bug reports and feature requests](https://github.com/allen1versonfr/vidocq/issues/new/choose)
- [Changes in each documented version](CHANGELOG.md)

When reporting a problem, include the app version, Windows version, and steps to reproduce it. Remove tokens, API keys, personal queries, and sensitive findings from screenshots and logs.

## Credits

Inspired by [OSINT Framework](https://osintframework.com/). Vidocq uses a smaller set of reviewed adapters; it does not execute the full framework directory. The earlier directory review is preserved in [source-review.json](source-review.json). Built with Python, pywebview, Pillow, SQLite, and PyInstaller; their respective licenses apply to those components.
