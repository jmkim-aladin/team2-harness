# Phase 45 Verification - Legacy SQL Statement Risk Classification

## Commands

```bash
./gradlew test --tests 'kr.co.aladin.partner.integration.batch.legacy.*'
```

```bash
./gradlew bootRun --args='--partner.integration.legacy-sql-plan.enabled=true --partner.integration.legacy-sql-plan.spec=docs/dtsx-spec/priority-13-17-migration-spec.json --partner.integration.legacy-sql-plan.output=docs/legacy-sql/sample-report.json --partner.integration.legacy-sql-plan.report-id=legacy-sql-sample --partner.integration.legacy-sql-plan.created-at=2026-06-19T00:00:00Z'
```

```bash
./gradlew test --rerun-tasks
```

## Actual

- RED compile failure confirmed before implementation: missing `statementKind`, missing `LegacySqlStatementKind`, and missing kind count fields.
- Focused legacy tests passed: 4 tests.
- Actual runner wrote `docs/legacy-sql/sample-report.json`.
- Sample report records `sqlCandidateCount=46`, `procedureCallCount=34`, `unresolvedSqlCount=12`, `selectSqlCount=3`, `mutationSqlCount=6`, `unknownSqlCount=3`.
- `./gradlew test --rerun-tasks` passed: 130 tests, 0 failures, 0 errors, 0 skipped.
- b2b local commit: `8cf5dd7`.
- No external endpoint, DB, SQL Agent, DTSX execution, partner-facing publish, YouTrack, KB, push, or PR action was touched.
