---
phase: 1
phase_name: DTSX Evidence Lock
status: executed_with_external_evidence_gate
completed: 2026-06-19
plans:
  - 01-PLAN.md
requirements:
  - INV-01
  - INV-02
  - INV-03
  - INV-04
---

# Phase 1 Summary: DTSX Evidence Lock

## Result

Phase 1 produced the local evidence ledger for Excel 업무 번호 13-17 and locked the migration assumptions needed before Kotlin implementation starts.

The implementation baseline is Kotlin + Spring Boot 4.1.x + Spring Batch 6.0.x with Kotlin 2.2+. DTSX is treated as the current batch specification, not as Kotlin source code to auto-convert.

## Completed

- Created `.planning/LEDGER.md` as the SSIS equivalence ledger.
- Mapped Excel physical rows 15-19 to 업무 번호 13-17.
- Listed local DTSX candidates for Naver book, Naver shopping, Naver ranking, Google, and Kakao/Daum.
- Classified the visible DTSX operations into staging, extract, generate, publish, cleanup/retention, and validation categories.
- Marked row 15 as blocked until active SQL Agent package evidence confirms exact scope.
- Locked required production evidence as approval-required: SQL Agent, operational DTSX, SP definitions, golden outputs, publish/readback access, runtime account/network/secret evidence.
- Updated architecture language so the target model is partner integration artifact, not file-only. File/HTTP/FTP/API delivery remains a v1 compatibility bridge.

## Requirement Status

| Requirement | Status | Notes |
|---|---|---|
| INV-01 | Complete | Local Excel row to DTSX candidate inventory exists in `.planning/LEDGER.md`. |
| INV-02 | Partial | Candidate packages are listed. Full Control Flow/Data Flow XML extraction needs active package confirmation before it can be canonical. |
| INV-03 | Complete | Operation classification table exists in `.planning/LEDGER.md`. |
| INV-04 | Blocked | SQL Agent `msdb` read-only confirmation requires explicit approval. |

## Not Done By Design

- No Kotlin production code was generated in Phase 1.
- No DB, SP, SQL Agent, production endpoint, YouTrack, KB, git commit, push, PR, or prod changes were made.
- No SSIS equivalence claim was made because golden outputs and active job evidence are still missing.

## Next Gate

Decision G1 is required before implementation evidence can be treated as canonical:

- approve read-only SQL Agent `msdb` job/step/package/schedule check
- approve operational DTSX deployment readback
- approve SP definition read-only capture
- approve golden output collection
- approve publish/readback path access check
- approve runtime account/private network/secret inventory

Phase 2 architecture planning can proceed without DB/prod access, but implementation should not start until G1 evidence is resolved.
