---
phase: 15
phase_name: Contract Format Validation
status: context
created: 2026-06-19
requirements:
  - VAL-03
---

# Phase 15 Context: Contract Format Validation

## Why

SSIS equivalence requires more than expected file names and byte equality. Candidate artifacts must also satisfy the partner contract shape before golden comparison and final equivalence can be trusted.

## Scope

- Validate expected files for an integration/mode/businessDate.
- Check basic content format: encoding decode, newline, JSONL parse, XML well-formedness, TSV separator presence.
- Produce a JSON contract-format report.
- Require contract-format pass in the final equivalence gate.

## Non-Scope

- No real partner schema validation yet.
- No DB/SP/SQL Agent/prod access.
- No partner publish/readback.
