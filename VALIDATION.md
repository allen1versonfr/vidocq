# Validation for Vidocq 2.4.0

53 automated tests pass locally. The additional catalog checks cover snapshot completeness, pricing totals, unique entry IDs, filters/pagination, source/query validation, index-only actions, local-tool restrictions, new search-link allowlisting, and Open Library metadata parsing. Existing research, image, migration, updater corruption and rollback checks remain in the suite.

JavaScript passes `node --check`. The Windows workflow additionally tests the actual frozen executable, catalog packaging, replacement/restart and failed-launch rollback before publishing. BUILD_INFO.json records the gate results for the released artifact. Interactive native-window use and individual availability/pricing of all upstream tools are not manually verified by these tests.
