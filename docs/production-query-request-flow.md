# 운영 조회 SQL 공개·단일 승인·안정 실행 설계

상태: **Q3 안정 운영판·연결 분리·결과 이어받기 구현·격리 검증 완료 — 운영 미반영**. 후보는 `/Users/jm/Documents/workspace/team2-worktrees/production-query-usability`, 브랜치는 `team2/production-query-usability`다. 기존 운영 경로의 소스·설정·실행기는 유지한다. Q3b·Q4는 미완료다. 작업 ID `TASK-20261104-4560e95349bc`. 진행 원장은 `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/projects/production-query-usability/plan.md`다. 구현·배포·운영 SQL 실행 승인을 대신하지 않는다.

## 1. 범위와 사용 예

기존 client/gateway/control/transport/watchdog/recovery를 재사용한다. 새 웹 서버·작업 큐·DB 드라이버를 도입하지 않는다. Q1 산출물은 이 계약과 검토 근거이며, Q2(승인), Q3(작업·결과), Q3b(선택 CSV), Q4(통합 검증)로 구현을 나눈다. 한 슬라이스가 8파일을 넘으면 상태 전이와 화면 표시를 별도 슬라이스로 나눈다.

사용자는 목적을 전달하고 다음 내용을 확인한 뒤 “재개하고 표시한 SQL을 1회 실행” 또는 “표시한 SQL을 1회 실행”을 승인한다.

```text
대상: {별칭}/{DB}  실행 최대: {60초 이하}  결과: {행·바이트 한도}
동작: {실행만 | 표시한 중단 상태 해제 + 이 요청 1회 실행}
저장: {메모리만 | 필요에 따른 비공개 로컬 CSV, 경로·용도·필드}
연결 준비 SQL: {실제 전문}
조회 SQL: {실제 전문}
종료 확인 SQL: {실제 전문} / 실행 조건: 취소 또는 종료 불확실 시 1회
승인 식별자: {검토 전체 digest}
```

여기 중괄호는 UI 설계 예시다. 실제 검토는 SQL·태그·대상을 확정해 모두 채운다. 전문을 해시·요약·말줄임표로 대체하거나 기존 “종료 확인 SQL 표시 생략” 문구를 재사용하지 않는다. SQL 안의 제어 문자는 보이는 이스케이프로 표현하고 실제 바이트 digest는 원문 기준으로 고정한다.

논리 인터페이스(최종 명칭은 구현 관례에 맞춘다):

```text
prepare(sql, target, limits, resume=if_needed, output_mode) → request_id, complete_review, digest
approve_submit(request_id, approval_digest, selected_actions, approval_source) → accepted_job | rejected
job_status(request_id) → phase, outcome, result_state, next_action
fetch(request_id, result_digest, offset) → immutable bounded chunk
ack(request_id, result_digest) → delivered | already_delivered
export(request_id, result_digest, approved_export_spec) → local_csv | refused
```

`prepare`는 접속·비밀번호 조회·중단 해제 없이 검토 자료만 만든다. 채팅 digest 전달은 사용자의 명시 승인을 전달하는 협력적 경로이며 사람 인증의 증명이 아니다. 기존 같은 UID 신뢰 모델은 유지한다. 기존 v1 승인·resume의 의미를 조용히 바꾸지 않고 새 계약의 capability/version을 구분한다.

## 2. 사용자 상태와 전이

| 상태 | 검토 가능 여부와 행동 | 실행 조건 |
|---|---|---|
| ready: idle·미차단 | 전체 SQL 표시, 실행 승인 1회 | snapshot·설정·digest·유효기간 일치 |
| resume-required: halted·idle·active 없음 | 접속 없는 검토, 재개 포함 승인 1회 | 기존 종료 증거와 정확한 epoch·marker 확인 |
| emergency-stop: 지속 중단·idle | 긴급 중단 해제 의미를 별도 문구로 같은 검토에 명시 | 일반 SQL 승인을 해제 승인으로 해석하지 않음 |
| busy: active 존재 | 상태와 취소 경로 표시 | 새 실행권 부여 없음, 자동 대기열 없음 |
| recovery-required: 종료 미확인·고아 worker | 기존 fencing·종료 관찰 복구 검토로 안내 | 종료 증거 전 일반 재개·실행 불가 |
| incompatible: 운영판·프로토콜·원장 불일치 | 기존 작업 상태만 확인, 버전 조치 안내 | 호환성 해결과 새 검토 전 실행 불가 |
| corrupt/unknown | 원장·marker 오류와 필요한 조치 표시 | 새 원장 생성·강제 해제 없이 차단 |

상태 원인과 작업 결과는 분리한다. `SQL 성공`, `결과 보관`, `클라이언트 전달 완료`는 서로 다른 사실이다. 오류·재시작 후 오래된 SQL·승인은 자동 복원하지 않는다.

## 3. 검토 봉투와 승인 범위

서버가 불변 검토 봉투를 만들고 canonical serialization의 SHA-256을 사용한다. 봉투에는 owner UID·요청 ID·대상/DB·정확한 사용자/준비/종료 확인 SQL·조건부 실행 조건과 횟수·timeout·결과 한도·출력 모드·프로파일/정책/운영판 fingerprint·생성/만료 시각·중단 snapshot·해당 검토의 정확한 승인 action 집합을 포함한다. host tag는 검토 때 정해 전송 때 재생성하지 않는다.

각 검토의 action 집합은 서버가 상태·출력 모드로 확정한다: ready는 execute_once, 재개 필요는 resume_current_stop+execute_once, 긴급 중단이면 release_emergency_stop도 추가, 승인된 CSV 모드이면 export_csv도 추가한다. “할 수 있는 action” 목록을 승인과 혼용하지 않는다. 화면에 실제 승인할 정렬된 정확한 집합을 표시하고 `approval_digest=H(envelope_digest, request_id, selected_actions)`로 결속한다. A는 submitted selected_actions·approval_digest가 서버의 해당 검토에 정확히 일치하는지 확인하고, 같은 commit에 집합·두 digest·승인 출처를 보존한다. 부분 승인·추가 action은 실행/재개 없이 거부하며 필요하면 새 검토를 만든다. 중복 요청은 원래 저장된 집합만 반환한다.

- 중단 snapshot: epoch, halted/reason, phase, active, 정렬된 정확한 marker nonce 집합. 같은 개수만 비교하지 않는다.
- 실행 승인과 중단 해제 승인은 별도 action이지만 한 검토에서 함께 명시 승인할 수 있다. 표시된 중단 상태만 해제 가능하다.
- 기존 30분 준비 유효기간과 최대 128개 준비 요청 한도를 재사용한다. 만료·내용/SQL/프로파일/한도·중단 상태 변경은 새 전문 표시와 새 승인으로 이어진다.
- 원장에는 digest·상태·대상 별칭·owner·승인 출처·run/instance 식별자·시각만 기록한다. 원문 SQL·자격증명·조회 결과는 원장·일반 로그에 저장하지 않는다. SQL·검토 봉투는 gateway 메모리에 유지하므로 gateway 소실 뒤에는 새 검토가 필요하다.
- 사용자 SQL 전송은 기존 `_write_query`의 UTF-8 원문 바이트를 유지한다. 연결 준비·조건부 observer도 봉투의 전문과 실제 payload를 독립 fixture로 대조한다. 승인 후 편의상 SQL·주석·GO·후처리 SELECT를 추가하지 않는다.
- 연결 준비와 사용자 조회의 승인 실행 한도는 60초 이하로 표시한다. 취소·종료 확인은 별도 승인된 조건부 batch 1회·최대 5초이며, 전체 경과 시간과 사용자 SQL 실행 시간을 구분해 보여준다. observer 재연결·SQL 재실행은 새 승인 없이 반복하지 않는다.

## 4. 재개·승인 소비·슬롯 확보

클라이언트가 `resume → approve → execute`를 세 RPC로 연결하는 설계는 채택하지 않는다. gateway가 한 번의 승인 접수에서 기존 로컬 SQLite 원장과 중단 gate를 사용한다.

```text
불변 검토 + 명시 승인
  → A. 짧은 제어 트랜잭션: snapshot·두 digest·정확한 action 집합·expiry·version 확인
       승인 1회 소비 + 요청/run 기록 + 단일 슬롯 확보
       phase=admitting; 외부 halted는 원래 값 유지
  → B. resume 경로에서만 검토된 marker 제거·fsync; 외부 halted=1 유지
       ready 경로는 marker를 제거하지 않음
  → C. 짧은 제어 트랜잭션: epoch/소유 run/phase/새 marker 재확인
       resume 경로만 승인된 외부 halt 해제·epoch 전진
       ready는 외부 halted/epoch를 쓰지 않음; run 실행 세대 고정
       active=이 run, phase=starting, 내부 실행 gate 활성
  → 승인된 audit 기록 확인 → credentials → bounded backend.start
  → 기존 dispatch intent + 최종 중단 검사 → SQL 1회 전송
```

준비 초안을 만들 때 기존 원장을 해제하지 않는다. 내부 admission gate는 기존 영속 phase로 표현한다: `admitting`은 닫힘, `starting` 이후만 연결/전송 후보이며 각각의 claim·dispatch 검사를 통과해야 한다. 외부 중단은 halted/epoch/markers로 별도 표현한다. 같은 요청 중복은 기존 상태를 반환하고, 같은 ID·다른 digest는 거부한다. 다른 요청은 active 슬롯 점유로 거부한다. A/B/C와 source SQL을 하나의 외부 분산 트랜잭션이라고 부르지 않는다.

| 경로 | A 뒤 외부 상태 | B | C의 CAS·허용 변경 |
|---|---|---|---|
| ready | halted=0, epoch=E, active=R, phase=admitting | marker 삭제 없음 | 같은 epoch·외부 미중단·marker 없음·소유 슬롯·admitting이면 phase만 starting으로; 외부 halt 해제 없음 |
| resume-required | halted=1, epoch=E, active=R, phase=admitting | 승인된 정확한 nonce만 제거 | 정확한 원 halt snapshot·E·소유 슬롯·admitting·새 marker 없음·resume action 일치일 때만 halted=0, epoch=E+1, phase=starting |
| 둘 다 새 stop | halted=1 또는 epoch/marker 변화 | 새 marker 보존 | CAS 실패, 외부 중단 유지·내부 gate 닫힘, SQL 0회 |

- A에서 실패: SQL·접속·marker 변경 없음. 승인 소비와 슬롯이 같은 SQLite commit으로 남지 않으면 실행을 시작하지 않는다.
- A 이후 B/C 실패·프로세스 손실: 원장에는 consumed 승인과 active/admitting이 남고 내부 gate는 닫힌다. 외부 halted가 0인 ready 경로도 active·phase로 신규 admission/dispatch를 차단한다. 재시작은 기존 startup halt를 추가한다. marker 일부 제거를 SQL 승인 복원이나 다음 요청 자동 허용 근거로 삼지 않는다. 기존 실행기 신원 fencing·복구 경로로만 정리한다.
- A의 동일 commit에 admitting 복구 레코드도 기록한다: gateway PID·생성 시각, runtime digest, request/run, target/DB 별칭, host tag, profile digest, stage. 아직 생성되지 않은 별도 worker journal을 필수로 가정하지 않는다. Q2는 recovery의 허용 phase와 레코드 검증을 admitting까지 확장한다. 살아 있는 원 gateway는 먼저 fencing하고, 유효한 소유권 증거와 별도 전문 검토·승인된 observer 1회의 세션 0건 증거가 있어야 슬롯만 정리한다. 차단·consumed 승인·실패 상태는 유지한다. 레코드 불완전은 unknown으로 거부하며 행 삭제·기한 만료로 강제 해제하지 않는다.
- C는 B 이전 snapshot의 epoch·소유 슬롯·정의된 admitting 상태를 비교한다. 중간에 새 중단이 epoch를 바꾸거나 새 marker가 생기면 열지 않는다. 과거 승인 전부는 이전 세대로 남아 유효해지지 않는다.
- ready 경로도 같은 슬롯 확보를 사용하되 외부 중단 해제 권한을 생성하지 않는다. 내부 admitting 동안 marker가 추가되면 역시 거부한다.
- 마커 파일과 SQLite 사이에는 공통 원자 commit이 없다. marker 재확인·외부 halt 보존·내부 phase gate·소유 슬롯·영속 intent·재시작 차단으로 실패를 안전하게 남긴다. 파일 I/O·SQLite 실패를 임의 재시도로 숨기지 않는다.
- `LatchStore` 검사·독립 marker·watchdog를 유지한다. dispatch gate 이전에 관측·반영된 중단은 SQL 전송을 막는다. 최종 gate와 경합하며 이미 전송 단계에 들어간 요청은 취소·종료 확인 대상이다. 물리적으로 이미 보낸 SQL의 소급 취소나 marker 쓰기와 네트워크 전송의 완전한 원자성을 주장하지 않는다.
- 제어 잠금과 SQLite 쓰기 트랜잭션 안에서 DB 접속·query 대기·종료 관찰·대용량 결과 쓰기를 하지 않는다. 기존 짧은 nonblocking dispatch와 결과 청크 gate를 재사용한다.
- 독립 감사 DB와 제어 원장의 원자 commit도 가정하지 않는다. 접수·전송 intent와 작업 상태는 동일 제어 원장에 기록한다. 기존 감사 쓰기가 실패하면 SQL 전송 전에는 차단하고, 전송 후에는 상태를 불명확/복구 필요로 남긴다.

`Supervisor.execute`에는 “임의 run ID로 reserve를 건너뛰는 옵션”을 추가하지 않는다. 원장이 발급한 소유권·세대·승인 소비를 재확인하는 제한된 admission 계약을 두고, 기존 v1 경로는 기존 reserve를 유지한다. backend·watchdog·dispatch·finish 검증을 우회하지 않는다.

구체 seam은 `ApprovalLedger.admit` → 내부 `AdmissionTicket` → `Supervisor.execute_admitted`다. Q2는 기존 Store에 v2 책임을 모두 넣는 대신 같은 SQLite transaction을 사용하는 ApprovalLedger로 조합했다. ticket은 gateway 외부 JSON에서 받지 않으며 request/run ID·digest·owner·target fingerprint·활성 epoch·gateway 신원과 원장의 consumed 기록을 연결한다. `execute_admitted`는 backend 생성 전에 이를 대조하고 `ApprovalLedger.claim_backend_start`로 연결 시작 intent를 한 번만 commit한다. ticket 재사용은 credentials·connect 전에 거부한다. 기존 실행 루프를 공통 내부 경로로 재사용하며 raw run ID만으로 검증을 건너뛰는 API를 만들지 않는다. connecting intent 이후 crash는 재접속·재전송이 아닌 fencing/복구다.

작업 실행 deadline은 A의 승인 소비·접수 시점 monotonic + 승인 timeout으로 한 번만 정하고 같은 gateway instance의 ticket에 고정한다. B/C·thread 시작·연결 준비가 소비한 시간을 빼며 Supervisor/transport가 새 60초를 시작하지 않는다. deadline 이후 backend 시작·SQL 전송은 거부하고 종료 확인으로 간다. 재시작 후 저장된 wall clock만으로 작업을 재가동하지 않는다. 30분 preview TTL은 실행 대기열 허용 시간이 아니다.

v2 preview는 기존 v1 `Store.prepare`의 halted 거부를 해제하지 않는 별도 경로다. 검토 봉투는 메모리, 불변 digest·만료·상태만 로컬 원장에 둔다. A는 동일 제어 DB에서 preview 상태를 CAS하고 consumed 승인·소유 슬롯을 함께 기록한다. gateway가 검토 봉투를 잃으면 metadata만으로 승인·실행을 재구성하지 않고 `preview_lost`와 새 검토를 안내한다.

## 5. 안정 실행과 재접속

기존 gateway가 작업의 소유자다. 승인된 작업 하나만 단일 bounded 실행 경로에서 돌리며 외부 브로커·별도 DB worker 서비스를 추가하지 않는다. 요청 접수 commit 뒤에만 접수 응답을 보낸다. 사용자에게는 요청 ID를 직접 조작하게 하기보다 목적·상태·다음 행동을 표시한다.

Q3 구현은 A에서 `query_jobs_v2`의 request/run/owner/instance 기록도 같은 transaction에 추가한다. `approve_submit`은 A/B/C와 승인 audit 뒤 daemon thread를 시작하고 accepted를 반환한다. 기존 제어 원장의 영속 phase를 request/run과 연결해 실행 중 상태를 제공하고 종결 결과는 job 원장에 기록한다. `job-status`는 재실행 없는 상태 조회이며 `result`는 같은 결과를 다시 받아 길이·SHA-256 확인 뒤 ack한다. `run`도 이 두 경로를 사용한다. 단순 Ctrl+C는 대기만 끝내고 조회 중단은 `stop`이다. v1 execute/fetch는 기존 의미를 유지하며 v1 fetch로 v2 결과를 소비하는 경로는 거부한다.

- 영속 상태: preview digest/expiry → admitting → starting → dispatching → running → finishing → completed 또는 failed/unknown/recovery-required. 전달 완료는 delivered, 반출은 exporting/exported/export_unknown으로 별도 기록한다. 임의 상태 점프를 허용하지 않는다.
- 접수 응답 유실: 같은 ID의 상태 조회만 한다. 새 ID를 만들어 SQL을 다시 제출하거나 승인 소비를 취소하지 않는다. 시작되지 못한 admitted 작업도 자동 재실행하지 않는다.
- client 연결 종료: gateway 소유 작업과 watchdog는 유지되고 사용자는 상태 조회로 다시 붙는다. client를 gateway/worker 소유권 heartbeat로 사용하지 않는다. 실행기·worker 종료와 단순 표시 연결 종료를 구별한다.
- 실제 gateway/worker 손실: 기존 PID·생성 시각 fencing·복구 journal·세션 종료 증거를 유지한다. launchd가 프로세스를 다시 띄워도 모든 과거 실행은 재전송하지 않는다.
- 종료 확인 전에는 슬롯·결과를 공개하지 않는다. SQL 성공·제어 commit 성공·감사 성공이 확인돼야 result_available로 전이한다. audit/finish 실패 뒤 기존 결과 캐시를 성공으로 노출하지 않는다.
- 실행기 메모리만 기본 보관한다는 사용자 선택을 적용한다. gateway 사망 뒤 영속 metadata에 completed가 남아도 결과는 `lost_on_restart`로 표시하고 SQL을 자동 재실행하지 않는다.
- Q3의 기본 캐시는 기존처럼 최신 결과 1개·완료 후 60초다. 새 결과로 대체되면 기존 요청을 `superseded`로 표시하고 읽기로 TTL을 연장하지 않는다. 현재 `RESOURCE_MAX_BYTES=None`이므로 기존에 유한 상한이 있다고 가정하지 않는다. 사용자가 새 v2 메모리 결과의 **기본 32MiB**를 선택했다. v2 memory 모드는 결과 payload를 32MiB 이하로 받고 검토 자료의 실제 byte 한도에 넣는다. 더 작은 요청 한도는 그대로 적용한다. v2 memory의 unlimited/32MiB 초과 요청은 준비 단계에서 거부하고 CSV 또는 명시된 기존 경로를 안내한다. 기존 v1 무제한 기본값을 조용히 바꾸지 않는다. 이는 payload 한도이며 Python object·transport buffer를 포함한 프로세스 전체 RSS가 32MiB라는 뜻은 아니다.

### 결과 이어받기

사용자가 동일 사용자·중단 세대에서 결과 이어받기를 허용했다. 기존처럼 offset을 먼저 소비하거나 마지막 청크에서 결과를 지우면 재접속이 불가능하므로 Q3에서 바꾼다.

- 매 fetch마다 owner UID, 요청/result digest, 현재 epoch, 미차단, TTL, 미ack 상태와 immutable 결과 식별자를 확인한다. bounded 청크를 같은 offset으로 반복 요청하면 같은 bytes를 반환한다. SQL 실행 승인을 재소비하지 않는다. ack commit 후 메모리 정리 전 crash/동시 fetch도 durable delivered 상태를 보고 bytes 반환을 거부한다.
- 클라이언트가 전체 길이·SHA-256을 검증한 뒤 ack한다. `(request_id, result_digest, owner, epoch)`의 ack tombstone을 같은 제어 DB transaction에서 durable delivered로 기록한 뒤 메모리를 정리한다. tombstone 없이 먼저 메모리를 지우지 않는다. ack 응답 유실·gateway 재시작 후 반복 ack는 metadata로 already_delivered를 확인한다. 중단 이후에는 전달 완료 상태만 조회 가능하고 결과 bytes는 반환하지 않는다.
- terminal job/ack/export 상태 metadata는 기본 30일 보존하며 보존 기간 내에만 멱등 확인을 보장한다. 이후는 expired/unknown으로 답하고 SQL을 재실행하지 않는다. 미종결·active·복구 필요 레코드는 TTL로 삭제하지 않는다. 원문 SQL·결과·자격증명은 이 metadata에 포함하지 않는다.
- 새로운 중단·권한/소유 불일치·만료·superseded/lost 결과는 재전송하지 않고 원인을 표시한다. 최종 결과 청크 gate 전에 반영된 중단이 결과 공개보다 우선한다.

### 운영판과 배포

런타임은 비공개 로컬의 digest별 immutable bundle로 설치하고 상태 원장·socket·stop.d·lock은 기존 공통 위치 하나를 사용한다. 개발 worktree의 파일 변경이 실행 중 운영판을 부분 갱신하지 않게 한다. 런타임 선택 symlink 교체는 승인된 배포에서만 한다. CLI는 현재 운영판과 protocol/capability를 확인한다.

프로세스 관리는 macOS 사용자 LaunchAgent의 launchd를 재사용하는 설치안을 제공하되 설치·재시작은 별도 승인 대상이다. 재기동은 DB 접속이나 중단 해제를 뜻하지 않는다. 정상 idle 전환·완료 확인 뒤에만 계획 교체하고 active 작업을 업데이트 때문에 강제 종료하지 않는다.

원장 변경은 로컬 SQLite additive migration으로 분리한다. production SQL Server schema·SP는 바꾸지 않는다. schema/capability가 맞지 않으면 오래된 binary로 원장을 열어 실행하지 않는다. rollback도 active 없음·종료 증거·호환성 확인 후 승인된 버전으로 전환하며 과거 승인은 복원하지 않는다.

## 6. 필요한 경우 CSV 저장 — Q3b

사용자는 필요한 결과를 CSV로 저장해 개발에 참고하는 것을 허용했다. 기본 메모리 보관의 **명시적 파일 반출 예외**이며 모든 조회 결과의 자동 저장이 아니다. 저장 모드·컬럼·용도·비공개 로컬 경로를 검토 자료에 포함한다. 원본은 Git·공개 저장소·자동 동기화 위키에 두지 않는다.

canonical export spec 전체(형식 버전·정확한 컬럼/순서/타입·NULL codec·고정 base directory·서버 생성 artifact 이름·용도)를 검토 봉투 digest에 포함하고 원장에 spec digest를 보존한다. export는 client가 보낸 경로·컬럼을 실행에 사용하지 않고 서버가 보관한 봉투에서 파생한다. client는 request ID·result digest·export spec digest만 참조하며 정확히 일치하지 않으면 거부한다. 봉투가 사라지면 metadata만으로 반출 사양을 재구성하지 않는다.

현재 sqlcmd의 공백 정렬 텍스트를 split하거나 구분자를 쉼표로 바꾸는 것만으로 CSV를 만들지 않는다. NULL/빈 문자열·따옴표·쉼표·개행·한글·긴 값이 손실될 수 있다. Q3b는 구조화 출력 전용 SQL을 **승인 전에 완성·표시**하는 모드부터 지원한다. 일반 SQL을 승인 후 감싸거나 CSV를 위해 몰래 재조회하지 않는다.

첫 구현 후보는 `FOR JSON PATH, INCLUDE_NULL_VALUES`의 배열을 고정 HEX UTF-16LE frame으로 반환하는 검토된 읽기 batch다. 단일 result set, 명시된 유일 컬럼 별칭·순서·타입을 계약에 넣고, 해당 sqlcmd 버전에서 문자열·frame 비절단을 격리 transport로 입증한 경우에만 켠다. 프레임 디코딩은 한정된 ASCII hex·정확한 길이·JSON 구조를 검증한다. 프로토콜 검증이 실패하면 CSV 저장을 거부한다. 이 후보를 일반 조회의 무조건적인 SQL 재작성으로 사용하지 않는다.

큰 CSV는 memory 결과를 거쳐 저장하지 않는다. 승인된 CSV 모드에만 bounded streaming sink를 주고, hex→UTF-16LE→JSON record→CSV를 제한된 buffer로 private staging directory에 기록한다. JSON 전체나 hex 전체를 한 번에 모으지 않는다. 검토 봉투에 유한 파일 byte 한도·컬럼 schema·record byte 한도·행수 한도/명시적 무제한·실행 시간을 넣는다. record가 buffer 한도를 넘거나 파일/디스크 한도에 도달하면 취소·정리하고 CSV 성공으로 표시하지 않는다. transport의 stdout 조각·코드 포인트·JSON token 경계를 가로지르는 테스트와 최대 record/RSS 관측이 streaming 모드 출시 조건이다. 기존 plaintext 수집 경로의 숨은 모드 전환으로 구현하지 않는다.

- 정확한 타입/값 보존: decimal·큰 정수·문자열 식별자·시간값은 검토된 명시 형식으로 고정한다. 부동소수점 재계산·Excel의 자동 타입 추론을 경유하지 않는다. 중복 key·부정확한 구조·복수 result set은 거부한다.
- CSV는 표준 writer로 UTF-8·고정 컬럼 순서·인용 규칙을 사용한다. NULL은 `\N`, 리터럴 선두 backslash는 escape하는 development-csv-v1과 column/type/null metadata를 함께 남겨 NULL과 빈 문자열을 구별한다. 자동으로 스프레드시트를 열거나 값을 평가하지 않는다.
- 위치 기본안: `~/Library/Application Support/team2-db/exports/{request_id}/`, directory 0700·파일 0600. 작업 ID·요청/결과 digest·건수·컬럼·생성 시각·용도만 manifest에 기록한다. 결과 원문은 일반 감사 로그에 넣지 않는다. 사용 후 정리 시점은 사용 목적에 맞춰 안내하며 자동으로 매번 영구 보관하지 않는다.
- 쓰기 전 durable exporting intent는 서버의 불변 `result_stream_id`, request/envelope/approval/spec digest, owner·epoch와 서버가 고른 artifact directory를 기록한다. 아직 알 수 없는 최종 content digest를 요구하거나 placeholder digest로 완료를 표현하지 않는다.
- 스트리밍 중 source byte SHA-256·CSV byte SHA-256·길이·record 수를 누적한다. 정상 EOF·frame/codec/schema 검증·세션 종료·SQL 성공·제어/감사 commit 확인 뒤에만 stream ID에 연결된 정확한 content/CSV digest와 수치를 completion으로 commit한다. completion 없는 staging은 publish 불가다. SQL/user 결과와 CSV의 digest를 같은 값으로 혼용하지 않는다.
- private staging directory의 manifest에는 canonical export spec **전체**, stream/request lineage, 최종 source/CSV digest와 길이·건수를 포함한다. canonical spec의 hash가 원장 spec digest와 정확히 같은지 검증해 봉투 소실 뒤에도 비교할 수 있게 한다. CSV와 manifest를 모두 완성·fsync하고 공개 준비 directory도 fsync한다.
- 최종 공개 전에 committed completion·owner·epoch·중단·정확한 spec을 재확인하고, 동일 파일시스템의 기존 목적지를 덮어쓰지 않는 directory 단위 원자 공개를 사용한다. CSV만 먼저 보이게 하지 않는다. 설치 OS의 no-replace 기능은 격리 검증 출시 gate이며 덮어쓰기 rename으로 대체하지 않는다. parent fsync·공개 이후 상태 기록 실패나 공개 여부 불확실은 export_unknown으로 남긴다. SQLite commit과 filesystem 공개를 하나의 원자 동작이라고 주장하지 않는다.
- 재시작 reconciliation은 durable completion·exporting intent에 지정된 소유 directory·manifest/CSV 두 파일의 digest·canonical spec을 비교해 이미 공개된 완전한 artifact를 exported 또는 export_unknown으로 분류한다. completion 없는 staging·symlink·부분 산출물·다른 기존 파일은 거부한다. 봉투나 유효한 중단 세대가 사라진 재시작 뒤에는 private staging을 새로 publish하지 않는다. 복구 작업은 SQL 재조회·다른 파일 복사·원본 덮어쓰기를 자동 실행하지 않는다.
- 공개 gate 전에 반영된 stop은 export를 막는다. 이미 승인해 로컬 파일로 반출한 결과를 뒤늦은 stop이 소급 회수한다고 주장하지 않는다. 쓰기 중단·오류 시 소유한 미완성 staging만 정리한다. 이미 존재하는 파일을 임의 삭제·덮어쓰기하지 않는다.
- 원 승인에서 구조화/CSV 모드와 정확한 export spec을 승인했고 동일 결과 stream 또는 완전한 bytes가 남은 경우에만 추가 DB 조회 없이 export한다. plain text·만료·부분 결과·미승인 spec이면 원 export를 `not_exportable`로 거부한다. export API는 새 SQL 준비·승인·실행으로 이어지지 않는다.
- 사용자가 이후 별도로 새 구조화 조회를 요청한 경우에만 새 request ID·승인·result digest와 새 lineage로 진행한다. UI는 이를 “원 결과 내보내기”가 아닌 “새 운영 조회”로 표시하고 원 결과와 시점/값이 달라질 수 있음을 구별한다. 원 request/result의 export는 계속 거부 상태이며 기존 결과를 새 조회 결과로 교체하지 않는다.

## 7. 반례와 구현 검증 계약

```text
prepare (DB 0회) ─ review SQL 전체 동일성 ─ 승인
  ├ 새 epoch / nonce 교체 / 만료 / 설정 변경 → 거부 [Q2 회귀]
  ├ A 동시 접수 → consumed 1·active 1 [Q2 프로세스 경쟁]
  ├ A/B/C 각 crash → 소유 슬롯 보존·재시작 차단, SQL 0 [Q2 fault injection]
  └ activation → setup → dispatch intent → SQL 1회
       ├ stop/부분 전송/종료 미확인 → 취소·복구 [기존 + Q2]
       ├ 접수·client 응답 유실 → 상태 조회, SQL 추가 0 [Q3 →E2E]
       └ finish/commit 확인 → memory result
            ├ 청크/ack 유실 → 동일 결과 이어받기 [Q3 →E2E]
            ├ 새 stop/만료/재시작/새 결과 → 차단·상태 표시 [Q3]
            └ 요청된 구조화 CSV → digest + publish gate [Q3b →E2E]
                 └ 잘린 frame/NULL/개행/디스크 오류/중단 → 저장 거부·정리
```

구현 seam: client 전체 검토 렌더링↔gateway 불변 봉투, ApprovalLedger admission↔Supervisor 실행권, transport 실제 bytes, gateway 작업/상태/fetch/ack, CSV writer의 입력·파일 공개. SQL 기대값은 구현 generator의 출력을 복사하지 않고 고정 fixture와 독립 수작업 기대값으로 대조한다.

기존 회귀 기반: `tools/tests/test_db_query_control.py`의 one-use/stop-before-dispatch/다중 프로세스 슬롯, `test_db_prod_gateway.py`의 marker/epoch 경쟁·준비 중 무접속·결과 commit gate, `test_db_prod_transport.py`의 원문 1회 전송·부분 쓰기·종료 관찰, `test_db_prod_watchdog.py`와 `test_db_prod_recovery.py`의 실제 소유자 fencing. Q2의 봉투·admitting 검증은 [Q2 근거](./verification/production-query-usability/q2-results.md), Q3의 작업·반복 fetch/ack·운영 bundle 검증은 [Q3 근거](./verification/production-query-usability/q3-results.md)를 따른다. CSV는 Q3b의 미검증 범위다.

Q2 구현 순서: T1(P1) 전체 SQL 렌더링·봉투 fixture → T2(P1) admitting 상태·원자 승인 소비/슬롯·marker 실패 전이 → T3(P1) gateway/CLI 단일 승인과 제한된 admission 연동. Q3는 이후에 작업 영속 metadata → 연결 분리 → fetch/ack 순으로 진행한다. Q3b는 검증된 구조화 frame → CSV codec → 원자적 파일 공개 순서다. 같은 gateway/control을 건드리므로 순차 구현한다.

성능 계약: 승인 하나에 실행 하나, 복구 observer 최대 1회, busy는 즉시 명시 응답. 메모리·준비 수·청크·TTL은 기존 상한 내에서 측정한다. 제어 트랜잭션 지연·독립 stop 반응·대형/최대 길이 결과를 기준선과 비교하고, 중단 응답이 악화되거나 상한이 깨지면 다음 배포로 넘기지 않는다. 이번 설계에서 성능 개선 수치를 주장하지 않는다.

배포 차단 조건: SQL 표시/실행 불일치, 중복 전송, 새 stop 소실, 종료 증거 없는 슬롯 정리, 결과 유출, CSV 값 손실, migration/rollback 불일치. 어느 하나라도 재현되면 새 경로를 끄고 기존 경로를 유지한다. 배포 전엔 격리 테스트·Docker transport·사용자 흐름을 검증하고 운영 반영 시 별도 승인을 받는다.

## 8. 근거와 미확인 범위

- [SQLite transaction](https://www.sqlite.org/lang_transaction.html): 기존 `BEGIN IMMEDIATE`와 단일 writer를 재사용한다. 승인·슬롯·작업 메타데이터를 같은 제어 DB transaction으로 묶는 설계의 근거다.
- [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html): DB 원자 commit을 외부 marker·audit DB·SQL 네트워크 전송까지 확대하지 않는다. 단계별 durable intent와 실패 시 닫힘은 본 설계의 별도 책임이다.
- [Python sqlite3](https://docs.python.org/3/library/sqlite3.html): thread 간 connection 공유 대신 기존처럼 작업별 연결·명시적 transaction을 사용한다. 설치 Python에 없는 새 autocommit API를 전제하지 않는다.
- [Apple launchd](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html): 사용자 background 실행의 내장 관리 수단. Q3는 생성 plist와 임시 bundle의 실제 프로세스 기동을 검증했다. 실제 launchd 등록·재시작·설치 권한은 운영 반영 승인 뒤 Q4 경로에서 확인한다.
- [Microsoft sqlcmd output](https://learn.microsoft.com/en-us/sql/tools/sqlcmd/sqlcmd-commands?view=sql-server-ver17), [sqlcmd options](https://learn.microsoft.com/en-us/sql/tools/sqlcmd/sqlcmd-utility?tabs=go&view=sql-server-2017): 공백 정렬·줄바꿈·너비·가변 길이 표시를 구조화 CSV로 오인하지 않는 근거.
- [FOR JSON NULL](https://learn.microsoft.com/en-us/sql/relational-databases/json/include-null-values-in-json-include-null-values-option?view=sql-server-ver15), [Python CSV](https://docs.python.org/3/library/csv.html): 명시적 NULL 계약과 표준 인용 규칙의 근거. 설치 transport에서 HEX frame과 전체 타입 정확성은 아직 미검증이며 Q3b 출시 gate다.

2026-11-04 확인. Q1은 설계 검토였으며 Q2·Q3는 격리 후보에서 구현·검증했다. 실제 DB·sqlcmd 연결과 운영 서비스 설치·중단 해제·재시작·배포를 수행하지 않았다. Q3는 결과 이어받기를 지원하지만 CSV는 아직 지원하지 않는다. 운영 DB 읽기 전용 권한·DMV 권한·실제 대상의 구조화 SQL 지원은 기존 개통/별도 승인으로 검증할 전제다. 같은 UID의 악의적 변조까지 막는 OS 격리는 범위 밖이다.
