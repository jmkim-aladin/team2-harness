# Phase 51 맥락 - 기존 SQL 주석 접두어 변경문 분류

## 배경

`docs/legacy-sql/sample-report.json`의 미해결 SQL 후보 중 3개가 `UNKNOWN`으로 남아 있었다. 해당 후보들은 실제 DTSX preview가 `--- 19금 상품 삭제 Delete ...`처럼 한 줄 주석 접두어 안에 `Delete` 키워드를 포함하는 형태였다.

기존 분류기는 선행 `--` 주석을 제거한 뒤 남은 SQL만 검사했다. 줄바꿈 없이 주석 접두어와 변경문이 같은 preview 문자열에 들어오면 전체 문자열이 주석으로 제거되어 변경 SQL을 `UNKNOWN`으로 분류했다.

## 목표

- DTSX preview가 주석 접두어로 시작해도 변경 키워드가 보이면 `DATA_MUTATION`으로 분류한다.
- SELECT 분류는 기존처럼 정규화된 SQL에서만 판단해 주석 설명문이 SELECT로 오인되지 않게 한다.
- 실제 legacy SQL sample report의 `unknownSqlCount`를 3에서 0으로 낮춘다.

## 범위

- 로컬 분류 로직과 테스트
- 커밋된 legacy SQL sample report
- readiness sample report와 G1 approval packet 재생성
- README와 migration ledger의 카운트 정합성 갱신

## 제외

- SQL 실행 또는 DB 접속
- `LegacyDbAdapter` 실제 DB wiring
- 미해결 SQL 후보 해소 주장
- SSIS 동등성 주장
