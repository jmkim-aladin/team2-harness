---
phase: 15
phase_name: Contract Format Validation
status: passed_local_verification
verified: 2026-06-19
requirements:
  - VAL-03
---

# Phase 15 Verification

## Commands Run

```bash
./gradlew test --rerun-tasks

./gradlew bootRun --args='--partner.integration.contract-format.enabled=true --partner.integration.contract-format.candidate-root=build/contract-format-sample/naver-book-today --partner.integration.contract-format.integration-id=NAVER_BOOK --partner.integration.contract-format.mode=TODAY --partner.integration.contract-format.business-date=2026-06-19 --partner.integration.contract-format.output=docs/contract-format/sample-report.json --logging.level.root=WARN'

./gradlew bootRun --args='--partner.integration.equivalence-gate.enabled=true --partner.integration.equivalence-gate.validation-report=docs/equivalence/sample-validation-report.json --partner.integration.equivalence-gate.contract-format-report=docs/contract-format/sample-report.json --partner.integration.equivalence-gate.golden-report=docs/golden-comparison/sample-report.json --partner.integration.equivalence-gate.output=docs/equivalence/sample-equivalence-report.json --logging.level.root=WARN'

jq '{conclusion,totalFiles,passedFiles,failedFiles, results:(.results|map({fileName,status,messages}))}' docs/contract-format/sample-report.json

jq '{conclusion,validationConclusion,contractFormatConclusion,goldenComparisonConclusion,blockingReasons}' docs/equivalence/sample-equivalence-report.json
```

## Result

- Tests passed: 24 test methods.
- Contract-format sample report conclusion: `PASSED`.
- Equivalence sample report conclusion: `BLOCKED`.
- Secret/password grep returned no matches.

## Residual Risk

- Contract-format checks are still basic. Partner-specific field schemas and sort/order rules need G1 evidence.
