---
phase_name: Local Smoke Matrix Runner
status: complete
updated: 2026-06-19
---

# Phase 24 Plan: Local Smoke Matrix Runner

## Objective

Add an executable local matrix runner that proves the current Spring Batch skeleton coverage for priority rows before G1 evidence is available.

## Tasks

1. Add `LocalSmokeMatrix` report model.
2. Add `LocalSmokeMatrixRunner` that runs the seven runnable local targets and validates artifact counts.
3. Add `LocalSmokeMatrixCommandLineRunner` gated by `--partner.integration.local-smoke-matrix.enabled=true`.
4. Require `--partner.integration.golden-comparison-required=false` for the matrix runner.
5. Record row 15 `naverRankingFeedJob` as `BLOCKED_EXPECTED`.
6. Add unit tests and actual `bootRun` verification.
7. Update README and migration ledger.

## Verification

- `./gradlew test --tests 'kr.co.aladin.partner.integration.batch.smoke.*' --rerun-tasks`
- `./gradlew test --rerun-tasks`
- `./gradlew bootRun --args='--partner.integration.local-smoke-matrix.enabled=true --partner.integration.local-smoke-matrix.business-date=2026-06-19 --partner.integration.local-smoke-matrix.output=build/local-smoke-matrix/report.json --partner.integration.golden-comparison-required=false --partner.integration.manifest-root=build/partner-integration/local-smoke-matrix/manifest --partner.integration.artifact-root=build/partner-integration/local-smoke-matrix/artifacts --logging.level.root=WARN'`
