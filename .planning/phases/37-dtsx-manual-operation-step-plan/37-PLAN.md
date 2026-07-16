# Phase 37 Plan: DTSX Manual Operation Step Plan

## Steps

1. Add failing tests for worklist-to-step-plan conversion.
2. Implement `DtsxManualOperationStepPlan` report, evaluator, and command-line runner.
3. Generate a sample report and actual runtime report.
4. Update b2b README/migration ledger and GSD planning records.
5. Run focused tests, actual runner smoke, and full tests.
6. Commit b2b changes locally and report concise status to triage/global.

## Success Criteria

- Current priority worklist yields 17 items total.
- 16 items are planned into runnable feed job manual steps.
- 1 `NAVER_RANKING` item is explicitly `BLOCKED_G1`.
- Unsupported package/resolution is blocked, not passed.
- No external system or partner-facing side effect occurs.
