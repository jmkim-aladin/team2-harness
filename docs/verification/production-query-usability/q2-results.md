# 운영 조회 단일 승인 Q2 구현 검증

- 작업: `TASK-20261104-4560e95349bc`, 2026-11-04 macOS 로컬 검증.
- 대상: `/Users/jm/Documents/workspace/team2-worktrees/production-query-usability`, 브랜치 `team2/production-query-usability`, base/HEAD `ff0ca564cea38e1814677a235102d4512ac4cee9` 위 미커밋 후보. 최종 파일 SHA-256과 runtime fingerprint는 [q2-baseline.json](./q2-baseline.json)에 기록한다. HEAD만으로 후보를 식별하지 않는다.
- 실행 계약: [설계 §3·§4·§7](../../production-query-request-flow.md). Q1 과거 증거는 원본 그대로 보존하며 Q2 실행 검증과 구별한다.

## 된 것과 구현 경계

T1은 사용자·연결 준비·조건부 종료 확인 SQL 전문과 조건·한도·정확한 action을 모두 보여주는 불변 검토 봉투다. T2는 같은 SQLite 제어 DB에 ApprovalLedger를 조합해 승인 소비·소유 슬롯·복구 metadata를 원자적으로 남긴다. T3는 `preview` → 명시 승인 → `run`의 단일 approve_submit 경로를 연결한다. 기존 Supervisor·transport·watchdog·recovery와 v1 승인 경로를 재사용한다. 각 seam을 순차 구현했으며 새 서비스·DB 드라이버·큐는 없다.

ready는 실행만 승인하고 외부 halted/epoch를 쓰지 않는다. halted/idle은 표시한 중단 해제와 해당 SQL 한 번을 함께 승인한다. 긴급 중단 해제도 별도 action으로 표시·결속한다. 승인 뒤 새 중단·동작/SQL/설정 변경·만료는 접속 전에 거부한다. 승인 소비 이후 실패는 consumed와 소유 슬롯을 남기고 자동 재실행하지 않는다.

v2 memory 결과는 기본·최대 32MiB payload다. 프로세스 RSS 상한이나 v1 기본 제한 변경을 뜻하지 않는다. 실행 deadline은 admission 시 한 번 고정하며 준비·marker 정리·접속 시간을 포함한다. 조건부 observer는 검토된 SQL 한 번·최대 5초·1행·256바이트다.

## 검증 결과

| 검사 | 관찰 결과 | 원본 |
|---|---|---|
| `python3 -m unittest discover -s tests` | 476건 통과 | [q2-root-tests.txt](./q2-root-tests.txt) |
| `python3 -m unittest discover -s tools/tests` | 307건 중 306건 통과, 1건 skip | [q2-tools-tests.txt](./q2-tools-tests.txt) |
| py_compile, harness lint, diff check | exit 0; 신규 위반·회귀 0 | [q2-checks.json](./q2-checks.json) |
| 최종 신규 검사 28건·vault lint·범위 secret scan·문서 검사 | 모두 exit 0; vault 2건, secret 34파일 발견 0 | [q2-final-checks.json](./q2-final-checks.json) |

도구 검사에는 새 28건이 포함된다. root 476건은 기존 원본 작업 경로에만 있던 별도 훅 fixture 2건을 후보로 옮기지 않은 수치이며, Q1의 478건과 모수를 혼용하지 않는다. root 로그의 산출 경로 오류 문구는 거부 동작의 기대 출력이며 unittest 판정은 OK다. root 검사 후에는 새 admission 원장의 runtime 지문 저장과 그 crash 검사를 보강했고, 영향받는 tools 전체를 다시 실행했다. 이후 제품 코드 변경 없이 전송 검사의 고정 SQL 기대값을 강화하고 신규 28건을 다시 통과시켰다. 최종 검증 이후에는 근거 문서·baseline 기록만 정리했다.

## 독립 기대값과 장애 표본

아래는 `/Users/jm/Documents/workspace/team2-worktrees/production-query-usability/tools/tests/test_db_prod_approval.py`의 28개 test method와 기존 transport/control 회귀가 확인한 범위다.

| 범위 | 기대값의 근거와 관찰 |
|---|---|
| 전문 표시·실제 전송 | 고정 사용자 SQL과 독립 수작업 setup/observer fixture를 표시 문자열 및 실제 adapter pipe bytes와 비교. 원문 그대로 1회, observer는 취소 때만 1회 |
| 재개 포함 한 승인 | halted preview는 상태·자격증명 읽기·접속 변화 0. 한 approve_submit 이후 정확히 1회 실행. 중복 제출은 추가 접속/전송 0 |
| ready·긴급 중단 | ready는 resume action 없음·epoch 불변. SQLite trigger로 halted/epoch UPDATE 자체 0 확인. 긴급 해제 action 누락은 거부 |
| 변경·만료 | 틀린 action/digest/source, SQL/설정/profile/control SQL 변경, 같은 개수의 marker nonce 교체, expiry·잘못된 byte 한도 모두 거부·접속 0 |
| 원자성·경쟁 | 독립 Python 프로세스 두 개가 같은 슬롯을 경쟁해 consumed 승인·소유 슬롯은 하나. A rollback은 반쪽 소비 없음. B 부분 삭제/C rollback은 재개·접속 없이 차단/소유 슬롯 보존 |
| 실제 프로세스 소실 | A/B/C 각각 child에서 `os._exit(42)`. durable run·gateway PID/birth·runtime 지문·host/profile metadata 보존. C 직후는 starting/미차단이지만 소유 슬롯이 남고 재시작 halt 후 복구 검토 가능. 자동 재가동 0 |
| 복구 | admission metadata fallback은 worker journal 파일이 실제로 없는 때만 사용. 소유 실행기 fencing과 새 전문 승인 observer가 필요하고 복구 뒤 halt 유지. 손상 파일을 fallback으로 숨기지 않는 기존 검증 재사용 |
| 전송 전 gate | 누락된 consumed 승인, ticket SQL/deadline 변경·재사용, audit 실패, 자격증명 조회 중 새 stop은 접속/전송을 막음 |
| 시간·byte 한도 | admission/정리가 소비한 시간을 deadline에서 차감. 실제 SqlcmdBackend에 short-write 합성 pipe를 연결해 reviewed bytes와 byte overflow·observer payload 검증 |
| CLI 전체 흐름 | 실제 로컬 Unix socket/Handler와 CLI를 연결해 전문 표시·한 approve_submit·결과 digest를 확인. Backend는 합성이며 운영 socket/DB를 사용하지 않음 |
| 기록 최소화 | SQLite 실제 파일 bytes에 민감 fixture SQL 없음. audit/원장은 digest·식별자·상태/복구 metadata만 유지 |

TDD에서 표시 생략, 미지원 approve_submit/run, B/C 사이 새 marker 누락, consumed 승인 증거 누락, ready의 halted/epoch UPDATE를 각각 실패로 확인한 뒤 수정했다. 마지막 crash 표본의 runtime 지문 보존 검사도 A/B/C에서 `KeyError: runtime`으로 실패한 뒤 원장에 저장하도록 보강해 통과했다. 초기 import 경로 오류와 child PID 수집 오류는 테스트 harness 오류로 수정했으며 제품 결함의 red 증거로 세지 않는다.

## 운영 경로 보존과 남은 단계

개발 중 source fingerprint가 기존 CLI의 재시작 요구를 유발할 수 있음을 확인해 후보를 별도 worktree로 옮겼다. 기존 `/Users/jm/Documents/workspace/team2`의 이번 tracked 수정만 역적용하고, 원본 소스 지문이 작업 전 `57650f0d2969a969b79a3866628e4b0409bec3ee7764513217fdbb952cf348ed`와 같음을 확인했다. 다른 미추적 훅 근거·fixture·shepherdr 작업은 보존했다. 이 파일 동등성 확인은 실행 중 daemon의 상태 확인이나 배포 검증이 아니다.

운영 자격증명 조회·DB 연결·SQL 실행·중단 해제·설치·실행기 재시작·커밋·푸시·머지는 수행하지 않았다. SqlcmdBackend 검사는 실제 adapter와 합성 stdio를 사용하며 실제 sqlcmd/SQL Server·Docker 통합 검증을 수행한 것으로 해석하지 않는다. skip은 TTY가 없는 runner에서 기존 키체인 helper의 TTY 거부 검사 한 건이다.

Q2는 기존 연결형 실행과 소비형 fetch를 유지한다. Q3에서 immutable 운영 bundle·연결 분리형 작업·상태 조회·반복 fetch/ack를 구현한다. Q3b는 구조화 CSV, Q4는 통합·부하·운영 반영 준비다. 미공개 SQL 자동 재실행·CSV 자동 재조회·stale gateway 자동 재시작은 없다. 이 후보를 설치·운영에서 검증하기 전에는 실제 사용 가능 상태로 보고하지 않는다.
