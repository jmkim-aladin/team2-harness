---
phase_name: Local Smoke Contract Gate
status: complete
updated: 2026-06-19
---

# Phase 25 Plan: Local Smoke Contract Gate

## Objective

Make the local smoke matrix fail unless each runnable target passes contract-format validation after artifact generation.

## Tasks

1. Add contract-format fields to `LocalSmokeMatrixTargetResult`.
2. Add `contractFormatPassedTargetCount` to `LocalSmokeMatrixReport`.
3. Inject `ContractFormatValidator` into `LocalSmokeMatrixRunner`.
4. Resolve candidate artifact root from generated artifact storage URIs.
5. Fail runnable target when contract-format conclusion is not `PASSED`.
6. Update tests for pass/fail contract-format scenarios.
7. Run targeted tests, full tests, and actual bootRun matrix.

## Verification

- `./gradlew test --tests 'kr.co.aladin.partner.integration.batch.smoke.*' --rerun-tasks`
- `./gradlew bootRun --args='--partner.integration.local-smoke-matrix.enabled=true --partner.integration.local-smoke-matrix.business-date=2026-06-19 --partner.integration.local-smoke-matrix.output=build/local-smoke-matrix/report.json --partner.integration.golden-comparison-required=false --partner.integration.manifest-root=build/partner-integration/local-smoke-matrix/manifest --partner.integration.artifact-root=build/partner-integration/local-smoke-matrix/artifacts --logging.level.root=WARN'`
- `./gradlew test --rerun-tasks`
