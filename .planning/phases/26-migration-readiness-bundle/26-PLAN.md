# Phase 26 Plan: Migration Readiness Bundle

## Objective

Create an offline migration readiness report that prevents local skeleton success from being confused with SSIS equivalence.

## Tasks

1. Add readiness report model and evaluator.
2. Add Spring `ApplicationRunner` CLI:
   - `--partner.integration.readiness.enabled=true`
   - input report paths for local smoke, G1 evidence, equivalence, local publish/readback
   - output path under `build/migration-readiness/report.json`
3. Add tests for:
   - missing evidence blocks readiness
   - all gates passed returns `READY_FOR_SHADOW_RUN`
   - failed equivalence returns `NOT_EQUIVALENT`
   - CLI writes blocked report when fail flag is disabled
4. Document command and sample report path.

## Verification

- `./gradlew test --tests 'kr.co.aladin.partner.integration.batch.readiness.*' --rerun-tasks`
- readiness `bootRun` with current local smoke and sample reports
- full `./gradlew test --rerun-tasks`
