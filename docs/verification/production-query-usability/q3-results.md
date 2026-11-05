# 운영 조회 Q3 안정 실행·결과 이어받기 검증

- 작업 ID: `TASK-20261104-4560e95349bc`, 2026-11-04 macOS 로컬 검증.
- 대상: `/Users/jm/Documents/workspace/team2-worktrees/production-query-usability`, `team2/production-query-usability`, base/HEAD `ff0ca564cea38e1814677a235102d4512ac4cee9` 위 미커밋 Q2+Q3 후보.
- 재개 대조: Q2 baseline의 15파일 SHA-256이 모두 일치한 뒤 Q3에 착수했다. Q2 기록은 과거 검증 대상으로 보존한다. 최종 Q3 지문은 [q3-baseline.json](./q3-baseline.json), 실행 시점·명령·결과는 [q3-checks.json](./q3-checks.json)이다.
- 계약: [실행 설계 §5](../../production-query-request-flow.md). SQL 전문 공개·명시 승인·전역 한 슬롯·deadline·중단·watchdog·서버 종료 확인을 재사용한다.

## 구현과 관찰

1. 같은 SQLite A transaction에서 승인 소비·소유 슬롯과 job request/run/owner/instance를 함께 기록한다. approve_submit은 정확한 재개 검증·audit 이후 gateway 소유 thread를 시작하고 접수 응답을 반환한다. 클라이언트 연결 여부는 이 thread의 실행권·watchdog heartbeat가 아니다. 실행 중 phase는 기존 영속 제어 원장과 request/run 연결로 조회한다.
2. `job-status`·`result`와 run 내부 상태 조회는 SQL을 제출하지 않는다. 접수 응답이 유실돼도 기존 ID만 조회한다. fetch는 owner·request/result digest·epoch·현재 stop·TTL·미ack을 확인하고 같은 offset에 같은 bytes를 돌려준다. 전체 길이·SHA-256 확인 뒤 delivered를 먼저 commit하고 메모리를 정리한다. ack 응답 유실·재시작 뒤에도 metadata로 반복 확인한다.
3. 새 중단, 만료, 다음 결과, gateway 손실은 stopped/expired/superseded/lost_on_restart로 구별한다. 최신 1개·60초·v2 최대 32MiB payload는 메모리에만 남는다. 종결 metadata는 30일 이내 멱등 확인, 기동 시 오래된 종결 job 정리다. 미종결·복구 필요 job은 TTL로 정리하지 않는다. 원문 SQL·결과·비밀번호는 job 원장에 저장하지 않는다.
4. 지문별 bundle은 owner 전용 디렉터리에 원자적으로 준비하고 directory 0500/files 0400으로 고정한다. manifest가 파일 digest·capability·job schema를 고정한다. 개발 소스 변경은 이미 준비한 bundle에 반영되지 않는다. 선택 도구는 gateway lock 획득·halted idle·active 없음·schema 호환 뒤에만 current symlink를 교체한다. 새 serve는 검증된 bundle에서만 기동한다. launchagent 명령은 plist만 생성한다.

기존 v1 execute/fetch 의미를 유지했다. v2 cache를 v1 fetch로 소비하는 우회는 거부한다. Q2 CLI socket 검사는 새 접수→상태 조회→반복 가능한 결과→ack의 전체 흐름으로 갱신했다. CSV는 구현하지 않았다.

## 검증 결과

| 검사 | 결과 | 원본 |
|---|---|---|
| 기본 전체 회귀 | 476건 통과 | [q3-root-tests.txt](./q3-root-tests.txt) |
| 도구 전체 회귀 | 329건 중 328건 통과, 1건 skip | [q3-tools-tests.txt](./q3-tools-tests.txt) |
| py_compile·harness lint·diff check | exit 0; 신규 지시문 위반·회귀 0 | [q3-checks.json](./q3-checks.json) |
| 최종 문서·vault·secret 검사 | 모두 exit 0; vault 2건, secret 51파일 발견 0 | [q3-final-checks.json](./q3-final-checks.json) |

skip은 TTY 없는 runner에서 키체인 helper의 TTY 거부 검사다. root 476건은 Q2와 같은 모수이며 원래 작업 경로의 별도 훅 fixture 2건은 포함하지 않는다. root 로그의 산출 경로 오류 문구는 거부 동작 기대 출력이고 unittest 결과는 OK다.

새 작업 검사 17건과 runtime 검사 5건, 기존 Q2 28건을 포함한다. 아래 기대값은 승인/중단 계약, 고정 `b'1\n'`와 한글·따옴표·개행 fixture, 수작업 60초/30일 경계, SQLite commit의 앞뒤 관찰, 실제 프로세스·파일 mode에서 구했다.

| seam | 실제 확인한 표본 |
|---|---|
| 접수·작업 | fake Backend가 완료되지 않은 동안 accepted 반환, disconnect=true에도 완료·SQL 1회, 중복 제출 추가 실행 0 |
| 응답 유실 | CLI 접수 응답과 첫 ack 응답을 각각 유실시켜 같은 ID의 상태 조회·ack 재확인만 수행, submit 1회·ack 2회·결과 일치 |
| bytes·완료 | 동일 offset 반복 청크 일치, 다중 청크 한글·개행 전체 bytes/SHA 일치, 변조 bytes는 ack 전 거부, ack commit 뒤 메모리 정리 오류에도 fetch 차단 |
| 중단·소유·수명 | UID/epoch/digest/offset 오류 거부·정상 결과 보존, 완료 후 새 marker에 fetch/ack 차단, fetch가 TTL 연장하지 않음, 다음 결과 supersede |
| 재시작·복구 | 완료 결과 lost_on_restart, ack tombstone 유지, preview_lost 새 검토 요구, 31일 뒤 종결 확인 거부·미종결 복구 기록 유지. 기존 A/B/C 실제 child crash와 fencing 검사 재실행 |
| 작업 손실 | thread 시작 오류를 recovery_required로 표시, 접속 0·자동 재실행 0. detached 실행 중 timeout/명시 stop은 실패·차단·중복 재실행 0 |
| 운영판 | bundle 준비 뒤 개발 gateway 파일 변경에도 bundle digest 불변, payload/mode 변경 거부, 선택 시 실행 중 lock·ready·unconfirmed·schema 불일치 거부, halted idle만 선택 |
| 정상 기동 | 임시 bundle에서 Python `-I` CLI 실제 실행. 임시 상태/소켓의 실제 gateway subprocess 기동·status·SIGTERM 종료, credentials helper 없는 상태에서 halted/idle·capability 확인. 운영 상태·소켓을 사용하지 않음 |

TDD 최초 실패는 연결 종료가 SQL 중단으로 이어짐(`stopped`), 미지원 fetch_result, v1 fetch의 v2 결과 우회, thread 시작 실패가 영구 starting으로 남음이다. 각각 작업 소유 분리·반복 fetch/ack·legacy gate·복구 상태 기록으로 수정했다. 런타임 새 모듈 부재 뒤 구현했고, 테스트의 존재하지 않는 resume 호출과 macOS `/var`/`/private/var` 경로 별칭 비교는 fixture 오류로 수정했다. 기존 CLI mock이 새 상태 조회를 응답하지 않아 대기한 것도 mock을 새 계약에 맞춰 고쳤다. 이 fixture 오류를 제품 결함 증거로 세지 않는다.

## 한계와 다음 단계

운영 자격증명·DB·SQL·설정·소켓·실행기·launchd를 변경하지 않았다. 원래 `/Users/jm/Documents/workspace/team2`의 tracked diff가 비어 있고 source fingerprint가 Q2 전과 같은지는 최종 baseline에 기록한다. bundle 선택·gateway 기동 검사는 모두 임시 fixture에 한정한다. 실제 SQL Server/sqlcmd·Docker·운영 launchd 등록/재시작·서명/설치 권한 검증을 수행한 것으로 주장하지 않는다. 기존 watchdog/transport 합성·로컬 프로세스 회귀를 재사용한다. 실제 실행기/worker 손실의 운영 환경 통합·부하 및 롤백 점검은 Q4에서 다룬다.

CSV는 다음 Q3b에서 구조화 결과·값 보존·파일 공개를 구현한다. 배포·운영 조회는 별도 승인 대상이며, plan-run을 그 승인으로 해석하지 않는다. Q3 검증 이후 변경은 문서·evidence·vault 상태 정리뿐이다.
