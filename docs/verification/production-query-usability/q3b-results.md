# Q3b 구조화 CSV 선택 저장 — 검증 결과

- 작업 ID: `TASK-20261105-c5044da1af18`, 2026-11-05 macOS(arm64) 로컬 검증.
- 기준: main `add6fad` → branch `team2/production-query-q3b` (slice 1 커밋 `9e5014a` + slice 2~4 미커밋).
- 계약: [설계 §6](../../production-query-request-flow.md). 운영 실행기·원장·socket·키체인·운영 DB를 쓰지 않았다.

## 구현 범위

| slice | 내용 |
|---|---|
| 1 codec | `tools/db_prod_export.py`: canonical spec, `build_batch`(SELECT 하나를 `FOR JSON PATH, INCLUDE_NULL_VALUES` + `varchar(8000)` hex frame batch로), bounded `CsvExport`(frame → UTF-16LE → JSON record → development-csv-v1) |
| 2 gateway·transport | `prepare(output_mode='csv')`가 batch·spec을 검토 봉투에 결속하고 `export_csv` action 추가. transport `attach_stream_sink`로 stdout을 메모리 대신 sink로, sink 거부 시 조회 실패. `query_exports_v1` 원장, 0700/0600 staging, 완료 commit → manifest → 공개 gate(중단·halt·epoch) → `renamex_np(RENAME_EXCL)`, 재기동 reconciliation |
| 3 CLI | `preview --output csv --columns --purpose --max-file-bytes [--max-record-bytes --max-source-bytes]`, 검토에 spec·저장 위치·CSV 승인 문구. `run`·`result` 종료 코드가 job·export 결과를 반영(Q4 발견 1 수정) |
| 4 E2E | `e2e_flow.py`에 CSV 5개 시나리오와 실패 job 종료 코드 검사 추가 |

## 검증 결과

| 검사 | 결과 | 원본 |
|---|---|---|
| 실제 sqlcmd frame gate `csv_frames.py` | PASS — bigint max·decimal(38,6)·datetime2(7)·NULL/빈 문자열/리터럴 `\N`·값 안 CRLF·한글 20만 자·ORDER BY·빈 결과 | [q3b-codec-gate.log](./q3b-codec-gate.log) |
| E2E `e2e_flow.py` (실제 bundle·gateway·CLI·sqlcmd·SQL Server 2022) | 26/26 PASS, 컨테이너 삭제, 보고서에 fixture 비밀번호 없음 | [q3b-e2e.json](./q3b-e2e.json), [q3b-e2e.log](./q3b-e2e.log) |
| tools `python3 -m unittest discover -s tests -p 'test_*.py'` (`tools/`) | 365건 OK, 1건 skip(TTY 없는 키체인 helper) | |
| root `python3 -m unittest discover -s tests -p 'test_*.py'` | 476건 OK | |

신규 단위 검사: codec 12, 공개·reconciliation 7, transport stream 5, gateway export 8, client 5.

E2E CSV 시나리오:

| 시나리오 | 관찰 |
|---|---|
| 정상 export | exit 0, `exported`, CSV 값 일치(`\\N` 이중화·NULL `\N`·값 안 CRLF·한글), manifest spec digest = 검토 digest·records 2, 디렉터리 0700, 생성 batch 전송 1회, staging 없음 |
| 파일 한도 12바이트 | 스트리밍 중 거부 → exit≠0, `failed`, 산출물 없음, 서버 세션 0, halted 유지 |
| 목적지 이미 존재 | exit≠0, `not_published`/`destination_exists`, 기존 파일 그대로 |
| export 중 사용자 stop | exit≠0, `failed`, staging 삭제, 서버 세션 0 |
| export 중 gateway SIGKILL | staging 생성 확인 → watchdog fence → 재기동 reconciliation `failed`/`gateway_restarted`, staging 삭제, job `recovery_required`, 재전송 0 |
| 실패 job 종료 코드 | 사용자 취소·시간 초과·worker 손실 모두 exit≠0 |

## 발견과 수정

1. **job terminal과 export 공개 사이 경쟁(제품 결함).** job이 `completed`로 기록된 뒤 공개가 진행돼 `run`이 `complete` 상태를 읽고 실패 종료할 수 있었다. 첫 E2E의 "목적지 존재" 실패로 드러났다. 단위 테스트의 대기 함수가 export 정착까지 기다려 이 경쟁을 가리고 있었다. 대기를 엄격히 하고 공개를 늦추는 테스트로 red 재현 → export 정착 뒤 job 종결로 순서 변경 → green.
2. harness 오류(제품 결함 아님): CSV를 `read_text()`로 읽어 CRLF가 LF로 바뀜 → bytes 디코드로 수정. 같은 SELECT의 생성 batch가 두 시나리오에서 동일해 전송 수를 전체로 세면 2가 됨 → 시나리오 전후 차이로 판정.
3. TDD 기록: codec·transport stream·client·경쟁 회귀는 red를 관찰했다. 공개·reconciliation 7건과 gateway export 첫 6건은 구현과 같은 호출에서 처음 실행해 red를 별도로 관찰하지 못했다.

## 운영 반영 전제와 미확인

- 실행기 교체가 필요하다(새 capability `csv_export`, 새 모듈). 절차: `tools/README.md` §운영판 launchd 수명 — `bootout` → `build` → `activate`(halted·idle·active 없음) → `bootstrap`. 사용자 승인 대상이다.
- job schema 버전은 그대로이고 export 원장은 별도 테이블이라 이전 번들로 rollback해도 원장이 호환된다(이전 번들은 새 테이블을 무시).
- 미확인: 운영 SQL Server에서 `FOR JSON`·`varchar(8000)` frame 동작(fixture는 SQL Server 2022 CU24·`sa`), 운영 계정 권한에서의 생성 batch 실행, 대용량(수백 MB) export 처리 시간·디스크 사용, macOS 외 플랫폼(공개 거부).

## 마감 리뷰 반영 (2026-11-05, `/ad:code-review 2d28b98`)

강도 위험. 메인 판정 + 보안 감사·데이터 정합성 페르소나(같은 벤더, 읽기 전용). 페르소나 발견 15건은 메인이 코드·실행으로 검증해 13건으로 병합했다(기각 0). 교차 모델 리뷰는 생략(기본값).

| # | 결함 | 수정 |
|---|---|---|
| 1 | 열린 export 행이 있을 때 exports 디렉터리 삭제·권한 변경이면 reconcile 예외로 gateway 기동 실패(launchd 재시작 반복). 실행 재현 | reconcile은 파일시스템 상태로 예외를 던지지 않고 행만 분류 |
| 2 | `export_unknown`인데 final이 없으면 `not_published`로 강등 | 증거 없이는 `export_unknown` 유지 |
| 3 | rename 이후 기록 실패 시 abort가 `failed`로 덮어씀 | 공개 시도 뒤 abort는 `export_unknown`만 기록, 파일을 건드리지 않음 |
| 4 | 루트 권한 문제가 승인 소비 뒤 드러나 `recovery_required` | `preview` 단계에서 플랫폼·루트 검사 |
| 5 | CSV job 원장에 `output_bytes=0`·빈 sha | CSV receipt에서 메모리 결과 필드 제거 |
| 6 | codec 거부 사유가 `query_not_completed`로만 기록 | `failure_reason()`을 원장 reason으로 |
| 7 | `max_source_bytes` 기본 8배는 좁은 행에서 부족 → halt | 기본 64배 |
| 8 | 괄호를 닫아 SELECT를 추가하면 단일 SELECT 검사 통과(쓰기는 `validate_read_sql`이 거부, 실행 확인) | 괄호·따옴표·주석 균형 검사 |
| 9 | staging에 미리 있는 manifest를 검증 없이 공개 | 존재하면 거부 |
| 10 | 감사 로그에 csv sha256·건수 | 감사에는 state·reason만 |
| 11 | 공개 직전 루트 재확인 없음 | 루트·staging lstat 재확인, 신뢰 불가면 손대지 않고 미공개 |
| 12 | lineage에 approval digest 없음, epoch를 worker에서 다시 읽음 | activation 시점 epoch·approval digest를 intent·manifest에 기록 |
| 13 | 스프레드시트 수식 실행 위험 | 검토 화면 경고, README에 처리량 상한과 함께 명시 |

안전 가정 입증(실행 확인): 생성 batch가 운영자 승인 DB 경로의 `validate_local_references`를 통과하고 3-part 참조는 거부. 괄호 탈출 UPDATE는 `validate_read_sql`이 거부. codec 최대 RSS는 stdout 250MiB에서 13MiB 유지, 단일 0.9MiB 행 22MiB(설계 §6 출시 조건). 처리량 약 8MiB/s.

반영 뒤 검사: 신규 회귀 14건 red 관찰 후 green. export 관련 46건, tools 379건(1 skip), root 476건 OK. E2E 26/26 재통과(위 표의 q3b-e2e.json은 반영 뒤 실행본).
