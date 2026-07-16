# Phase 51 계획 - 기존 SQL 주석 접두어 변경문 분류

## 계획

1. 실패 테스트 추가
   - `--- 19금 상품 삭제 Delete ...` 형태의 SQL preview가 `DATA_MUTATION`으로 분류되어야 한다.
   - 검증: focused legacy test가 먼저 실패해야 한다.

2. 최소 구현
   - 주석 제거 후 문자열이 비어도 원문에 변경 키워드가 있으면 보수적으로 `DATA_MUTATION`으로 분류한다.
   - SELECT는 정규화된 SQL에 대해서만 유지한다.
   - 검증: focused legacy test 통과.

3. 산출물 재생성
   - `docs/legacy-sql/sample-report.json`
   - `docs/readiness/sample-report.json`
   - `docs/g1-evidence/approval-packet.json`
   - 검증: legacy SQL report가 `mutationSqlCount=9`, `unknownSqlCount=0`을 기록한다.

4. 문서 정합성 갱신
   - README 기존 SQL 요약
   - migration ledger 기존 SQL 섹션
   - 검증: 오래된 `mutation 6 / unknown 3` 표현이 남지 않는다.

5. 전체 검증과 커밋
   - `git diff --check`
   - focused legacy test
   - legacy SQL runner
   - readiness runner
   - approval packet runner
   - full Gradle test
   - 로컬 커밋

## 성공 기준

- 주석 접두어 안에 변경 키워드가 있는 SQL preview가 `DATA_MUTATION`으로 분류된다.
- 기존 저장 프로시저/SELECT/일반 변경 SQL 분류가 유지된다.
- legacy SQL sample report는 SQL 후보 46개, SP 후보 34개, 미해결 SQL 후보 12개, SELECT 3개, 변경 SQL 9개, 알 수 없음 0개를 기록한다.
- readiness는 계속 `BLOCKED`지만 blocker 설명은 최신 legacy SQL report를 반영한다.
- G1 approval packet은 blocking gate 7개를 유지한다.
