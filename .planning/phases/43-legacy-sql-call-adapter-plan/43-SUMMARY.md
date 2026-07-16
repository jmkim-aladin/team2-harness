# Phase 43 Summary - Legacy SQL Call Adapter Plan

## Result

`partner-integration-batch` now generates a local legacy SQL call adapter plan from the DTSX migration spec in local commit `789cb43`. The report records SQL/SP candidates behind `LegacyDbAdapter` and leaves unresolved direct SQL as manual adapter review.

## Verification

- Focused legacy tests passed: 3 tests.
- Actual runner wrote 46 SQL candidates, 34 stored procedure candidates, and 12 unresolved SQL candidates.
- Full `./gradlew test --rerun-tasks` passed: 127 tests, 0 failures, 0 errors, 0 skipped.

## Changes

- Added `LegacySqlCallPlanReport` model.
- Added `LegacySqlCallPlanGenerator`.
- Added `LegacySqlCallPlanCommandLineRunner`.
- Added `docs/legacy-sql/sample-report.json`.
- Updated README, migration ledger, and GSD ledger.

## Current Sample

- SQL candidates: 46
- Stored procedure candidates: 34
- Unresolved SQL candidates: 12
- Conclusion: `BLOCKED_UNRESOLVED_SQL`

## Remaining Blocker

Real SP definitions and side effects still require approved G1 read-only evidence.
