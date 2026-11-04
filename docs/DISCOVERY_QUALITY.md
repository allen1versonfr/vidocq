# Discovery and evidence improvements in 2.19.0

This update targets useful account discovery and source relevance. Software tests do not establish a higher real-world discovery score. Private benchmarks and identifiers are excluded from the repository.

## Changes

1. People-directory results stay in raw evidence but cannot become AI citations, expansion anchors or relevant candidate counts.
2. Property listings receive the same exclusion from account discovery evidence.
3. Model context requires a complete supplied name, supplied identifier, supplied account reference or analyst-confirmed evidence. First-name-only and unrelated results are filtered. Approved spelling variants and first/last forms remain supported.
4. Name-only quotation drafts carry a possible-namesake label. Matching a name does not establish identity.
5. Identical long excerpts syndicated across different URLs cannot consume multiple model context slots. Richer copies of the same canonical source get priority.
6. Equivalent context queries are skipped before execution, including AI suggestions that repeat a supplied-name search. Reports record the skipped queries rather than crediting extra tasks.
7. Adaptive searches can use up to four additional platform-specific index queries by default, within the approved total budget. The setting permits zero to eight. These run after baseline tasks even when generic searches returned nonempty results. Supplied profile platforms are skipped, and terms come only from supplied identifiers/names.
8. Explicit author paths in indexed TikTok videos and X posts produce separate unverified review leads with parent citations. The original content URL stays intact. This does not confirm ownership, and it never guesses an Instagram post's author from an opaque post ID.
9. LinkedIn public /in/ profiles and Hudl numeric /profile/ references are recognized separately from companies, posts or teams. Followups use an exact reference search, not a fabricated shared username or numeric-handle scan.
10. AI phases report filtered citations/reasons, selected resource counts and duplicate-context counts. Report exports include query efficiency and platform search details.
11. Search request sharing and caches use the same normalized effective query, with platform scope kept distinct.
12. Brave can optionally retain the first 20 results instead of 10. The default stays 10; request caps remain in force. The requested depth, original ranks and cache separation survive diagnostics and saved settings.

## Controls and limits

Adaptive platform searches query the configured index; they do not directly fetch social profiles or log into accounts. They remain inside the case's search, request and deadline limits. Disable adaptive searches or set the platform limit to zero to avoid the additional queries.

The deeper Brave option is in Search connection. Brave's [official API reference](https://api-dashboard.search.brave.com/api-reference/web/search/get) documents a maximum count of 20 and notes that fewer results may be returned. No pagination or automatic credit purchase is added. Other providers retain their existing response limits.

Directory/property exclusions affect model context, candidate summaries and automatic expansion. Raw source records remain available for review. These source categories are unsuitable for automatically attributing accounts; a directory listing is not independent ownership evidence.

Quoted text can still be irrelevant or concern a namesake. Unknown candidates need independent review. Blocked/unsupported checkers remain source gaps; non-detection is not proof that an account is absent.

## Validation

Synthetic regressions exercise source exclusions, unlinked-profile abstention, supplied-profile relevance, name-only ambiguity, resource/excerpt deduplication, platform query limits, duplicate-task avoidance, content-author provenance, profile URL shapes and optional deep-result ranks/cache separation. DOM fixtures verify the new settings. A real local Qwen run on synthetic evidence selected a valid verbatim excerpt and abstained from unrelated selections. These checks verify behavior, not investigative accuracy. Windows release checks repeat the full suite and packaged update/recovery checks before publishing.
