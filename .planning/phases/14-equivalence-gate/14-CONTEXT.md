---
phase: 14
phase_name: Equivalence Gate
status: context
created: 2026-06-19
requirements:
  - VAL-01
  - VAL-02
  - VAL-03
---

# Phase 14 Context: Equivalence Gate

## Why

The project must never mark a Spring Batch output equivalent to SSIS unless structure validation, contract-format validation, and SSIS golden comparison pass. Phase 14 adds the final equivalence decision gate that combines those reports.

## Scope

- Add an equivalence gate report model.
- Evaluate `ValidationReport`, `ContractFormatValidationReport`, and `GoldenComparisonReport`.
- Return `EQUIVALENT` only when all reports pass.
- Return `BLOCKED` when golden evidence is missing or incomplete.
- Return `NOT_EQUIVALENT` when evidence exists and proves mismatch.

## Non-Scope

- No real golden output acquisition.
- No DB/SP/SQL Agent/prod access.
- No publish/readback execution.
