# Phase 52 검증 - 기존 SQL 보고서 메시지 한글화

## 검증 상태

완료.

## 검증 기록

- RED: `./gradlew test --rerun-tasks --tests 'kr.co.aladin.partner.integration.batch.legacy.LegacySqlCallPlanGeneratorTest'`
  - 결과: 한글 메시지 기대값에서 4개 테스트 실패.
- GREEN: `./gradlew test --rerun-tasks --tests 'kr.co.aladin.partner.integration.batch.legacy.LegacySqlCallPlanGeneratorTest'`
  - 결과: `BUILD SUCCESSFUL`, 4개 테스트 통과.
- legacy focused suite: `./gradlew test --rerun-tasks --tests 'kr.co.aladin.partner.integration.batch.legacy.*'`
  - 결과: `BUILD SUCCESSFUL`, 5개 테스트 통과.
- legacy SQL runner:
  - `./gradlew bootRun --args='--partner.integration.legacy-sql-plan.enabled=true --partner.integration.legacy-sql-plan.spec=docs/dtsx-spec/priority-13-17-migration-spec.json --partner.integration.legacy-sql-plan.output=docs/legacy-sql/sample-report.json'`
  - 결과: `BUILD SUCCESSFUL`.
- 오래된 영문 메시지 검색:
  - `rg -n "Map stored procedure|SELECT SQL must|Mutation SQL requires|SQL is not a stored" src/main/kotlin src/test/kotlin docs/legacy-sql/sample-report.json`
  - 결과: 검색 결과 없음.
- 카운트 확인:
  - `sqlCandidateCount=46`, `procedureCallCount=34`, `unresolvedSqlCount=12`, `selectSqlCount=3`, `mutationSqlCount=9`, `unknownSqlCount=0`.
- 공백 검사: `git diff --check`
  - 결과: 통과.
- 전체 테스트: `./gradlew test --rerun-tasks`
  - 결과: `BUILD SUCCESSFUL`.
