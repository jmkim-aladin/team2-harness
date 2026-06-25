# Phase 52 요약 - 기존 SQL 보고서 메시지 한글화

## 결과

완료.

`LegacySqlCallPlanGenerator`의 사용자 노출 메시지를 한글로 바꿨다. 저장 프로시저, SELECT SQL, 변경 SQL, 알 수 없는 SQL 분기 모두 한글 메시지를 생성한다. enum, status, CLI option, `LegacyDbAdapter` 경계명은 실행 계약이므로 유지했다.

`docs/legacy-sql/sample-report.json`을 재생성했고, 기존 영문 메시지는 남지 않는다. 카운트는 SQL 46, SP 34, 미해결 12, SELECT 3, 변경 9, 알 수 없음 0을 유지한다.

## 변경 파일

- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/legacy/LegacySqlCallPlan.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/legacy/LegacySqlCallPlanGeneratorTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/legacy-sql/sample-report.json`

## 남은 범위

- readiness report 메시지 한글화는 다음 phase 후보로 남긴다.

## 커밋

- b2b repo: `0e04d55 [ssis-kotlin-batch-migration] Localize legacy SQL report messages`
