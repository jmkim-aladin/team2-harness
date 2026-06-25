# Phase 50 검증: G1 operator preflight readiness gate

## 검증 명령

```bash
./gradlew test --tests 'kr.co.aladin.partner.integration.batch.readiness.MigrationReadinessEvaluatorTest'
```

결과: 통과

```bash
./gradlew test --tests 'kr.co.aladin.partner.integration.batch.readiness.MigrationReadinessCommandLineRunnerTest'
```

결과: 통과

```bash
./gradlew test --tests 'kr.co.aladin.partner.integration.batch.readiness.*'
```

결과: 통과

```bash
./gradlew bootRun --args='--partner.integration.readiness.enabled=true ... --partner.integration.readiness.g1-operator-preflight-report=build/g1-evidence/local-dtsx-candidates-preflight-report.json ... --partner.integration.readiness.output=docs/readiness/sample-report.json --partner.integration.readiness.fail-on-not-ready=false'
```

결과: `requiredGateCount=11`, `passedGateCount=4`, `blockedGateCount=7`, `G1_OPERATOR_PREFLIGHT=BLOCKED_LOCAL_REPO_CANDIDATE`

```bash
./gradlew bootRun --args='--partner.integration.g1-approval.enabled=true --partner.integration.g1-approval.readiness-report=docs/readiness/sample-report.json --partner.integration.g1-approval.request-bundle=docs/g1-evidence/request-bundle.json --partner.integration.g1-approval.output=docs/g1-evidence/approval-packet.json'
```

결과: approval packet blocking gate 7개

## 추가 검증

- `git diff --check`: 통과
- full `./gradlew test --rerun-tasks`: `BUILD SUCCESSFUL in 6s`

## 커밋

- `e904cb9 [ssis-kotlin-batch-migration] Gate readiness on G1 preflight`
