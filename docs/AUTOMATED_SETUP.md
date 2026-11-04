# Automatic setup and evidence-driven investigations

Vidocq 2.16 includes a **Set up investigation tools** panel. Approve the tools you want once; Vidocq remembers those choices and starts their local services on subsequent launches. Setup never searches a subject. Each case still has its own source permissions, direct-request approval and finite budgets.

| Tool | Automatic part | What you supply |
| --- | --- | --- |
| Mwmbl | Enable anonymous free API search and restore that preference | Nothing; its small index and quotas still limit coverage |
| Maigret | Start/check the included authenticated companion and restart it when needed | Select sites and allow checks in a case |
| theHarvester | Start the included pinned passive-only companion, check available sources | A supplied domain and case permission; crt.sh/Cert Spotter need no provider key |
| Photon | Start the included pinned crawler and enforce public HTTPS/robots/page/depth limits | Approve direct requests to a specific website |
| Local AI | Download/verify the pinned runtime/model, preserve files on updates, start on demand | Approve the approximately 2.54 GB download and enable AI-assisted investigation in the case |
| Browser helper | Register Vidocq's Windows URI handler; generate a capture bookmark for the selected case | Add/use the bookmark or install the optional extension; approve opening Vidocq when the browser asks |
| Osintgram | Start the included pinned public-profile service, prompt for missing credentials, retain the encrypted key | **Your HikerAPI key**; provider quota/charges may apply to approved lookups |

There is no automatic registration or purchase of provider accounts. Steam and HIBP still need their respective keys. Other theHarvester providers can require credentials and are not made free by this setup. Existing manually configured services remain supported. The automatic installer currently targets the portable Windows x64 release; source developers build the companion assets with Python 3.14 and `python scripts/build_collectors.py` before starting the Python 3.12 app.

## Osintgram credentials

The current upstream service supports HikerAPI or a separately prepared Instagram session. The included managed path uses **HikerAPI**, avoiding an automated Instagram password login. On first launch, or when the enabled service lacks a usable saved key, Vidocq prompts for your provider key in a password field. You can skip, change it, or forget it later.

The key is encrypted with Windows DPAPI for the current Windows user, stored in the dedicated app data folder, and passed to the owned companion through standard input. The app does not return the key through its APIs or add it to reports, workspace backups, command-line arguments or logs. It survives executable updates. Forget stops the service and removes the saved credential; Burn includes the named credential files. A Windows account migration may require entering the key again. No subject password, password reset, contact syncing, message or follow action is used.

Managed Osintgram allows only the selected public profile/bio/caption/hashtag commands, with a 1–5 backend-call budget and private/unknown-privacy restrictions. Startup with a key checks local service readiness, **not whether the provider accepts the key or has available credit**. Live paid lookups require your working key and explicit case approval.

## The AI now participates in a case

Enable **AI-assisted investigation** after installing/enabling the model. The approved pipeline:

1. Builds possible queries from supplied names, handles, locations, historical aliases and analyst-approved spelling variants. The model selects indexes from that finite list; it cannot invent new identifiers.
2. Executes validated novel selections through the configured search provider, within the overall search limit and the separate AI-search cap. The run records their origin and attempted count. An empty/unconfigured provider remains a coverage gap.
3. Proposes exact HTTPS links already present in cited evidence. With published-link following enabled, eligible linked profiles can enter the bounded queue with their parent citation. A different handle can be checked on its linked platform if that site was explicitly permitted for Maigret. Aggregate imported Photon inventories do not establish a page-to-page relationship and are not automatically followed.
4. Drafts a short source-based synthesis with existing citation IDs and verbatim supporting quotes. Invalid citations, invented URLs/numbers and certain ownership assertions are rejected. Validation cannot prove semantic accuracy: explanations remain **model drafts for analyst review**, and linked accounts remain unverified until an analyst records an ownership decision.

Only bounded excerpts of non-rejected records enter the local runtime. There is no cloud fallback, arbitrary browsing or unrestricted tool execution. Missing/failed AI leaves deterministic searches running and records the gap. The manual query/excerpt drafting workbench is still available.

## Coverage and browser review

A finished queue can still produce **Coverage incomplete**. Reports separately expose unavailable/missing sources, unsearched tasks and AI failures. Processing completion is not proof of exhaustive discovery or a negative finding.

Major-index search buttons open prepared queries in your ordinary browser. Select public text, use the generated case-specific bookmark or the optional extension's **Send to Vidocq**, approve the native-app prompt if shown, then review/import the pending capture inside Vidocq. Captures are held in memory for ten minutes, up to ten at a time; receiving a capture never silently adds it to a case. JSON export/import remains available. Browser installation and permissions cannot be silently bypassed. The native helper uses the normal default app-data location; custom `VIDOCQ_DATA` developer sessions can use JSON import instead.

## Dated checker controls

Use an independently confirmed public profile as a dated checker control. A mismatch quarantines that site checker; an unavailable retry does not clear an earlier mismatch. A passing dated control can re-enable it. Controls expire after thirty days and do not validate every account or imply ownership. Unsupported, blocked, absent and unavailable outcomes remain separate.

## Packaging and limits

The separately executed companions use pinned upstream commits and verified executable hashes. theHarvester is GPL-2.0-only; Osintgram and Photon are GPL-3.0. Their licenses are available through setup and the corresponding source/build instructions are distributed as **Collectors-Source.zip** with each release. The main app does not install browser binaries or silently download AI weights. Owned child processes stop with Vidocq. Photon uses bounded pinned public HTTPS requests, robots rules, a single approved host, at most five attempted pages and depth two; it blocks action paths and does not retain raw crawler exports.

These changes improve setup and evidence handling. They do not make Mwmbl a major search index, bypass platform restrictions, guarantee that searches never trigger platform telemetry, or establish investigation accuracy without independent evaluation.
