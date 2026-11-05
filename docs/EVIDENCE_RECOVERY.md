# Deeper retrieval and evidence recovery in 2.20.0

These changes target missed public-account references and explain remaining misses. They do not guarantee any discovery percentage. Private test data and answer keys are excluded from the repository.

## Case controls

New cases created in the interface select 20 Brave results per search. Existing cases retain their settings; zero means use the saved connection depth. Other providers keep their existing limits. A case-specific choice does not change the saved connection, and depth-specific caches stay separate.

Additional Brave excerpts are optional. When selected, the request asks for extra snippets and retains up to five distinct additional passages per result, within response/report limits. The [official Brave documentation](https://api-dashboard.search.brave.com/api-reference/web/search/get) describes this parameter. No original page is fetched by index search. Unsupported plans/provider errors remain visible; there is no silent retry or paid fallback.

Optional indexed-link following accepts only explicit account URLs in a snippet from a supplied-identifier or analyst-reviewed profile. It does not guess handles from names. Index snippets are not verified live bios, and all resulting links remain unverified. Total search, followup, depth, deadline and provider request caps still apply.

## Recovering evidence

- Cited account links become separate review-lead records with parent citations, even when an approved followup has no results or the followup budget is zero. They are labeled as links, not verified live accounts. Generated link captions and supplied historical assertions cannot be cited as independent AI source evidence. Rejected/self links are excluded; retained linked profiles are capped.
- Model excerpts use an exact contiguous window near supplied identifiers, with character offsets in phase metadata. Useful material late in a long snippet is no longer necessarily cut off by the initial 1,500-character slice. Quotations remain validated against that source window.
- Public-profile capture handles punctuation around bio URLs. It prioritizes explicit bio links and structured Person.sameAs links when the Person URL matches the approved profile. Unrelated people/organization nodes are ignored. General page anchors remain separately labeled. Direct requests still require approval and respect robots/access restrictions.
- Historical aliases can be added with a small form. Supplied evidence and successor URLs enter the bounded query plan. Same-platform successor edges retain supplied dates/evidence and are explicitly analyst assertions, not proof of current ownership or continuity. No alias is guessed or imported from an answer key.
- Alias/successor account URLs and account URLs in starting notes are treated as supplied inputs. They cannot earn withheld-discovery credit when scoring a key that incorrectly labels them withheld.
- Review plans distinguish scoped and unscoped searches, prioritize unattempted queries, and expose index options. Comparison output identifies changed supplied evidence as a different condition.

## Read-only miss diagnosis

After a report finishes, expand **Diagnose a finished private benchmark** and choose a local JSON answer key. The key is used only for diagnosis; it is never put in the case or sent to providers. The report stays unchanged. A minimal key is:

```json
{"accounts":[{"id":"A1","role":"withheld","platform":"Instagram","canonical_url":"https://www.instagram.com/exampleprofile/"}]}
```

The diagnostic distinguishes an exact reference already returned, a link-only review lead, an analyst rejection, an original adapter reference missing from persisted records, an explicit link not materialized, and an unresolved miss. Unsupported profile shapes can still be compared as exact URLs without gaining ownership/recall eligibility.

The command-line tool can also inspect already-saved controls:

```powershell
python scripts/diagnose_benchmark.py --report LOCAL_REPORT.json --key LOCAL_KEY.json --seal LOCAL_SEAL.json --controls LOCAL_CONTROLS --output LOCAL_DIAGNOSIS.json
```

Controls use ACCOUNT_ID-index.json files. The optional seal contains the report file's sha256. A mismatch stops processing. Inputs are not overwritten. Different answer-targeted control queries cannot prove a blind pipeline loss. A later same-query control result beyond the original result cutoff is labeled as post-test deeper evidence, never as an original blind discovery. Missing from returned rows does not prove absence from the index.

New reports retain bounded original adapter reference/rank/citation traces for this analysis. Older reports may lack these traces, leaving some misses unresolved. No provider request runs during diagnosis and no score is increased.

## Validation and limits

Synthetic regressions cover case-local depth/snippet settings, cache separation, exact excerpt windows, opt-in link following, zero-followup retention, historical evidence queries, input-versus-discovery roles, structured bio links, scoped review history, sealed-file diagnostics, post-test control separation and key-contamination checks. DOM fixtures cover the case controls and alias form. Packaged API checks verify the diagnostic leaves reports unchanged and makes no provider calls.

Real local Qwen checks use synthetic evidence, including a supplied identifier late in a long record. Valid excerpts and task outputs are not proof of semantic accuracy. Link-only matches, index-returned matches, unresolved ownership and changed supplied evidence remain separate. No fresh paid/private-person benchmark was run for this release, and no higher score is claimed.
