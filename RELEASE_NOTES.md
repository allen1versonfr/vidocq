# Vidocq 2.10.0 - Additional investigation sources

- Have I Been Pwned: attributed public breach metadata for supplied emails, using your subscription key. No passwords or raw leaks.
- theHarvester: passive P0 domain discovery through your local HarvestView API, with selected sources, bounded runs and partial results.
- Maigret: selected-site username checks through an authenticated local companion. Download Maigret-Bridge.zip and install its separate pinned dependency.

All three feed case reports with coverage gaps and unverified leads. Session configuration and per-case permission are required. Existing cases keep them off. Matching handles and breach records do not establish identity or account ownership.

Setup: docs/ADDITIONAL_COLLECTORS.md. 164 automated tests cover connector contracts and existing functionality. External services require separate installation. Functional tests do not measure investigation accuracy.
