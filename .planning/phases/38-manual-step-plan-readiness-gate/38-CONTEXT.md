# Phase 38 Context - Manual Step Plan Readiness Gate

## Objective

`partner-integration-batch`의 migration readiness bundle이 DTSX manual operation step plan report를 필수 gate로 요구하게 만든다. Phase 37에서 생성한 job/manual step/adapter method 계획이 readiness에서 누락되면 row 15/G1 차단 상태가 숨겨질 수 있으므로, readiness가 이를 직접 드러내야 한다.

## Current State

- b2b repo latest commit before this phase: `e825f6b`
- Phase 37 runtime report: `build/dtsx-manual-step-plan/report.json`
- Phase 37 actual conclusion: `BLOCKED_G1`
- Runtime counts: work items 17, planned 16, blocked 1, unsupported 0
- Blocked item: `NAVER_RANKING`, pending G1 SQL Agent/DTSX/SP/golden evidence

## Constraints

- Do not connect to SQL Server, FTP, SMB, HTTP, APIs, or production endpoints.
- Do not claim SSIS equivalence from local placeholder artifacts.
- Do not change YouTrack, KB, push, PR, DB/SP, SQL Agent, or production state.
- Keep code changes limited to readiness model/evaluator/runner and supporting tests/docs.
