---
phase: 4
phase_name: Feed Job Design And First Conversion Plan
status: executed_with_external_evidence_gate
completed: 2026-06-19
plans:
  - 04-PLAN.md
requirements:
  - FEED-01
  - FEED-02
  - FEED-03
  - FEED-04
  - FEED-05
---

# Phase 4 Summary: Feed Job Design And First Conversion Plan

## Result

Phase 4 specified feed-level Spring Batch job designs and selected `kakaoDaumFeedJob` as the first vertical slice after G1 and repo creation approval.

## Created

- `04-NAVER.md` - Naver book, Naver shopping, blocked Naver ranking design
- `04-GOOGLE.md` - Google full/today TSV design and partition/schedule-slot decisions
- `04-KAKAO-DAUM.md` - Kakao/Daum six XML output design and retention job
- `04-FIRST-SLICE.md` - first vertical slice decision

## Key Decisions Locked

- Use stable jobs per integration with `mode=FULL|TODAY`.
- Use identifying `scheduleSlot` or `windowKey` when same-day today runs repeat.
- Use `kakaoDaumFeedJob` as the first vertical slice.
- Keep `naverRankingFeedJob` blocked until row 15 G1 evidence.
- Keep Google `groupId` as a partition key in `StepExecutionContext`.
- Keep feed-specific formats in `ContractOutputSpec`.

## Not Done By Design

- No repo was created.
- No Kotlin production code was implemented.
- No DB/SP/SQL Agent/prod access occurred.
- No golden outputs were collected.
- No shadow run or cutover was executed.

## Next

Phase 5 can only be fully meaningful after G1 and repo approval. The next practical decision is whether to approve read-only G1 evidence collection and repo creation for `partner-integration-batch`.
