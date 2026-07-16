---
phase: 4
phase_name: Feed Job Design And First Conversion Plan
status: ready_for_planning
created: 2026-06-19
requirements:
  - FEED-01
  - FEED-02
  - FEED-03
  - FEED-04
  - FEED-05
---

# Phase 4: Feed Job Design And First Conversion Plan - Context

## Phase Boundary

Phase 4 defines feed-specific Spring Batch job designs and the first vertical slice plan. It does not create the repo, implement Kotlin code, access DB/prod systems, collect golden files, or run shadow/cutover.

## Locked Decisions

- Use one stable `Job` per integration. `mode=FULL|TODAY` distinguishes full/today where applicable.
- Add `scheduleSlot` or `windowKey` when same-day today jobs can run multiple times.
- Keep `runPurpose=PRODUCTION|SHADOW|RETRANSFER` as identifying semantics.
- Feed-specific format rules live in `ContractOutputSpec`.
- `kakaoDaumFeedJob` is the first vertical slice candidate because local evidence shows one package, six XML outputs, and separate retention.
- `naverRankingFeedJob` remains blocked until G1 confirms row 15 exact scope.
- Google split uses `groupId` as `StepExecutionContext` partition key, not top-level `JobParameter`.

## Canonical References

- `.planning/LEDGER.md`
- `.planning/REQUIREMENTS.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-ARCHITECTURE.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-BATCH-MAPPING.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-OPERATIONS.md`
- `.planning/phases/03-validation-harness-specification/03-VALIDATION-HARNESS.md`
- `.planning/phases/03-validation-harness-specification/03-SHADOW-RUN.md`
- `/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_NaverDBFile`
- `/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_GoogleShop_DBFile`
- `/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_DaumDBFile_Make`

## Required Phase 4 Output

- Naver book/shopping/ranking design.
- Google shopping design.
- Kakao/Daum design and retention design.
- First vertical slice decision.
- full/today mode and schedule slot decision.
- G1 blockers per feed.
