# DB 이관/CDC 진단 정책

## 목적

IDC DB 운영 안정화와 향후 AWS 전환 기반 마련을 위해, 레거시 분석 산출물은 운영/현대화/DB 분리 기준과 별도로 CDC 적용 가능성 및 이관 위험을 함께 추출한다.

이 정책은 전체 DB CDC 재시도 계획이 아니다. 2주 안에 확인 가능한 범위에서 1차 대상을 선별하고, IDC MSSQL 안정성과 성능 개선에 직접 영향을 줄 수 있는 batch, procedure, table, query를 찾기 위한 최소 기준이다.

## 적용 범위

- batch job
- stored procedure
- table
- ad hoc query 또는 반복 조회 query
- rename/swap, truncate/drop/create, select into, 전체 update가 포함된 DB 작업
- 집계/랭킹/전시/추천/임시 산출물 table

## 저장 위치

| 산출물 | 저장 위치 |
|---|---|
| 정책/등급 기준/추출 필드 | 팀 하네스 `policies/`, `docs/`, `templates/` |
| 서비스별 진단 결과 | 로컬 Obsidian 운영 지식 위키 |
| batch/SP/table/query별 contract | 로컬 Obsidian 운영 지식 위키 |
| Google Sheet 업로드용 CSV/표 | 로컬 Obsidian 운영 지식 위키 또는 사용자 지정 로컬 경로 |
| YouTrack KB/Issue 반영 | 사용자 승인 후에만 수행 |

## 필수 추출 필드

분석 중 batch, SP, table, query 후보가 발견되면 아래 필드를 가능한 범위에서 채운다. 모르는 값은 추정하지 않고 `Unknown` 또는 `Needs Review`로 둔다.

| 필드 | 설명 |
|---|---|
| 번호 | 조사 row 번호 |
| 담당팀 | owner 후보 또는 확인 필요 |
| 대상명 | batch명, procedure명, table명, query명 |
| 유형 | batch / procedure / table / query |
| 관련 테이블 | 주요 read/write 대상 table |
| 처리 방식 | INSERT, UPDATE, DELETE, TRUNCATE, DROP, CREATE, RENAME, SELECT INTO 등 |
| 전체 UPDATE 여부 | 특정 table 전체 또는 대량 row update 여부 |
| rename/swap 여부 | 새 table 생성 후 기존 table과 교체하는지 여부 |
| TRUNCATE/DROP/CREATE 여부 | 객체 삭제/재생성 여부 |
| SELECT INTO 여부 | SELECT INTO로 신규 table을 생성하는지 여부 |
| 파생/집계/랭킹 여부 | 원장 data가 아니라 batch 결과, 집계, 랭킹, 전시, 추천, 임시 산출물인지 여부 |
| Lock 이력 | lock wait, blocking, 장애 연관 가능성 |
| CDC 등급 | A~F 기준 |
| 권장 조치 | CDC 후보 유지, CDC 제외, chunk update, version pointer, AWS 재생성, full refresh 등 |
| 근거 | source path, hash, line, graph node |
| 상태 | Confirmed / Inferred / Needs Review |

## CDC 등급 기준

| 등급 | 유형 | 설명 | CDC 적합성 | 기본 조치 방향 |
|---|---|---|---|---|
| A | 일반 소량 변경 | 일반적인 INSERT/UPDATE/DELETE 중심이고 변경량이 작으며 PK가 명확함 | 적합 | CDC 후보 유지 |
| B | 범위성 변경 | 일정 범위 UPDATE/DELETE가 있으나 변경량과 실행 시간을 통제할 수 있음 | 조건부 적합 | chunk update, 실행시간 조정 후 CDC 검토 |
| C | 전체 UPDATE | 특정 batch가 table 전체 또는 대량 데이터를 UPDATE함 | 부적합 가능성 높음 | 전체 UPDATE 제거 또는 chunk update 전환 |
| D | rename/swap | 연산 결과 table을 만든 뒤 기존 table과 rename/swap함 | 부적합 | CDC 제외, version pointer 전환 검토 |
| E | truncate/drop/create/select into | 객체 삭제/재생성 또는 SELECT INTO 중심 구조 | 부적합 | CDC 제외, full refresh 또는 재생성 방식 검토 |
| F | 파생/집계/랭킹/임시 table | 원장 data가 아니라 batch 결과, 집계, 랭킹, 추천, 전시, 임시 산출물 | CDC 대상 아님 | AWS 재생성, full refresh, read model 후보 |

## 2주 1차 조사 우선순위

전체 DB를 한 번에 조사하지 않는다. 2주 안에 확인 가능한 범위에서 아래 순서로 1차 대상을 고른다.

1. 실행 시간이 길거나 실행 빈도가 높은 batch
2. 서비스 장애 또는 lock과 연관 가능성이 있는 batch/SP/query
3. 특정 table 전체 또는 대량 데이터를 UPDATE하는 batch
4. 연산 결과 table을 생성한 뒤 rename/swap하는 batch
5. TRUNCATE, DROP, CREATE, SELECT INTO를 사용하는 batch
6. 집계, 랭킹, 전시, 추천 등 파생 data table
7. 호출 빈도가 높은 SELECT query 또는 조회 procedure

## 분석 원칙

- CDC 등급은 DB 이관 적합성 판단이며, 도메인 소유권이나 DB 분리 readiness와 다르다.
- 원장 table과 파생/read model table을 분리해서 본다.
- D/E/F 등급은 나쁘다는 뜻이 아니라 CDC 방식이 맞지 않을 수 있다는 뜻이다.
- C 등급은 가능한 경우 chunk update, keyset pagination, version pointer로 전환 후보를 남긴다.
- lock 이력은 source만으로 확정하지 않는다. 운영 모니터링, 장애 기록, 실행 시간, wait 통계가 없으면 `Needs Review`다.
- 전체 UPDATE, rename/swap, TRUNCATE/DROP/CREATE, SELECT INTO는 발견 즉시 migration risk로 표시한다.
- 운영 DB 조사나 query 실행은 사용자 승인 없이 수행하지 않는다.
- YouTrack KB/Issue 반영은 사용자 승인 없이 수행하지 않는다.
- 분석 결과와 evidence import는 로컬 Obsidian 운영 지식 위키에 저장한다.
- 서비스 DB script에 없는 cross DB SP source mirror는 로컬 Obsidian이 아니라 대상 db-script repo의 `databases/_cross-db/{external-source}/db_script/`에 둔다.
- `missing-sp-source`, `batch-schedule-unknown`, `dirty-source`는 coverage registry와 unresolved queue가 일치해야 하며, stale/missing coverage가 있으면 완료로 보지 않는다.

## Evidence Gate

운영 evidence가 필요한 항목은 승인 전에는 실행하지 않는다. 승인 후에도 아래 기준을 통과해야 상태 전환할 수 있다.

| Kind | 상태 전환 최소 근거 |
|---|---|
| `batch-schedule-unknown` | SQL Agent job/step/schedule/run history 또는 owner-confirmed no-run evidence, lock/blocking summary, CDC action |
| `missing-sp-source` | object existence, source authority/location/hash 또는 source-unavailable owner confirmation, dependency surface, active/retire decision |
| `dirty-source` | owner decision, clean commit/PR 또는 accepted dirty baseline, regression/cleanup decision |

로컬 Obsidian 위키에서는 evidence import header/redaction과 coverage drift를 validator로 검증한다.

## 권장 조치 매핑

| 조건 | 권장 조치 |
|---|---|
| PK 명확, 소량 변경 | CDC 후보 유지 |
| 시간대 통제 가능 범위 UPDATE | chunk update, 실행시간 조정 |
| 대량/전체 UPDATE | 전체 UPDATE 제거, chunk update, version column 검토 |
| rename/swap | CDC 제외, version pointer 또는 alias/view 전환 |
| truncate/drop/create | CDC 제외, full refresh 또는 재생성 pipeline |
| SELECT INTO | 명시적 target table + batch metadata 또는 full refresh |
| 파생/집계/랭킹 | AWS에서 재생성, read model 후보 |
| lock 이력 있음 | 실행 시간 조정, batching, index/transaction 검토, 추가 분석 |

## 완료 기준

1차 조사는 다음을 만족해야 한다.

- 조사 대상별 필수 추출 필드가 채워져 있다.
- CDC 등급 A~F 중 하나가 부여되어 있다.
- `Confirmed`, `Inferred`, `Needs Review`가 구분되어 있다.
- D/E/F 등급은 CDC 제외 또는 재생성 후보로 분리되어 있다.
- C 등급은 chunk update 또는 version pointer 전환 후보가 기록되어 있다.
- source path/hash 또는 graph 근거가 있다.
- unresolved evidence import와 coverage drift validator가 통과한다.
- 로컬 위키 lint가 통과한다.
