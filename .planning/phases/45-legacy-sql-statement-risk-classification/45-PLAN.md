# Phase 45 Plan - Legacy SQL Statement Risk Classification

## Objective

Classify legacy SQL candidates by statement risk so adapter review can prioritize mutation and unknown SQL before readiness can pass.

## Tasks

1. Add failing tests for SELECT and mutation statement classification.
2. Add `LegacySqlStatementKind` to the call plan item.
3. Add statement kind counts to the report and package summaries.
4. Classify stored procedures, SELECT/CTE queries, mutation SQL, and unknown snippets.
5. Regenerate `docs/legacy-sql/sample-report.json`.
6. Update README, migration ledger, and GSD ledger.
7. Run focused legacy tests and full test suite.

## Verification

- `./gradlew test --tests 'kr.co.aladin.partner.integration.batch.legacy.*'`
- actual legacy SQL plan runner
- `./gradlew test --rerun-tasks`
