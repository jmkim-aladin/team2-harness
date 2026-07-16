# Phase 43 Verification - Legacy SQL Call Adapter Plan

## Commands

```bash
./gradlew test --tests 'kr.co.aladin.partner.integration.batch.legacy.*'
```

```bash
./gradlew bootRun --args='--partner.integration.legacy-sql-plan.enabled=true --partner.integration.legacy-sql-plan.spec=docs/dtsx-spec/priority-13-17-migration-spec.json --partner.integration.legacy-sql-plan.output=docs/legacy-sql/sample-report.json'
```

## Expected

- focused legacy tests pass
- actual runner writes the sample report
- report records SQL candidate count, procedure call count, unresolved SQL count, and package breakdown
- no external endpoint, DB, SQL Agent, DTSX execution, or partner-facing publish is touched

## Actual

- RED generator test failed on missing `LegacySqlCallPlanGenerator`.
- RED runner test failed on missing `LegacySqlCallPlanCommandLineRunner`.
- Focused legacy tests passed: 3 tests.
- Actual runner wrote `docs/legacy-sql/sample-report.json`.
- Sample report records `sqlCandidateCount=46`, `procedureCallCount=34`, `unresolvedSqlCount=12`, `conclusion=BLOCKED_UNRESOLVED_SQL`.
- `./gradlew test --rerun-tasks` passed: 127 tests, 0 failures, 0 errors, 0 skipped.
- b2b local commit: `789cb43`.
- No external endpoint, DB, SQL Agent, DTSX execution, or partner-facing publish was touched.
