# Phase 27 Plan: DTSX Spec Coverage Gate

## Objective

Prevent readiness from passing while the priority 13-17 DTSX migration spec still has unresolved manual-review steps.

## Tasks

1. Add `DtsxSpecCoverageReport` model.
2. Add evaluator and CLI runner for `docs/dtsx-spec/priority-13-17-migration-spec.json`.
3. Add coverage gate to `MigrationReadinessEvaluator`.
4. Update README, migration ledger, and sample reports.
5. Verify:
   - dtsxspec/readiness tests
   - actual dtsx coverage `bootRun`
   - actual readiness `bootRun`
   - full Gradle tests
