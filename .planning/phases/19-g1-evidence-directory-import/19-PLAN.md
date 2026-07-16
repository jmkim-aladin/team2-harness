---
phase_name: G1 Evidence Directory Import
status: complete
updated: 2026-06-19
requirements:
  - INV-04
  - VAL-01
  - VAL-02
  - OPS-04
---

# Phase 19 Plan: G1 Evidence Directory Import

## Objective

Operator read-only export fragments can be imported into a single G1 evidence pack and validated with the existing G1 gate.

## Tasks

1. Define import metadata/report models.
2. Implement directory importer with required fragment preflight.
3. Add command-line runner behind `partner.integration.g1-import.enabled`.
4. Add focused tests for complete import, missing fragment failure, and fail-on-non-passed validation.
5. Document required fragment filenames and local-only command usage.
6. Verify full test suite, sample import runner, and secret-pattern scan.

## Acceptance Criteria

- Missing fragment fails before pack write.
- Complete valid fragments validate as `PASSED`.
- Template fragments import successfully but validation remains `FAILED`.
- Runtime reports are generated under `build/g1-evidence/`.
- No DB/prod/network operation is introduced.
