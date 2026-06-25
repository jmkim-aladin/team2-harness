# Phase 44 Plan - Legacy SQL Adapter Plan Readiness Gate

## Objective

Make the legacy SQL adapter plan a first-class migration readiness gate.

## Tasks

1. Add failing readiness tests for a missing legacy SQL plan report.
2. Add failing readiness tests for `BLOCKED_UNRESOLVED_SQL`.
3. Add `LEGACY_SQL_ADAPTER_PLAN` to the readiness gate model.
4. Add `LegacySqlCallPlanConclusion.PASSED` as the only passing plan state.
5. Wire `--partner.integration.readiness.legacy-sql-plan-report` into the readiness runner.
6. Regenerate readiness and approval packet samples.
7. Update README and migration ledger.
8. Run focused readiness tests and full test suite.

## Verification

- `./gradlew test --tests 'kr.co.aladin.partner.integration.batch.readiness.*'`
- actual readiness runner with `--partner.integration.readiness.legacy-sql-plan-report=docs/legacy-sql/sample-report.json`
- actual G1 approval packet runner against the regenerated readiness report
- `./gradlew test --rerun-tasks`
