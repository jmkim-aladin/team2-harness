# Phase 45 Summary - Legacy SQL Statement Risk Classification

## Result

`partner-integration-batch` now classifies every legacy SQL plan item by statement risk in local commit `8cf5dd7`.

## Changes

- Added `LegacySqlStatementKind`.
- Added `statementKind` to each `LegacySqlCallPlanItem`.
- Added SELECT, mutation, and unknown counts to the report and package summaries.
- Updated messages so SELECT SQL and mutation SQL have different review requirements.
- Regenerated `docs/legacy-sql/sample-report.json`.
- Updated README and `docs/migration-ledger.md`.

## Current Sample

- SQL candidates: 46
- Stored procedure candidates: 34
- Unresolved SQL candidates: 12
- SELECT SQL candidates: 3
- Mutation SQL candidates: 6
- Unknown SQL candidates: 3

## Remaining Blocker

The plan remains `BLOCKED_UNRESOLVED_SQL` until G1 read-only SP definition, side-effect, idempotency, and golden-output evidence is available.
