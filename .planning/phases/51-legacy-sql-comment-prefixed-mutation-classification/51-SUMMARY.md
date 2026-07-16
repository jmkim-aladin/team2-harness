# Phase 51 요약 - 기존 SQL 주석 접두어 변경문 분류

## 결과

완료.

`LegacySqlCallPlanGenerator`가 주석 접두어 제거 후 비어 버린 SQL preview라도 원문에 변경 키워드가 있으면 보수적으로 `DATA_MUTATION`으로 분류하도록 수정했다. SELECT 분류는 정규화된 SQL에 대해서만 유지해 주석 설명문이 SELECT로 오인되지 않게 했다.

legacy SQL sample report는 SQL 후보 46개, SP 후보 34개, 미해결 SQL 후보 12개, SELECT 3개, 변경 SQL 9개, 알 수 없음 0개를 기록한다. readiness sample은 11개 gate 중 4개 통과, 7개 차단으로 계속 `BLOCKED`이며, G1 approval packet은 차단 gate 7개를 유지한다.

## 변경 파일

- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/legacy/LegacySqlCallPlan.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/legacy/LegacySqlCallPlanGeneratorTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/legacy-sql/sample-report.json`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/readiness/sample-report.json`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/g1-evidence/approval-packet.json`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/README.md`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/migration-ledger.md`

## 남은 차단

- 실제 operator `READ_ONLY_EXPORT` fragment source-root가 필요하다.
- 미해결 SQL 12개는 여전히 `LegacyDbAdapter` 수동 검토 대상이다.

## 커밋

- b2b repo: `bca0d99 [ssis-kotlin-batch-migration] Classify commented SQL mutations`
