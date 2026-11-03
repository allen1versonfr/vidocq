# Validation for Vidocq 2.3.0

45 automated tests pass locally, including 17 updater tests covering stable-version ordering, exact asset selection, missing/invalid digests, redirect allowlisting, credential stripping on CDN redirects, private repository errors, partial/corrupt/oversized downloads, successful replacement, rollback after failed startup, and notebook preservation.

Frontend JavaScript passes node --check. The Windows workflow must additionally pass frozen application import/UI/database smoke checks, actual executable replacement/restart, and failed-launch rollback before publishing. BUILD_INFO.json records these gates for the released artifact. The interactive native window is not manually exercised by these automated checks.
