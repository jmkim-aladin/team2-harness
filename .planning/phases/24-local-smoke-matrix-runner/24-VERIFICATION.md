---
phase_name: Local Smoke Matrix Runner
status: passed
updated: 2026-06-19
---

# Phase 24 Verification: Local Smoke Matrix Runner

## Commands

```bash
./gradlew test --tests 'kr.co.aladin.partner.integration.batch.smoke.*' --rerun-tasks
```

Result: passed, 4 smoke tests.

```bash
./gradlew bootRun --args='--partner.integration.local-smoke-matrix.enabled=true --partner.integration.local-smoke-matrix.business-date=2026-06-19 --partner.integration.local-smoke-matrix.output=build/local-smoke-matrix/report.json --partner.integration.golden-comparison-required=false --partner.integration.manifest-root=build/partner-integration/local-smoke-matrix/manifest --partner.integration.artifact-root=build/partner-integration/local-smoke-matrix/artifacts --logging.level.root=WARN'
```

Result: passed, report written to `build/local-smoke-matrix/report.json`.

```bash
jq '{conclusion,runnableTargetCount,blockedTargetCount,expectedArtifactCount,actualArtifactCount}' build/local-smoke-matrix/report.json
```

Observed:

```json
{
  "conclusion": "PASSED",
  "runnableTargetCount": 7,
  "blockedTargetCount": 1,
  "expectedArtifactCount": 19,
  "actualArtifactCount": 19
}
```

```bash
./gradlew test --rerun-tasks
```

Result: passed, 61 tests.

## Requirement Check

| Requirement | Status | Evidence |
|---|---|---|
| FEED-01..05 | Local skeleton matrix complete | 7 runnable targets pass and row 15 is blocked expected |
| VAL-04 | Local shadow smoke strengthened | report captures run/artifact count and blocked target |

## Residual Risk

- Real SSIS equivalence still requires G1 read-only evidence and golden output comparison.
- Row 15 remains blocked until active package/scope is confirmed.
