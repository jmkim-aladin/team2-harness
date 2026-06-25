---
phase: 11
phase_name: Control Flow Evidence Extraction
status: context
created: 2026-06-19
requirements:
  - INV-02
  - INV-03
---

# Phase 11 Context: Control Flow Evidence Extraction

## Why

Phase 10 extracted package, connection, executable, and SQL/SP candidates. To rebuild SSIS behavior as Spring Batch jobs, the migration ledger also needs file/path variables and task ordering evidence.

## Scope

- Extend the DTSX inventory parser to extract package/task variables.
- Extract precedence constraints as control-flow edges.
- Persist the priority 13-17 inventory JSON under `docs/dtsx-inventory/` so the evidence is not only a build artifact.

## Non-Scope

- No SQL Agent, DB, SP, SSIS runtime, production, or partner endpoint access.
- No Script Task source decompilation.
- No equivalence claim.
