# Phase 50 계획: G1 operator preflight readiness gate

## 작업

1. readiness evaluator 테스트에 `G1_OPERATOR_PREFLIGHT` 누락/차단/통과 조건을 추가한다.
2. `MigrationReadinessGate`에 `G1_OPERATOR_PREFLIGHT`를 추가한다.
3. `MigrationReadinessEvaluator`가 preflight report를 필수 gate로 평가하게 한다.
4. `MigrationReadinessCommandLineRunner`가 `--partner.integration.readiness.g1-operator-preflight-report`를 읽게 한다.
5. `docs/readiness/sample-report.json`과 `docs/g1-evidence/approval-packet.json`을 재생성한다.
6. README와 migration ledger를 11 gates/7 blocking gates 기준으로 갱신한다.

## 검증

- focused readiness tests
- 실제 readiness runner
- approval packet regeneration
- `git diff --check`
- full `./gradlew test --rerun-tasks`
