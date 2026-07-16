---
phase_name: G1 Fragment Template Directory Generation
status: complete
updated: 2026-06-19
requirements:
  - INV-04
  - VAL-01
  - VAL-02
  - OPS-04
---

# Phase 20 Plan: G1 Fragment Template Directory Generation

## Objective

Generate an operator-friendly G1 evidence fragment template directory from the existing template pack model.

## Tasks

1. Add fragment write report model.
2. Implement `G1EvidenceFragmentWriter`.
3. Add `G1EvidenceFragmentTemplateCommandLineRunner`.
4. Add round-trip tests through the Phase 19 importer.
5. Document template directory generation command.
6. Verify full tests, runner round-trip, and secret-pattern scan.

## Acceptance Criteria

- Writer emits all seven required fragment files.
- Writer refuses non-empty output roots unless overwrite is explicit.
- CLI supports deterministic `businessDate`, `evidencePackId`, and `capturedAt`.
- Generated template fragments import successfully but validate as `FAILED`.
- No DB/prod/network operation is introduced.
