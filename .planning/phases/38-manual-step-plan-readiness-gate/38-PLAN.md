# Phase 38 Plan - Manual Step Plan Readiness Gate

## Goal

Make `DTSX_MANUAL_STEP_PLAN` a required migration readiness gate so manual operation step wiring evidence is required before readiness can pass.

## Tasks

1. Add failing tests for the new readiness gate.
   - Missing step plan report keeps readiness `BLOCKED`.
   - `PASSED` step plan contributes a passed gate.
   - `BLOCKED_G1` step plan contributes a blocked gate with planned/blocked/unsupported counts.
   - `FAILED_EMPTY_WORKLIST` contributes a failed gate.
   - Command-line runner reads `--partner.integration.readiness.dtsx-manual-step-plan-report`.

2. Implement the minimal readiness change.
   - Add `DTSX_MANUAL_STEP_PLAN` to `MigrationReadinessGate`.
   - Add `dtsxManualStepPlan` input to `MigrationReadinessEvaluator.evaluate`.
   - Map `DtsxManualOperationStepPlanConclusion` to readiness statuses.
   - Wire the command-line runner option.

3. Update documentation and samples.
   - README readiness command includes the new report option.
   - `docs/readiness/sample-report.json` shows 8 gates with manual step plan blocked by G1.
   - `docs/migration-ledger.md` lists manual step plan as a required readiness input.

4. Verify.
   - Confirm RED compile failure before implementation.
   - Run focused readiness tests.
   - Run actual readiness bootRun smoke with all sample inputs.
   - Run full Gradle test suite.
   - Commit b2b repo with a small local commit.
