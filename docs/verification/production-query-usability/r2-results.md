# R2 launchd 수명 등록 — 검증 결과

- 작업 ID: `TASK-20261105-c5044da1af18`
- 기준: main `d044476` → branch `team2/production-query-launchd`
- 운영 반영: 2026-11-05 사용자 승인("등록 진행"). 운영 DB 접속·SQL 실행·자격증명 조회 없음.

## 수행한 운영 변경

| 순서 | 동작 | 관찰 |
|---|---|---|
| 1 | 운영판 `status` 재확인 | `halted=false`, `active=null`, `phase=idle`, epoch 78 |
| 2 | 수동 실행기(PID 4837, bundle `320090125c39…`)에 SIGTERM | 5초 안에 종료, 남은 gateway 프로세스 0 |
| 3 | `db_prod_runtime.py launchagent` 출력 plist(`plutil -lint` OK)를 `~/Library/LaunchAgents/kr.co.aladin.team2-db.plist`(600)로 설치, `launchctl bootstrap gui/501` | exit 0, `state = running`, pid 10386, `runs = 1`; status `halted=true`, `reason=service_started_requires_operator_resume`, idle, epoch 80 |
| 4 | `launchctl kickstart -k gui/501/kr.co.aladin.team2-db` (계획 재시작) | `runs = 2`, pid 11221, `last exit code = 0`; gateway 프로세스 1개; halted·idle, epoch 82 |
| 5 | 운영판 `preview --target cool-prod --database WebCatalog --timeout 30` (`SELECT 1 AS connection_ok;`) | exit 0, `selected_actions=["execute_once","resume_current_stop"]`, stop snapshot epoch 82·halted. 승인·`run` 하지 않음 → 요청 만료 대상 |

plist 핵심: `ProgramArguments=[Python 3.9 framework, -I, <root>/current/db_prod_gateway.py, serve]`, `RunAtLoad`, `KeepAlive`, `ThrottleInterval=10`, PATH `/usr/bin:/bin:/opt/homebrew/bin`(transport는 DB 클라이언트 절대 경로 사용), stdout/stderr `/dev/null`.

## 완료 기준과 판정

| 기준 | 결과 |
|---|---|
| launchd가 운영판 번들 실행기를 띄운다 | 충족 (3) |
| 재기동 시 halted·무접속으로 뜬다 | 충족 (3·4, SIGTERM 종료 코드 0 → KeepAlive 재기동) |
| `preview`가 재개 포함 검토를 만든다 | 충족 (5) |
| 등록·해제·교체·롤백 절차 문서화 | 충족 — `tools/README.md` §운영판 launchd 수명, 설계 문서 §5 운영판과 배포 |

## 확인 못 함

- 실제 로그아웃·재부팅 후 `RunAtLoad` 기동은 이 세션에서 관찰하지 않았다. 다음 로그인 뒤 `launchctl print`와 운영판 `status`로 확인한다.
- launchd 컨텍스트에서 키체인 helper가 비밀번호를 읽는지는 첫 승인 조회(`run`)에서 확인된다. 이번 검증은 접속하지 않았다.
- 번들 교체(`bootout → activate → bootstrap`) 절차는 문서화만 했고 실행하지 않았다(Q3b 반영 때 첫 실행).
