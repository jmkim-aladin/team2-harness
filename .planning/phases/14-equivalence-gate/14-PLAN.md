---
phase: 14
phase_name: Equivalence Gate
status: planned
created: 2026-06-19
requirements:
  - VAL-01
  - VAL-02
  - VAL-03
---

# Phase 14 Plan: Equivalence Gate

## Tasks

1. Add equivalence gate report models and conclusion enum.
2. Implement gate logic over `ValidationReport`, `ContractFormatValidationReport`, and `GoldenComparisonReport`.
3. Add command-line runner for JSON report generation.
4. Add tests for equivalent, blocked missing golden, mismatch, and structure-blocked cases.
5. Generate sample equivalence report under docs.

## Verification

- `./gradlew test --rerun-tasks`
- `./gradlew bootRun` with `partner.integration.equivalence-gate.enabled=true`
- `jq` report summary
- secret/password grep over generated reports
