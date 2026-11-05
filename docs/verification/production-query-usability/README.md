# 운영 조회 사용성 Q1 설계 검증 근거

- 공통 작업 ID: `TASK-20261104-4560e95349bc`.
- 대상: `/Users/jm/Documents/workspace/team2/docs/production-query-request-flow.md`와 `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/projects/production-query-usability/plan.md`의 Q1.
- baseline: HEAD `ff0ca564cea38e1814677a235102d4512ac4cee9`, 브랜치 `team2/harness-hook-context-audit`. 코드·환경·재사용 검사 근거는 [q1-baseline.json](./q1-baseline.json).
- 현재 단계: 설계 검증. 신규 admission/job/fetch/export 동작은 아직 구현·실행·배포되지 않았다. 운영 접속·중단 해제·실행기 재시작·자격증명 조회를 수행하지 않았다.

## 스코프 판정

기존 원장·gateway·transport·watchdog·recovery를 재사용한다. Q1은 문서·검토 증거만 변경하며 새 서비스·queue·DB driver는 만들지 않는다. Q2·Q3·Q3b는 같은 control/gateway에 의존하므로 순차 구현한다. 각 구현 슬라이스에서 8파일 초과 또는 두 개 이상의 새 서비스가 필요하면 다시 분할한다. 구현·격리 검증·운영 반영을 구별하며 운영 반영은 Q4의 별도 승인 gate다.

사용자 판정은 다음과 같다.

- 모든 실제 실행 SQL·조건부 SQL과 대상·시간·결과 한도를 승인 전에 표시한다.
- 메모리 기본 보관과 동일 사용자/중단 세대에서의 결과 이어받기를 선택했다. SQL 재실행은 허용하지 않는다.
- 필요한 CSV 파일 저장·개발 참고를 허용했다. 기본 보관의 예외로, 검토된 구조화 결과와 비공개 로컬 저장에 한정한다.
- 새 v2 메모리 결과 기본 32MiB를 선택했다. 현재 v1 무제한 정책과 구별해 준비·검토·실행 계약에 명시한다.

내장 기능 검토: SQLite `BEGIN IMMEDIATE`·표준 Python sqlite3·CSV writer·기존 Unix socket·macOS launchd를 재사용한다. SQLite transaction이 marker 파일·별도 audit DB·네트워크 전송까지 원자적으로 묶지는 않으므로 staged admitting과 durable intent를 설계했다. 출처와 설치별 미확인 범위는 설계 문서 §8에 연결했다.

## 섹션 검토

| 섹션 | 확인한 변경 필요 지점 | 증거와 판정 |
|---|---|---|
| 아키텍처 | 차단 중 검토 불가, client 연결과 작업 수명이 결합됨 | `/Users/jm/Documents/workspace/team2/tools/db_query_control.py:106`의 `if state["halted"]` 거부; `/Users/jm/Documents/workspace/team2/tools/db_prod_gateway.py:948`의 `if disconnected and disconnected()` → stop. 사용자 목표에 맞춰 v2 preview와 gateway 소유 작업으로 분리한다. |
| 코드 품질 | 기존 SQL bytes·보안 경계를 재사용하고 표시 누락만 별도 변경 | `/Users/jm/Documents/workspace/team2/tools/db_prod_transport.py:760`의 `sql.encode("utf-8")`를 유지. `/Users/jm/Documents/workspace/team2/tools/db_prod_client.py:64`의 종료 확인 SQL 표시 생략 문구는 Q2에서 바꾼다. |
| 테스트 | 기존 one-use·stop·fencing 기반은 있으나 새 전이는 GAP | `/Users/jm/Documents/workspace/team2/tools/db_prod_gateway.py:1044`의 `item["offset"] = end`와 `:1046`의 결과 삭제는 현재 응답 재전송을 막는다. 사용자 선택에 맞춘 fetch/ack 새 회귀·E2E가 필요하다. |
| 성능 | 현재 결과 byte 상한이 없음 | `/Users/jm/Documents/workspace/team2/tools/db_prod_gateway.py:82`의 `RESOURCE_MAX_BYTES = None`. v2 32MiB 기본값을 사용자 판정으로 확정했다. RSS 전체 한도나 성능 향상으로 확대 해석하지 않는다. |

실패 모드·테스트 다이어그램은 설계 문서 §7에 있다. 새 경로별 SQL/연결 0회·정확히 1회, 중단 이후 거부, 상태/캐시/파일 결과를 구별한 assert를 Q2/Q3/Q3b에 배치했다. 미래 테스트 항목을 현재 TESTED로 표시하지 않는다.

## 반증 검토

위험 강도 계약 두 개(승인·중단 보존 / 재접속·CSV 결과 안전성)를 fresh-context 내부 reviewer에게 전달했다. 작성자의 대화·리뷰 결론을 전달하지 않고 산출물과 계약·관련 코드만 제공했다. 외부 벤더로 코드·정책을 전송하지 않았다. Q1 자체는 하루 이내 문서 작업이므로 별도 outside-voice 세션은 생략하고 필수 반증 검토를 수행했다.

- [1차 반증](./q1-doubt-round-1.md): export spec 승인 연결 P1, CSV+manifest 공개 P2, ack tombstone P2와 admitting 복구 미확인. 모두 산출물의 구체 계약으로 반영했다.
- [2차 반증](./q1-doubt-round-2.md): 실제 action 집합 승인 결속과 원 결과 export/새 조회 lineage를 보강했다.
- [3차 반증과 메인 종료 판정](./q1-doubt-round-3.md): 외부 halt/내부 phase 분리와 사전 stream ID/사후 content completion을 보강했다. 메인이 반례 해소를 추적했으며 4차 fresh-context 반증은 하지 않았다. 설계 판정은 실제 신규 구현·장애 복구 검증을 뜻하지 않는다.
- [q1-test-map.json](./q1-test-map.json): 실재하는 기존 테스트 심볼 10개와 아직 실행되지 않은 새 seam별 테스트 의무를 구분했다.

## 다음 구현과 검증

- T1(P1) — client/봉투 — SQL 전체 표시와 불변 승인 봉투를 구현한다. 고정 사용자/준비/observer fixture와 실제 transport bytes를 대조한다.
- T2(P1) — Store/Supervisor/recovery — 승인 소비·소유 슬롯·admitting·marker 실패·새 중단·admission ticket 1회 claim·복구를 구현한다. 다중 프로세스·각 crash 위치를 검증한다.
- T3(P1) — gateway/CLI — v2 단일 승인 흐름을 연결한다. ready/resume/emergency와 상태 변경 거부를 격리 E2E로 확인한다.
- T4(P1) — gateway/job 상태 — client 연결 분리·상태 조회·메모리 캐시·immutable fetch/ack tombstone을 구현한다. 요청/청크/ack 응답 유실과 실제 gateway 손실을 구별한다.
- T5(P1) — CSV 구조화 경계 — 고정 frame·NULL/문자열/정밀도·buffer/파일 한도·server-owned export spec·directory 공개/복구를 검증한 뒤 선택 저장을 연결한다.
- 검증 명령: 기존 `python3 -m unittest discover -s tools/tests -p 'test_db*.py'`, 전체 `python3 -m unittest discover -s tests`, `python3 -m unittest discover -s tools/tests`, 하네스 lint. 새 테스트는 위 seam의 기존 test 파일에 추가하고 Q4에서 실제 transport 격리 검증과 사용자 흐름을 함께 확인한다.

범위 밖: 운영 SQL 실행·LaunchAgent 설치·실제 runtime 전환·운영 schema/SP 변경·새 DB driver·원본의 공개 Git/자동 동기화 위키 저장. 배포 전에 별도 승인을 받으며 Q1 완료로 배포까지 완료됐다고 표현하지 않는다.

운영 전제: 실제 DB 권한·DMV/구조화 SQL 지원, 설치본의 directory no-replace 공개 및 streaming frame 구현은 각 구현 단계에서 입증한다. 아직 구현되지 않은 새 경로의 테스트 GAP은 구현·출시 gate로 남긴다. 해결되지 않은 정책 선택과 단순 미래 검증 의무를 구별한다.

## Q1 종료 검사

[q1-checks.json](./q1-checks.json)에 최종 설계 SHA-256, production source 6개 불변 확인, 로컬 원장 probe의 실제 관측, 반증 라운드와 한계, 하네스 lint·위키 lint·지정 산출물 시크릿 패턴 검사 통과를 기록했다. 기존 full verification은 source baseline이 동일함을 확인해 재사용했고 새 코드가 통과한 것으로 세지 않았다. Q1 완료는 설계·검토 범위이며 다음은 Q2 구현이다.
