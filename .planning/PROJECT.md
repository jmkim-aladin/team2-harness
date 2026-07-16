# IDC DB 이관 B2B SSIS 13-17 Spring Batch 전환

## What This Is

IDC DB 이관 과정에서 private 통신만 가능한 전제를 두고, `B2B 배치.xlsx`의 우선 대상 13-17번 SSIS/DTSX 배치를 Kotlin + Spring Boot + Spring Batch 기반 신규 배치로 전환하는 프로젝트다. DTSX를 Kotlin 코드로 1:1 자동 변환하지 않고, 현재 SSIS 패키지를 배치 명세로 역공학한 뒤 `Job/Step/Tasklet/Reader/Writer` 모델로 재설계한다.

## Core Value

기존 SSIS가 생성하던 파트너 연동 산출물을 검증 가능한 Spring Batch 실행 단위로 재현하고, 이관 중에는 기존 파일/HTTP/FTP 등 제공 계약을 깨지 않는다.

## Requirements

### Validated

- [x] 신규 로컬 repo skeleton 생성: `/Users/jm/Documents/workspace/b2b/partner-integration-batch`
- [x] Spring Boot 4.1.0 + Spring Batch 6.0.4 + Kotlin 2.2.21 기준 테스트 통과
- [x] `kakaoDaumFeedJob` local shadow smoke 실행으로 6개 XML placeholder artifact와 manifest ledger 생성 확인
- [x] Naver book, Naver shopping, Google, Kakao/Daum local skeleton smoke 실행 확인
- [x] Naver ranking은 G1 전 실행 차단 확인
- [x] 우선 대상 DTSX 후보 8개에서 package, connection manager, executable, SQL/SP 후보 inventory JSON 생성 확인
- [x] DTSX variable과 precedence constraint를 tracked inventory JSON에 포함
- [x] DTSX inventory에서 Spring Batch migration spec JSON 생성 확인
- [x] Golden comparison harness와 sample report 생성 확인
- [x] 구조 검증 + golden 비교 결합 final equivalence gate 생성 확인
- [x] Contract format validation report와 final gate 통합 확인
- [x] G1 evidence pack schema/validator와 sample report 생성 확인
- [x] Local publish/readback runner와 sample report 생성 확인
- [x] G1 evidence fill-in template generator와 sample template 생성 확인
- [x] G1 evidence directory importer와 fragment 계약 문서 생성 확인
- [x] G1 fragment template directory writer와 runner round-trip 확인
- [x] 동일 feed/businessDate local domain run lock 구현과 release 확인
- [x] rebuild/retransfer JobParameter 분리와 retransfer generation guard 확인
- [x] manifest 기반 local retransfer 구현과 원본 artifact publish attempt 기록 확인
- [x] file-only가 아닌 integration exchange contract catalog 생성 확인
- [x] exchange catalog를 migration readiness 필수 gate로 통합 확인
- [x] DTSX manual implementation coverage를 migration readiness 필수 gate로 통합 확인
- [x] DTSX manual-review work item 17건의 Spring Batch job/manual step/adapter method 계획 생성 확인
- [x] DTSX manual operation step plan을 migration readiness 필수 gate로 통합 확인
- [x] G1 read-only evidence request bundle 생성 확인
- [x] G1 approval packet 생성 확인
- [x] G1 import approval guard 생성 확인
- [x] G1 import approval readiness gate 생성 확인
- [x] Legacy SQL call adapter plan report 생성 확인
- [x] Legacy SQL adapter plan readiness gate 생성 확인
- [x] Legacy SQL statement risk classification 생성 확인
- [x] DTSX manual-review coverage blocker를 manual implementation coverage와 manual operation step plan 통과 조건에 연결
- [x] 로컬 repo DTSX 후보 7개 checksum fragment/report 생성 확인
- [x] G1 approval packet 기반 build-only approval decision 생성과 approval guard import 확인
- [x] G1 operator export source-root preflight로 template/local 후보 fragment 차단 확인
- [x] G1 operator preflight report를 migration readiness 필수 gate로 통합 확인

### Active

- [ ] DTSX 13-17 후보를 실제 운영 SQL Agent job/step/package와 연결해 active package를 확정한다.
- [ ] 각 DTSX의 Control Flow, Data Flow, SQL/SP, Script Task, 파일/API/FTP/HTTP I/O, cleanup, publish 계약을 배치 명세로 추출한다.
  - Local DTSX inventory extractor now captures package/connection/variable/executable/precedence/SQL candidates. Active package, script internals, publish/readback, and cleanup details still require G1/follow-up evidence.
- [ ] 신규 베이스는 별도 Git repo의 독립 Kotlin + Spring Boot + Spring Batch app으로 설계한다.
- [ ] 기존 SP/SQL 호출은 `LegacyDbAdapter` 경계에 캡슐화하고 batch core로 누수시키지 않는다.
- [ ] v1에서는 현재 파트너 제공 계약을 유지하거나 compatibility bridge로 보존한다.
- [ ] 기존 SSIS와 신규 batch를 같은 businessDate로 shadow run해 row count, checksum, byte-level 차이를 검증한다.
- [ ] cutover 전 rollback, 수동 재실행, 재전송, 운영 알림, manifest/audit 기준을 문서화한다.
  - Local skeleton is implemented, but true shadow run still requires SSIS golden output.

### Out of Scope

- DTSX를 Kotlin 코드로 자동 변환 - 실행 가능한 운영 코드 품질과 동등성 검증을 보장하기 어렵다.
- 이관 v1에서 `ftp.aladin.co.kr`, `www2.aladin.co.kr`, SMB/UNC/API 제공 방식을 재설계 - 사용자가 "3번은 이관 후 변경"으로 결정했다.
- 승인 없는 YouTrack, KB, git commit/push/PR, DB/SP, prod 변경 - team2 정책상 사용자/사람 승인이 필요하다.
- row 15 범위 확정 없는 구현 착수 - SQL Agent active step 확인 전까지 후보가 모호하다.

## Context

- 대상 Excel: `/Users/jm/Documents/workspace/ssis/B2B 배치.xlsx`
- 대상 번호: 13, 14, 15, 16, 17
- 신규 repo 권장 이름: `partner-integration-batch`
- 신규 repo 로컬 경로: `/Users/jm/Documents/workspace/b2b/partner-integration-batch`
- 주요 로컬 SSIS repo:
  - `/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_NaverDBFile`
  - `/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_GoogleShop_DBFile`
  - `/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_DaumDBFile_Make`
- 기존 분석 노트: `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/projects/db-idc-migration/2026-06-b2b-ssis-13-17-kotlin-batch-transition.md`
- 생성된 DTSX inventory: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/dtsx-inventory/priority-13-17-inventory.json`
- 생성된 Spring Batch migration spec: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/dtsx-spec/priority-13-17-migration-spec.json`
- 생성된 legacy SQL call adapter plan report: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/legacy-sql/sample-report.json`
- 생성된 golden comparison sample report: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/golden-comparison/sample-report.json`
- 생성된 contract format sample report: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/contract-format/sample-report.json`
- 생성된 equivalence sample report: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/equivalence/sample-equivalence-report.json`
- 생성된 G1 evidence sample pack/report: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/g1-evidence/sample-pack.json`, `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/g1-evidence/sample-report.json`
- 생성된 G1 evidence request bundle: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/g1-evidence/request-bundle.json`
- 생성된 G1 approval packet: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/g1-evidence/approval-packet.json`
- 생성된 G1 approval decision template: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/g1-evidence/approval-decision-template.json`
- 생성된 build-only G1 approval decision: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/build/g1-evidence/approval-decision-approved.json`
- 생성된 build-only G1 local DTSX candidate approval import reports: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/build/g1-evidence/local-dtsx-candidates-approved-import-report.json`, `/Users/jm/Documents/workspace/b2b/partner-integration-batch/build/g1-evidence/local-dtsx-candidates-approved-validation-report.json`
- 생성된 build-only G1 operator preflight reports: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/build/g1-evidence/fragment-template-cli-preflight-report.json`, `/Users/jm/Documents/workspace/b2b/partner-integration-batch/build/g1-evidence/local-dtsx-candidates-preflight-report.json`
- 생성된 G1 sample import report: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/g1-evidence/sample-import-report.json`
- 생성된 G1 evidence fill-in template: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/g1-evidence/template-pack.json`
- 생성된 G1 evidence import guide: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/g1-evidence/import-fragments.md`
- 생성된 build-only G1 fragment template/import reports: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/build/g1-evidence/fragment-template-report.json`, `/Users/jm/Documents/workspace/b2b/partner-integration-batch/build/g1-evidence/fragment-template-import-report.json`
- 생성된 local publish/readback sample source/report: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/publish-readback/sample-source/daily/feed.txt`, `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/publish-readback/sample-report.json`
- 생성된 build-only lock smoke manifest: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/build/partner-integration/lock-smoke/manifest`
- 생성된 build-only rebuild/retransfer smoke manifest: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/build/partner-integration/rebuild-smoke/manifest`, `/Users/jm/Documents/workspace/b2b/partner-integration-batch/build/partner-integration/retransfer-guard/manifest`
- 생성된 build-only manifest retransfer smoke manifest: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/build/partner-integration/retransfer-success/manifest`
- 생성된 exchange catalog sample report: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/exchange-catalog/sample-report.json`
- 생성된 DTSX manual operation step plan sample/runtime report: `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/dtsx-manual-step-plan/sample-report.json`, `/Users/jm/Documents/workspace/b2b/partner-integration-batch/build/dtsx-manual-step-plan/report.json`
- 참고 구현: `/Users/jm/Documents/workspace/b2b/aladin-b2b-batch`는 참고만 하고, 신규 설계는 독립 Spring Batch app을 기준으로 한다.
- GSD 전용 subagent 정의는 현재 설치되어 있지 않아 `multi_agent_v1` explorer 3개로 병렬 조사했다.

## Constraints

- **Network**: private 통신만 가능 - 기존 외부/SMB/FTP/HTTP/API 제공 경로는 v1에서 계약 유지 또는 bridge로 보존한다.
- **Tech stack**: Kotlin + Spring Boot 4.1.x + Spring Batch 6.0.x - Kotlin 기반으로 SSIS 대체에 필요한 Job/Step metadata, restart, retry, skip, chunk transaction을 활용한다.
- **Repository**: 신규 별도 repo 권장 - SSIS 이관 전용 batch 명세, manifest, validation, delivery bridge 책임을 기존 B2B batch와 섞지 않는다.
- **Legacy boundary**: 기존 SP/SQL은 `LegacyDbAdapter`로 제한 - 신규 core에 SP 이름과 side effect가 퍼지지 않게 한다.
- **Validation**: shadow run 필수 - 기존 SSIS golden output 없이 동등성 완료 판단 금지.
- **Governance**: DB/SP/prod/git/YouTrack/KB 변경은 별도 승인 - 현재 project init은 로컬 planning 문서만 생성한다.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| DTSX 1:1 자동 변환 금지 | DTSX는 운영 배치 명세로 역공학하고 Spring Batch 모델로 재구성하는 편이 검증 가능하다. | Pending |
| 신규 별도 repo 이름은 `partner-integration-batch` | 발신 feed, 수신 파일, 향후 API/연동성 배치까지 포함할 수 있고, IDC나 특정 파트너명에 묶이지 않는다. | Locked |
| 신규 별도 repo의 독립 Spring Batch app 기준 | SSIS 대체에는 Job/Step 실행 이력, 재시작, retry/skip, chunk 처리가 필요하고, 이관 전용 책임을 기존 batch와 분리해야 한다. | Pending |
| 기존 SP/SQL은 `LegacyDbAdapter`로 1차 캡슐화 | DB 이관 일정과 side effect 불확실성을 줄이면서 신규 core 오염을 막는다. | Pending |
| 제공 방식 변경은 이관 후 별도 진행 | 이관 v1의 리스크를 낮추고 파일/HTTP/FTP/API 등 기존 파트너 계약을 깨지 않는다. | Locked |
| 내부 모델은 file-only가 아니라 partner integration artifact 기준 | 받는 연동도 있고, 향후 API/비파일 산출물이 있을 수 있으므로 생성물과 전달 방식을 분리한다. | Locked |
| 여러 DTSX 간 DAG는 외부 orchestrator 후보로 분리 | Spring Batch Job 안에 SSIS 전체 Control Flow를 재현하지 않는다. | Pending |
| Spring Boot 4 안정 계열 기준 | 2026-06-19 공식 문서 기준 Spring Boot 4.1.0이 현재 4.x 안정 라인으로 표시된다. Kotlin은 Boot 4 migration guide의 2.2+ 요구를 기준으로 한다. | Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition**:
1. Requirements invalidated? Move to Out of Scope with reason.
2. Requirements validated? Move to Validated with phase reference.
3. New requirements emerged? Add to Active.
4. Decisions to log? Add to Key Decisions.
5. "What This Is" still accurate? Update if drifted.

**After each milestone**:
1. Full review of all sections.
2. Core Value check - still the right priority?
3. Audit Out of Scope - reasons still valid?
4. Update Context with current state.

---
*마지막 갱신: 2026-06-20, Phase 51 기존 SQL 주석 접두어 변경문 분류*
*현재 진행: 2026-06-20, Phase 52 기존 SQL 보고서 메시지 한글화 완료*
*현재 진행: 2026-06-20, Phase 53 준비도와 승인 패킷 메시지 한글화 완료*
