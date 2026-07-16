# Phase 44 Summary - Legacy SQL Adapter Plan Readiness Gate

## Result

`partner-integration-batch` now requires a legacy SQL adapter plan report in migration readiness. The local b2b commit is `fae3145`.

## Changes

- Added `MigrationReadinessGate.LEGACY_SQL_ADAPTER_PLAN`.
- Added `LegacySqlCallPlanConclusion.PASSED`.
- Added readiness evaluator handling for missing, blocked, failed, and passed legacy SQL plans.
- Added runner option `--partner.integration.readiness.legacy-sql-plan-report`.
- Regenerated `docs/readiness/sample-report.json` with 10 gates.
- Regenerated `docs/g1-evidence/approval-packet.json` with 6 blocking gates.
- Updated README and `docs/migration-ledger.md`.

## Current Sample

- Readiness conclusion: `BLOCKED`
- Required gates: 10
- Passed gates: 4
- Blocked gates: 6
- Legacy SQL gate: `BLOCKED_UNRESOLVED_SQL`
- SQL candidates: 46
- Stored procedure candidates: 34
- Unresolved SQL candidates: 12

## Remaining Blocker

The legacy SQL plan cannot pass until unresolved SQL candidates and stored procedure side effects are reviewed with approved G1 read-only evidence.
