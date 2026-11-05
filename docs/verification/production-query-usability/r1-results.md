# R1 운영판 CLI·스킬·정책 문구 v2 반영 — 검증 결과

- 작업 ID: `TASK-20261105-c5044da1af18`
- 기준: main `7464b2c`(Q2·Q3 머지) → branch `team2/production-query-v2-docs`
- 범위: 문서·스킬 문구와 가드 회귀 케이스. 실행기·원장·설정·운영 DB·launchd는 변경하지 않았다.

## 완료 기준과 판정

| 기준 | 결과 | 근거 |
|---|---|---|
| `/ad:db-stop`의 `stop`·`status`·`emergency-stop` CLI가 운영판 `current/db_prod_client.py`를 가리킨다 | 충족 | `.claude/commands/ad/db-stop.md`. 운영판 경로가 없거나 시작 실패 시에만 저장소 CLI로 `stop` 재시도 |
| Codex 미러 `$ad-db-stop`이 같은 경로·재개 흐름을 안내한다 | 충족 | `.codex/skills/ad-db-stop/SKILL.md` (command 문서를 SoT로 참조) |
| 기본 조회 흐름이 `preview → 사용자 명시 승인 → run`이다 | 충족 | `tools/README.md` db_prod_client 절, `policies/production-db-access-policy.md`, `.claude/commands/ad/work-prep.md` |
| v1 `prepare/approve/execute`·독립 `resume`이 기본 경로로 남지 않는다 | 충족 | README는 v1을 별도 표로 분리하고 "기본 조회·재개 안내에 쓰지 않음" 명시. 정책·긴급 중단 문서는 재개를 "v2 재개 포함 승인(기본) 또는 독립 `resume`(사용자 요청 시 대체)"로 정의 |
| 개통 상태 문구가 정책과 어긋나지 않는다 | 충족 | work-prep·자격증명 정책의 "미개통" 문구를 정책 참조로 교체 |
| Paperclip 비대화 실행 가드가 운영판 경로를 막는다 | 충족 | `tools/tests/test_agent_run_guard.py` DENY에 번들 경로 3형태(절대·`$HOME` 따옴표·백슬래시 공백) 추가, 기존 `_DB_NAME` 파일명 매칭으로 차단됨 |

잔여 검색: 저장소에서 `team2/tools/db_prod_client.py` 경로는 `db-stop.md`의 대체 경로 1곳과 가드 테스트 fixture만 남는다. `현재 미개통` 문구 없음.

## 실행한 검사

| 검사 | 명령 | 결과 |
|---|---|---|
| root 회귀 | `python3 -m unittest discover -s tests -p 'test_*.py'` (repo 루트) | 476건 OK |
| tools 회귀 | `python3 -m unittest discover -s tests -p 'test_*.py'` (`tools/`) | 328건 OK, 1건 skip(TTY 없는 runner의 키체인 helper TTY 거부 검사) |
| 가드 단위 | `python3 -m unittest tools.tests.test_agent_run_guard` | 21건 OK |
| 운영판 상태 조회(읽기 전용, SQL 없음) | `python3 "$HOME/Library/Application Support/team2-db-runtime/current/db_prod_client.py" status` | `ok=true`, `halted=false`, `active=null`, `phase=idle`, `api_versions=[1,2]`, epoch 78 |

tools 모수 329→328: main에 함께 머지된 `37e4e88`(사람 세션 push·PR 훅 확인 제거)이 `test_agent_run_guard.py`의 테스트 메서드를 22→21로 줄였다. 이번 변경은 기존 메서드의 DENY 목록만 늘렸다.

## 확인 못 함

- 실제 `stop`·`emergency-stop` 실행은 하지 않았다 — 운영 실행기의 승인을 무효화하고 차단을 남기기 때문이다. 명령 존재는 운영판 `stop --help`로만 확인했다.
- 운영판이 없는 상태에서 저장소 CLI `stop` 대체 경로가 같은 중단 파일을 쓰는지는 현재 운영판의 `db_prod_client`·`db_prod_gateway`·`db_query_control`·`db_prod_watchdog`·`db_prod_transport` 5개 파일이 이 branch의 `tools/`와 바이트 일치(`cmp`)한다는 사실에 기댄다. 이후 원본이 바뀌면 다시 확인한다.
