# Reviewable investigations and scoped burn

## Profiles and query planning

Twitch, GitHub, GitLab, Reddit user and YouTube handle URLs supply username clues. Existing Instagram/TikTok/VSCO/Steam handling remains. Shared platform hosts and navigation pages are not expanded into subject-owned domain research. Recognizing a supplied identifier does not establish ownership.

Enter location alternatives separated by semicolons. Each name/location pair is searched separately; commas inside a city/state remain intact. An employer gets its own context query. Existing search/depth budgets still apply. The search log records attempted and budget-skipped tasks.

## Browser-assisted evidence

Open a prepared query in your default Chrome, Firefox or other browser. In Cases, paste a reviewed excerpt, original source URL, title and optional query into Capture reviewed browser evidence. Confirm and save it. The next report includes it as user-supplied evidence with a timestamp and citation. Vidocq does not fetch that page, solve challenges or claim the excerpt was automatically discovered. Raw source text uses the existing immutable Notebook capture/history system.

## Account decisions

For each case, enter an account URL, choose Rejected, Confirmed or Unverified, and provide a reason. Decisions retain change history and survive case edits and workspace backups. Confirmed means an analyst assertion, not automatic independent verification. Rejected references remain rejected when encountered again. Maigret skips a selected site's matching known-rejected handle when the saved profile URL identifies it. Rejection on one site does not suppress the handle everywhere.

Decisions affect new reports; existing captured reports stay unchanged. Reports separate raw records, relevant candidates, rejected/unlinked results and analyst-confirmed accounts. No-relevant-leads is a valid completed outcome. Neither job completion nor an unrelated archive record establishes successful discovery.

Maigret retains each selected site's outcome: candidate, absent, invalid handle, unsupported checker, blocked, timeout, cancelled, error or unknown. Absence is a check result, not proof an account cannot exist. Blocks are recorded without bypass attempts.

## Burn Vidocq

Open Updates and find Burn Vidocq. Preview first, review the exact paths, then type **BURN VIDOCQ** to execute within five minutes. Active investigations/updates must finish first. After confirmation the app disables new writes, stops its managed companion, closes and runs a hidden Windows cleanup helper.

The preview includes named workspace SQLite files (including possible journal/WAL/shared-memory sidecars), startup/update-result logs and the ownership marker. Attachments, account decisions and captured reports reside in that database. If selected in the portable Windows build, it also includes the current executable and adjacent `.previous` update backup with content hashes. Source code and Python environments are never removed.

The helper validates the dedicated data directory, ownership marker, named file scope, reparse points and executable hashes. It deletes only those listed paths after process exit. Unrelated files are preserved; directories are removed only when empty. Wrong/expired confirmation and changed scope are refused. Preview itself deletes nothing.

**Limits:** this is permanent file deletion, not guaranteed secure erasure from SSDs, filesystem journals, snapshots or backups. Exports/screenshots saved elsewhere, other executable copies, temporary updater downloads outside this workspace, browser history/download records, pinned shortcuts, OS/security logs, third-party tools/credentials and provider logs remain outside its scope. It does not modify Windows/browser history or security logs. On failure, details remain in the helper's temporary folder at the path provided by the closing message.

Development and release deletion tests use disposable fixtures/copied executables only. The user's real workspace and installed executable are not burned during development.
