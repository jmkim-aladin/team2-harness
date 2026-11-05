# Q4 통합 장애·경쟁 조건·사용 흐름 검증

- 작업 ID: `TASK-20261105-c5044da1af18`, 2026-11-05 macOS(arm64) 로컬 검증.
- 기준: main `8b2f62b` → branch `team2/production-query-q4`. 검증 대상 운영판 지문 `bc58fd34…`(운영 실행기와 같은 runtime fingerprint).
- 계약: [설계 §2·§4·§5·§7](../../production-query-request-flow.md), 계획 §Q4.
- 운영 실행기·원장·socket·키체인·운영 DB를 쓰지 않았다. 운영 socket inode가 실행 전후 같음을 harness가 검사했다.

## 무엇을 새로 검증했나

Q2·Q3는 seam별로 합성 backend·프로세스 내 socket을 썼다. Q4는 다음을 **모두 실제 프로세스**로 잇는다.

`db_prod_runtime.build_bundle`로 만든 immutable bundle → `-I`로 띄운 실제 gateway `serve` 프로세스 → 매 명령 별도 프로세스의 실제 client CLI(`preview`·`run`·`stop`·`job-status`·`result`·`recovery-*`) → host `/opt/homebrew/bin/sqlcmd` → 자체 소유 loopback Docker SQL Server 2022 CU24.

자식 프로세스 안에서 바꾼 seam은 셋뿐이다.

| seam | 이유 |
|---|---|
| `HOME`=임시 디렉터리 | 상태 원장·`stop.d`·lock·worker journal이 운영 파일과 섞이지 않게. gateway·client 모두 경로가 임시 HOME 아래인지 assert |
| `SOCKET`=임시 socket | 운영 `/tmp/team2-db-<uid>/query.sock`을 unlink·점유하지 않게 |
| Keychain vault → fixture `sa`, sqlcmd stdin tee | 운영 자격증명 없이 접속하고, 실제 전송 bytes를 검토 표시와 대조하기 위해 |

harness: `tools/tests/integration/sqlserver/e2e_flow.py`. 원본 보고서: [q4-e2e.json](./q4-e2e.json), 로그: [q4-e2e.log](./q4-e2e.log).

## 시나리오 결과 — 20/20 통과

| 시나리오 | 관찰 |
|---|---|
| 기동 | halted, `service_started_requires_operator_resume`, sqlcmd 프로세스 0 |
| 재개 후 조회 | `preview` actions `[execute_once, resume_current_stop]`, 접속 0 → 승인 1회 `run` → 결과 반환·halted 해제, 사용자 SQL 전송 1회 |
| 정상 조회 | ready에서 actions `[execute_once]`만, 결과 1회 |
| 중복 접수 | 소비된 승인으로 같은 ID 재`run` → 추가 sqlcmd 프로세스 0 |
| 변경된 SQL | B의 approval digest로 A 실행 → client와 gateway(`approve_submit` 직접 호출) 모두 거부, 전송 0 |
| 검토 후 새 중단 | 검토 뒤 `stop` → 기존 승인 거부, 전송 0 |
| 응답 유실 | 전송 확인 직후 client 프로세스 그룹 SIGKILL → 작업 completed, 새 client `result`로 같은 ID 결과 수신, 전송 1회, 서버 세션 0 |
| 사용자 취소 | 실행 중 `stop` → 0.27초 안에 failed, 결과 없음, 서버 세션 0, `operator_cancel_completed`로 자동 ready |
| 시간 초과 | timeout 3초 → 3.37초에 failed, 서버 세션 0, halted 유지, 다음 검토에 `resume_current_stop` 포함 |
| worker 손실 | 실행 중 sqlcmd SIGKILL → failed, 재실행 0, halted 유지, 서버 세션 0(관찰 확인으로 active 해제) |
| 실행기 손실 | 실행 중 gateway SIGKILL → watchdog가 고아 서버 세션 종료, 재기동은 halted·active 유지·job `recovery_required`, 새 `preview` 거부 → `recovery-review`로 observer SQL 전문 표시·승인 1회·실행 → idle·halted |
| 복구 뒤 | 승인 1회로 재개+조회 정상, 이전 SQL 재전송 0 |
| 전문 대조 | 모든 sqlcmd stdin bytes가 검토 화면(`preview`·`recovery-review`)에 JSON 표기로 표시된 사용자·준비·관찰 SQL의 연결로만 구성 |

## 발견

1. **`run` 종료 코드가 작업 실패를 반영하지 않는다.** 사용자 취소·시간 초과·worker 손실로 `job_state=failed`여도 `run`은 exit 0이다(실행기 손실 때만 1). 결과 JSON의 `ok`가 RPC 성공을 뜻하기 때문이다. JSON의 `job_state`·`outcome`은 정확하지만 종료 코드만 보는 호출자는 실패를 성공으로 오판할 수 있다. 안전 계약(재실행·차단·결과 공개)은 영향 없음. 수정은 client 코드 변경과 bundle 재build·교체가 필요하므로 이번 milestone에서 하지 않았다.
2. **Q3 runtime 테스트의 격리 빈틈.** `tools/tests/test_db_prod_runtime.py`의 실제 gateway 기동 검사는 `STATE`·`SOCKET`만 바꾸고 HOME은 그대로 둬서 `LATCH`가 운영 `stop.d`를 가리킨다. `LatchStore`는 이 경로를 읽기만 하므로 운영 상태를 바꾸지는 않지만, 운영에 중단 파일이 있으면 테스트 결과가 달라진다. Q4 harness는 HOME 자체를 임시로 둔다.
3. 첫 실행의 실패 4건은 harness 판정 오류였다(`run`이 검토 전문을 다시 출력하므로 출력 전체에서 결과 문자열을 찾으면 안 됨, 종료 코드로 실패 판정). 조건별 근거를 남기도록 고친 뒤 재실행했다. 제품 결함 증거로 세지 않는다.

## 회귀 검사

| 검사 | 결과 |
|---|---|
| root `python3 -m unittest discover -s tests -p 'test_*.py'` | 476건 OK |
| tools `python3 -m unittest discover -s tests -p 'test_*.py'` (`tools/`) | 328건 OK, 1건 skip(TTY 없는 키체인 helper 검사) |
| 승인·중단 회귀 `discover -s tests -p 'test_db_*.py'` (`tools/`) | 216건 OK, 1건 skip |
| Q4 E2E `python3 tools/tests/integration/sqlserver/e2e_flow.py --report …` | 20/20 PASS, 컨테이너 삭제 확인, 보고서에 fixture 비밀번호 없음 |

## 배포·롤백과 미확인 운영 전제

배포·교체·롤백 절차는 `tools/README.md` §운영판 launchd 수명(R2)을 따른다. Q4는 운영 코드를 바꾸지 않았으므로 bundle 재build·교체가 필요 없다.

이번 검증으로 확인하지 못한 운영 전제:

- 실제 운영 SQL Server의 버전·권한(VIEW SERVER STATE 범위)·네트워크 지연에서의 종료 관찰 시간. fixture는 `sa`·loopback·AMD64 에뮬레이션이다.
- launchd 컨텍스트의 키체인 읽기와 실제 로그인 재기동(R2 미확인 항목과 같음).
- 부하: 운영 DB 부하·대용량(32MiB 근접) 결과 전달 시간은 측정하지 않았다.
- 운영 실행기를 대상으로 한 실제 취소·장애 주입은 하지 않았다. 필요하면 시점마다 별도 승인을 받는다.
