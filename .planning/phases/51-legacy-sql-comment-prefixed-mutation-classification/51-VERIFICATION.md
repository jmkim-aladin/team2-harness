# Phase 51 검증 - 기존 SQL 주석 접두어 변경문 분류

## 검증 상태

완료.

## 검증 기록

- RED: `./gradlew test --tests 'kr.co.aladin.partner.integration.batch.legacy.LegacySqlCallPlanGeneratorTest'`
  - 결과: 신규 테스트 `주석 접두어 안에 변경문이 보이면 부작용 검토 대상으로 분류한다` 실패.
- GREEN: `./gradlew test --rerun-tasks --tests 'kr.co.aladin.partner.integration.batch.legacy.LegacySqlCallPlanGeneratorTest'`
  - 결과: `BUILD SUCCESSFUL`, 4개 테스트 통과.
- legacy SQL sample report 재생성:
  - `./gradlew bootRun --args='--partner.integration.legacy-sql-plan.enabled=true --partner.integration.legacy-sql-plan.spec=docs/dtsx-spec/priority-13-17-migration-spec.json --partner.integration.legacy-sql-plan.output=docs/legacy-sql/sample-report.json'`
  - 결과: `BUILD SUCCESSFUL`, `mutationSqlCount=9`, `unknownSqlCount=0`.
- readiness sample report 재생성:
  - `./gradlew bootRun --args='--partner.integration.readiness.enabled=true ... --partner.integration.readiness.output=docs/readiness/sample-report.json --partner.integration.readiness.fail-on-not-ready=false'`
  - 결과: `BUILD SUCCESSFUL`, `requiredGateCount=11`, `passedGateCount=4`, `blockedGateCount=7`, `failedGateCount=0`.
- G1 approval packet 재생성:
  - `./gradlew bootRun --args='--partner.integration.g1-approval.enabled=true --partner.integration.g1-approval.readiness-report=docs/readiness/sample-report.json --partner.integration.g1-approval.request-bundle=docs/g1-evidence/request-bundle.json --partner.integration.g1-approval.output=docs/g1-evidence/approval-packet.json'`
  - 결과: `BUILD SUCCESSFUL`, `status=APPROVAL_REQUIRED`, 차단 gate 7개.
- 공백 검사: `git diff --check`
  - 결과: 통과.
- 전체 테스트: `./gradlew test --rerun-tasks`
  - 결과: `BUILD SUCCESSFUL`.
