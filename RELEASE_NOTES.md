# Vidocq 2.9.0 — Give it your clues, get a sourced report

Cases & reports now supports bounded automatic investigation: enter names, phones, accounts and other identifiers, then let connected sources retrieve records, identify eligible new clues and follow them within your chosen limits.

Reports include an executive summary, stronger leads with multiple supplied identifiers, uncertain/unlinked results, explicit profile-name differences, source failures, unanswered questions and a cited follow-up trail. Cancel a run and export its preserved partial results.

New optional connections:

- Steam: native public API profile/vanity resolution, disclosed game library/recent playtime, optional game AppID filter and attributed Community Ban List records. Requires your Steam Web API key.
- Osintgram: bridge to your separately installed/configured Datalux/Osintgram 2.x service for public-profile information, account-about data and up to five recent posts' captions/hashtags. Its backend credentials and any charges remain in Osintgram.

Connections must be enabled for the session and explicitly allowed in the case. Default direct connectors are off. Broad name/phone/handle coverage usually requires your Brave API key. The readiness notice makes missing connections clear before a run. Results remain leads; the app does not infer account ownership from a matching name or guarantee a complete profile.

Existing cases/reports remain compatible. Source boundaries and setup are documented in docs/AUTOMATIC_INVESTIGATIONS.md. Tests use synthetic data; live authenticated Steam/CBL/HikerAPI/Instagram calls were not tested without user credentials.
