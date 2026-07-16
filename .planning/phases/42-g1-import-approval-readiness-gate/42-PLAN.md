# Phase 42 Plan - G1 Import Approval Readiness Gate

## Goal

Make migration readiness require an approved G1 import report in addition to a passed G1 validation report.

## Steps

1. Add RED tests for missing G1 import report when G1 validation has passed.
2. Add RED tests for a G1 import report whose decision is not `APPROVED_READ_ONLY_EXPORT`.
3. Add `G1_IMPORT_APPROVAL` readiness gate.
4. Add `g1Import` input to `MigrationReadinessEvaluator`.
5. Add `--partner.integration.readiness.g1-import-report` to the command runner.
6. Add `docs/g1-evidence/sample-import-report.json`.
7. Regenerate `docs/readiness/sample-report.json`.
8. Update README, migration ledger, and GSD planning ledger.
9. Run focused tests, actual readiness runner, and full tests.

## Acceptance

- G1 validation pass without import approval report stays blocked.
- Pending approval decision stays blocked.
- Approved import report is required for readiness pass.
- Sample readiness report records 9 gates, 4 passed, 5 blocked.
