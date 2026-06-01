# DB 이관/CDC 진단 추출 가이드

## 목적

Ralph Loop 또는 수동 분석으로 서비스 DB 리소스를 읽을 때, batch/SP/table/query의 CDC 적합성과 AWS 이관 위험을 함께 추출하기 위한 실행 가이드다.

정책 원본은 [db-migration-cdc-assessment-policy.md](../policies/db-migration-cdc-assessment-policy.md)다.

## 출력 위치

서비스별 결과는 로컬 Obsidian 운영 지식 위키에 저장한다.
문서 제목과 `title` frontmatter는 [wiki-document-language-and-title-policy.md](../policies/wiki-document-language-and-title-policy.md)를 따른다. 파일명은 `service_id` 접두어를 유지하되, H1은 `투비 ...`, `알라딘 웹 ...`처럼 한글 서비스 표시명으로 시작한다.

예시:

```text
Obsidian vault `wiki/inventory/{service}-db-migration-cdc-candidates.md`
wiki/contracts/stored-procedures/{service}/{sp}.md
wiki/contracts/tables/{service}/{table}.md
wiki/execution/{date}-{service}-cdc-assessment-pass.md
databases/_cross-db/{external-source}/db_script/{database}/StoredProcedures/{sp}.sql
```

분석 중 서비스 DB script에 없는 외부 SP가 cross DB 호출로 발견되면, 원본 DB 폴더 구조를 보존해 대상 db-script repo의 `databases/_cross-db/{external-source}/db_script/` 아래에 분석용 mirror로 복사한다. 이 mirror는 contract 작성과 dependency 추적용이며, 운영 변경 근거로 사용하지 않는다.

## 최소 표 양식

Google Sheet 또는 위키 표로 내보낼 때는 아래 컬럼을 사용한다.

| 번호 | 담당팀 | 대상명 | 유형 | 관련 테이블 | 처리 방식 | 전체 UPDATE 여부 | rename/swap 여부 | TRUNCATE/DROP/CREATE 여부 | SELECT INTO 여부 | 파생/집계/랭킹 여부 | Lock 이력 | CDC 등급 | 권장 조치 | 근거 | 상태 |
|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

## 자동 추출 힌트

source scan에서는 아래 패턴을 우선 찾는다.

| 항목 | 탐지 패턴 예시 |
|---|---|
| 전체 UPDATE | `UPDATE <table>` 후 key/range 조건이 없거나 대량 후보 |
| rename/swap | `sp_rename`, `RENAME`, `_temp`/`_bak`/`_new` 교체 |
| TRUNCATE | `TRUNCATE TABLE` |
| DROP/CREATE | `DROP TABLE`, `CREATE TABLE` |
| SELECT INTO | `SELECT ... INTO <table>` |
| 파생/집계 | `GROUP BY`, ranking/window, 추천/전시/랭킹/집계 naming |
| lock 위험 | 긴 transaction, cursor, massive update/delete, table scan 후보 |

자동 탐지는 확정이 아니다. source 기반으로 `Inferred` 또는 `Needs Review`를 남기고, 운영 실행 시간/lock 이력은 별도 확인한다.

## 도메인 문서에 추가할 섹션

도메인 또는 contract 문서에는 필요 시 아래 섹션을 추가한다.

```markdown
## DB Migration / CDC Assessment

| 대상 | 유형 | 관련 테이블 | 처리 방식 | CDC 등급 | 권장 조치 | 상태 |
|---|---|---|---|---|---|---|

## Migration Risks

- 전체 UPDATE:
- rename/swap:
- TRUNCATE/DROP/CREATE:
- SELECT INTO:
- 파생/집계/랭킹:
- Lock 이력:
```

## 등급 부여 순서

1. 원장 table인지 파생/read model table인지 구분한다.
2. INSERT/UPDATE/DELETE 범위와 key 조건을 확인한다.
3. 전체 UPDATE, rename/swap, TRUNCATE/DROP/CREATE, SELECT INTO를 먼저 찾는다.
4. batch 결과 table이면 F 등급 후보로 둔다.
5. CDC 등급과 권장 조치를 기록한다.
6. source 근거가 없으면 `Needs Review`로 둔다.

## Evidence Import Gate

운영 DB, `msdb`, DMV, Query Store, access log, private repo에서 evidence를 가져와야 하는 항목은 사용자 승인 전에는 실행하지 않는다.

승인 후에도 다음 기준을 지킨다.

- business row dump를 위키에 저장하지 않는다.
- source text는 owner 승인이 있을 때만 저장하고, 기본은 source path/hash/location을 기록한다.
- SQL Agent command/message, 연결 문자열, credential, file share, 개인정보는 redaction 후 저장한다.
- batch runtime, missing SP source, dirty source evidence는 로컬 Obsidian import template에 맞춰 저장한다.
- import file header와 unresolved coverage는 validator로 검증한다.

권장 검증:

```bash
python3 scripts/validate_unresolved_evidence_imports.py
python3 scripts/validate_unresolved_coverage.py
python3 scripts/run_all.py
```

## 다음 서비스 분석 요청 문구

```text
Ralph Loop로 {service} DB 이관/CDC 1차 진단을 같이 수행해줘.

목표:
- 전체 DB CDC 재시도가 아니라, 2주 안에 확인 가능한 우선순위 후보 선별
- batch/SP/table/query별 CDC 등급 A~F 부여
- 전체 UPDATE, rename/swap, TRUNCATE/DROP/CREATE, SELECT INTO, 파생/집계/랭킹 table, Lock 이력 후보 추출
- 결과는 로컬 Obsidian 운영 지식 위키에만 저장

산출:
- Obsidian vault `wiki/inventory/{service}-db-migration-cdc-candidates.md`
- 필요 시 contract 문서의 DB Migration / CDC Assessment 섹션 갱신
- wiki/execution/{date}-{service}-cdc-assessment-pass.md
- lint 결과와 Needs Review 큐
```
