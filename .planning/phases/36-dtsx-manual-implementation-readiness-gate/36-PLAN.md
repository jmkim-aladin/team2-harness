# Phase 36 Plan: DTSX Manual Implementation Readiness Gate

## Steps

1. Read readiness evaluator/runner tests and manual implementation coverage model.
2. Add RED tests requiring a new `DTSX_MANUAL_IMPLEMENTATION` readiness gate.
3. Implement the evaluator gate and command-line report option.
4. Update b2b README/sample report/migration ledger.
5. Run focused tests, readiness smoke, and full tests.
6. Commit b2b changes locally and report status to triage/global.

## Success Criteria

- Missing manual implementation report keeps readiness `BLOCKED`.
- `PASSED` manual implementation report records `implemented=17/17, unsupported=0`.
- Unsupported resolutions keep readiness `BLOCKED`.
- Empty worklist failure is treated as readiness failure.
- Readiness smoke reports 7 gates: 4 passed and 3 blocked.
