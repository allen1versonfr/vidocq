# Guided operator login and continued research (2.17)

The Windows release now includes instagrapi 3.2.2 in Osintgram's isolated companion. It is an alternative to the optional HikerAPI backend. **This is an Instagram session login, not OAuth.** Use an account you own and control; no subject password is required. The official professional-account OAuth API is a different service and is not used here.

## Connect your account

1. Open Search connection → Instagram operator session → Sign in / reconnect my account.
2. Enter your operator username/password and approve the login and encrypted session retention. Instagram can send login/security notices to that account.
3. If requested, enter its 2FA code. Codes and passwords are cleared from the UI and are not persisted by Vidocq. A pending login expires after five minutes; Cancel stops its owned companion.
4. On success, Vidocq saves only approved session settings with Windows DPAPI for the current Windows user. No plaintext session file or password is written. The encrypted session survives executable updates, stays outside case reports/workspace backups, and is included in named local cleanup.

The saved session loads without performing a network login at startup. Local readiness is not proof that Instagram still accepts it. An expired/challenged session requires an explicit reconnect. Target lookups block login/relogin methods and allow only the backend's public-profile information/feed read endpoints; there is no silent password login, challenge solving, recovery, messaging, following, contact syncing or posting. The normal post-login feed flow is disabled. Complete any required account challenge directly in Instagram, then reconnect yourself.

Forget operator session stops the local service and removes the saved session locally; it does not revoke every Instagram session remotely. Other saved search-provider keys and an existing HikerAPI key are preserved. **Forget saved Osintgram credentials** removes both Instagram/provider credentials but preserves separately saved search keys.

The managed adapter retains its existing public-profile privacy checks and finite operation budgets. It does not retrieve private posts, even when the operator could access them. About this account is unsupported by instagrapi and reports that limitation; it remains available through the optional HikerAPI path. Provider/platform restrictions and operation failures remain visible gaps.

## Broader search without depending on one index

Search connection now offers Serper and SerpApi Google-result adapters in addition to free Mwmbl and optional Brave. Supply your own key, select a session request cap (1–100), and optionally save the new provider's key with Windows encryption. Review the provider's current free allowance, quotas and charges. Vidocq does not purchase credits or silently switch providers. Setup sends no subject searches; case execution still requires approval.

Keys never appear in status/report URLs or exported evidence. Serper sends its key to its fixed HTTPS API in a header. SerpApi's required request key is omitted from report/source URLs and error messages. Redirects are refused, system proxies are disabled for these two adapters, responses are bounded, repeated queries are cached briefly, and rate/quota failures are not converted into empty results. Saved keys/preferences survive executable updates and are included in scoped cleanup. These adapters retrieve index snippets, not original result pages.

## Six research improvements

1. **Search coverage:** optional major-index adapters with explicit key/quota controls, rather than treating Mwmbl's empty index as exhaustive coverage.
2. **Public bios and links:** save reviewed public profile text, displayed names, explicitly observed platform IDs and bio links. A separate approval can try one public metadata page using pinned public HTTPS transport and robots rules. Private destinations, action URLs, query-bearing direct URLs, redirects and challenge bypass are refused. Whole-page links are distinguished from explicit bio links.
3. **Conditional variations:** an opted-in empty-result stage combines only supplied names, handles, separate locations and approved spellings, including separate first/last tokens. It adds at most six variations within the existing overall case budget. Errors/rate restrictions do not trigger a substitute claim of absence.
4. **Guided browser continuation:** show next searches/evidence needs, open a chosen search in the normal browser, import reviewed captures/bios, and approve a new report. The new snapshot identifies its preceding report, gets a fresh approved budget, and preserves previous reports. Browser permissions and review are still user-controlled.
5. **Useful AI review:** optional source-quoted comparisons require two different known citations with verbatim quotes; next actions are selected from a fixed list. Unsupported citations/identifiers are rejected. Generic ownership cautions do not count as substantive synthesis. Draft counts do not prove new facts or investigation accuracy; semantic correctness remains an analyst task.
6. **Checker evaluation:** both an independently verified positive and negative public control, dated within thirty days, must pass to clear mismatch quarantine. Record recent control history, response fingerprints, checker version/fingerprint and available diagnostics. Access errors stay unavailable coverage, not absence. A passing pair validates those fixtures, not every account.

Public profile graphs propose links between references and matching **platform-scoped** stable IDs. They retain citations and never automatically merge people or confirm account ownership. A shared ID on two different platforms is not a match.

## Remaining manual steps and validation limits

You supply operator credentials/2FA or a provider key in the app, approve browser activation when asked, review evidence and allow each case's source activity. No live operator credentials or paid search keys are included. Development tests use synthetic accounts/sessions; a successful local setup/restoration does not certify a real account login, provider credit or discovery accuracy. Public requests may be logged by platforms. Private benchmark data is not shipped.
