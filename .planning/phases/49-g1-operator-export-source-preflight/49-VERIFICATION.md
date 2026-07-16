# Phase 49 검증: G1 operator export source preflight

## 검증 명령

```bash
./gradlew test --tests 'kr.co.aladin.partner.integration.batch.g1.G1OperatorExportPreflightCheckerTest'
```

결과: 통과

```bash
./gradlew test --tests 'kr.co.aladin.partner.integration.batch.g1.G1OperatorExportPreflightCommandLineRunnerTest'
```

결과: 통과

```bash
./gradlew bootRun --args='--partner.integration.g1-operator-preflight.enabled=true --partner.integration.g1-operator-preflight.source-root=build/g1-evidence/fragment-template-cli --partner.integration.g1-operator-preflight.report=build/g1-evidence/fragment-template-cli-preflight-report.json'
```

결과: `BLOCKED_TEMPLATE_PLACEHOLDER`

```bash
./gradlew bootRun --args='--partner.integration.g1-operator-preflight.enabled=true --partner.integration.g1-operator-preflight.source-root=build/g1-evidence/local-dtsx-candidates --partner.integration.g1-operator-preflight.report=build/g1-evidence/local-dtsx-candidates-preflight-report.json'
```

결과: `BLOCKED_LOCAL_REPO_CANDIDATE`

## 추가 검증

- G1 focused suite: 통과
- `git diff --check`: 통과
- full `./gradlew test --rerun-tasks`: `BUILD SUCCESSFUL in 9s`

## 커밋

- `bff0068 [ssis-kotlin-batch-migration] Add G1 export preflight`
