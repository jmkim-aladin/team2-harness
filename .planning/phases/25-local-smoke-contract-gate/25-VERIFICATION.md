---
phase_name: Local Smoke Contract Gate
status: passed
updated: 2026-06-19
---

# Phase 25 Verification: Local Smoke Contract Gate

## Commands

```bash
./gradlew test --tests 'kr.co.aladin.partner.integration.batch.smoke.*' --rerun-tasks
```

Result: passed, 5 smoke tests.

```bash
./gradlew bootRun --args='--partner.integration.local-smoke-matrix.enabled=true --partner.integration.local-smoke-matrix.business-date=2026-06-19 --partner.integration.local-smoke-matrix.output=build/local-smoke-matrix/report.json --partner.integration.golden-comparison-required=false --partner.integration.manifest-root=build/partner-integration/local-smoke-matrix/manifest --partner.integration.artifact-root=build/partner-integration/local-smoke-matrix/artifacts --logging.level.root=WARN'
```

Result: passed, report written to `build/local-smoke-matrix/report.json`.

```bash
jq '{conclusion,runnableTargetCount,blockedTargetCount,expectedArtifactCount,actualArtifactCount,contractFormatPassedTargetCount}' build/local-smoke-matrix/report.json
```

Observed:

```json
{
  "conclusion": "PASSED",
  "runnableTargetCount": 7,
  "blockedTargetCount": 1,
  "expectedArtifactCount": 19,
  "actualArtifactCount": 19,
  "contractFormatPassedTargetCount": 7
}
```

```bash
./gradlew test --rerun-tasks
```

Result: passed, 62 tests.

## Requirement Check

| Requirement | Status | Evidence |
|---|---|---|
| VAL-03 | Local matrix now includes contract-format validation | 7/7 runnable targets have `contractFormatConclusion=PASSED` |
| VAL-04 | Local shadow smoke strengthened | matrix gates on artifact count and format validation |

## Residual Risk

- Byte-level equivalence still requires SSIS golden outputs.
- G1 evidence is still missing.
