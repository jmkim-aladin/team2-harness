---
phase_name: Rebuild Retransfer Intent Separation
status: complete
updated: 2026-06-19
requirements:
  - BATCH-02
  - BATCH-03
  - OPS-03
---

# Phase 22 Plan: Rebuild Retransfer Intent Separation

## Objective

Separate rebuild and retransfer intent so a retransfer request cannot enter artifact generation by accident.

## Tasks

1. Extend job launcher and `IntegrationJobParameters` with `forceRebuild` and `retransferArtifactId`.
2. Add validator rules for valid rebuild/retransfer combinations.
3. Persist `forceRebuild` and `retransferArtifactId` in `IntegrationRun`.
4. Add preflight guard blocking `RETRANSFER` before generation until publish-from-manifest exists.
5. Document operator intent rules.
6. Verify unit tests, rebuild smoke, retransfer guard smoke, full tests, and secret scan.

## Acceptance Criteria

- `forceRebuild=true` is accepted for non-retransfer runs.
- `runPurpose=RETRANSFER` requires `retransferArtifactId`.
- `retransferArtifactId` is rejected for non-retransfer runs.
- `forceRebuild` and `retransferArtifactId` are mutually exclusive.
- Retransfer guard produces zero artifacts and releases lock.
