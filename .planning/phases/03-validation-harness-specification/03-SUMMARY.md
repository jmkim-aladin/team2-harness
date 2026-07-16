---
phase: 3
phase_name: Validation Harness Specification
status: executed_with_external_evidence_gate
completed: 2026-06-19
plans:
  - 03-PLAN.md
requirements:
  - VAL-01
  - VAL-02
  - VAL-03
---

# Phase 3 Summary: Validation Harness Specification

## Result

Phase 3 specified the validation harness needed to prove SSIS-to-Spring Batch equivalence later.

## Created

- `03-GOLDEN-SET.md` - golden identity, metadata, sample classes, external storage rule, G1 gate
- `03-VALIDATION-HARNESS.md` - `IntegrationValidator` runtime harness, comparator registry, fixture shape, manifest recording
- `03-SHADOW-RUN.md` - shadow safety, candidate namespace, strict thresholds, duration thresholds, entry gates

## Key Decisions Locked

- Default equivalence is exact raw byte equality.
- Real SSIS golden files stay outside git.
- Any comparator tolerance is feed-specific, approved, and recorded in manifest evidence.
- Validation is runtime architecture behind `IntegrationValidator`, not only test assertions.
- Large files must be streamed.
- Shadow uses `runPurpose=SHADOW`.
- Shadow candidate artifacts live under `candidate/...` and cannot reach partner-facing targets.
- Row 15 remains excluded until G1 confirms active SQL Agent scope.

## Not Done By Design

- No real golden outputs were collected.
- No DB/SP/SQL Agent/prod access occurred.
- No repo was created.
- No Kotlin production code was implemented.
- No shadow run was executed.
- No partner-facing publish or readback occurred.

## Next

Phase 4 can design feed jobs and contracts locally. Implementation still requires G1 evidence and repo creation approval.
