# Phase 37 Context: DTSX Manual Operation Step Plan

## Goal

17개 DTSX manual-review work item을 Spring Batch job/manual step/adapter method 계획으로 고정한다. Phase 33-36은 adapter coverage와 readiness gate를 만들었지만, 실제 feed job flow에서 어떤 manual step으로 배치될지에 대한 원장은 아직 없다.

## Scope

- worklist -> job/step/adapter binding report model/evaluator/runner 추가
- `NAVER_RANKING` 관련 work item은 G1 전 `BLOCKED_G1`로 표시
- README, migration ledger, GSD 원장 갱신

## Non-Goals

- 실제 운영 DTSX, SQL Agent, SP, golden output 조회를 하지 않는다.
- partner-facing FTP/SMB/API/HTTP/prod publish를 하지 않는다.
- 아직 실제 feed job flow에 모든 manual tasklet을 삽입했다고 주장하지 않는다.
