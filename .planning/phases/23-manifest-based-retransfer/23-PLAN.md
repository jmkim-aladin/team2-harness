---
phase_name: Manifest Based Retransfer
status: complete
updated: 2026-06-19
requirements:
  - BATCH-03
  - OPS-01
  - OPS-03
---

# Phase 23 Plan: Manifest Based Retransfer

## Objective

Retransfer can publish an existing validated artifact from the manifest without artifact regeneration.

## Tasks

1. Extend `IntegrationManifestRepository` with artifact and validation lookup.
2. Implement lookups in file-backed and in-memory repositories.
3. Change retransfer generation step to no-op and record `RETRANSFER_PREPARED`.
4. Validate source run metadata and passed validation report before publish.
5. Publish original artifact descriptor in retransfer run.
6. Verify full tests and local retransfer success smoke.

## Acceptance Criteria

- Retransfer run creates no new artifact manifest directory.
- Retransfer source artifact must match integration/mode/businessDate/contractVersion.
- Retransfer source artifact must be included in a passed validation report.
- Publish attempt uses retransfer run id and original artifact id.
- Lock files are released after completion.
