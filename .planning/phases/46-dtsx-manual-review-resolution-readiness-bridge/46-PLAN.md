# Phase 46 Plan - DTSX Manual Review Resolution Readiness Bridge

## Objective

Allow `DTSX_SPEC_COVERAGE` manual-review blockers to be considered resolved only when the manual implementation coverage report and manual operation step plan report both pass.

## Tasks

1. Add failing readiness tests for resolved and unresolved DTSX manual-review coverage.
2. Pass manual implementation and manual step plan inputs into the DTSX spec coverage readiness gate.
3. Mark `BLOCKED_MANUAL_REVIEW` coverage as passed only when both manual reports are `PASSED`.
4. Keep missing, warning, empty spec, blocked manual implementation, and blocked manual step plan cases blocked or failed.
5. Regenerate `docs/readiness/sample-report.json` and `docs/g1-evidence/approval-packet.json`.
6. Update README, migration ledger, and GSD ledger.
7. Run focused readiness tests and full test suite.

## Verification

- `./gradlew test --tests 'kr.co.aladin.partner.integration.batch.readiness.MigrationReadinessEvaluatorTest'`
- actual readiness runner
- actual G1 approval packet runner
- `./gradlew test --tests 'kr.co.aladin.partner.integration.batch.readiness.*'`
- `./gradlew test --rerun-tasks`
