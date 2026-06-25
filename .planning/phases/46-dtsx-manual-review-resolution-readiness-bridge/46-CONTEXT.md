# Phase 46 Context - DTSX Manual Review Resolution Readiness Bridge

## Background

Phase 27 intentionally made `DTSX_SPEC_COVERAGE` block readiness when DTSX steps needed manual review. Phases 28-38 then decomposed those manual-review steps into 17 work items, implemented local Kotlin/Spring Batch building blocks and Tasklet adapters, and added manual implementation plus manual step plan readiness gates.

That leaves one integration gap: `DTSX_SPEC_COVERAGE` still treats `BLOCKED_MANUAL_REVIEW` as a permanent blocker even when the separate manual implementation and manual step plan reports prove the manual work has been mapped. The bridge should not weaken missing/warning/empty-spec checks, and it must not make the current sample ready while row 15 remains G1-blocked.

## Current Evidence

- `DTSX_SPEC_COVERAGE`: priority 13-17 spec still has 17 manual-review steps.
- `DTSX_MANUAL_IMPLEMENTATION`: current report is `PASSED`, 17/17 implemented.
- `DTSX_MANUAL_STEP_PLAN`: current report is `BLOCKED_G1`, 16 planned and 1 `NAVER_RANKING` work item blocked until G1 evidence.
- Readiness sample has 10 gates and remains `BLOCKED`.

## Scope

- Adjust readiness evaluation only.
- Do not change DTSX parser, manual worklist generation, manual operation services, or G1 policy.
- Preserve G1/golden/legacy SQL blockers.

## Non-Goals

- No claim of SSIS equivalence.
- No G1 evidence collection.
- No DB/SP/SQL Agent/prod access.
- No delivery modernization.
