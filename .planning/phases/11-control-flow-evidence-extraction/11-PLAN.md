---
phase: 11
phase_name: Control Flow Evidence Extraction
status: planned
created: 2026-06-19
requirements:
  - INV-02
  - INV-03
---

# Phase 11 Plan: Control Flow Evidence Extraction

## Tasks

1. Inspect DTSX variable and precedence constraint XML patterns in representative packages.
2. Extend `DtsxInventory` with variables and precedence constraints.
3. Extend `DtsxInventoryParser` and tests.
4. Regenerate priority 13-17 inventory JSON into tracked docs.
5. Verify tests, counts, and raw secret absence.

## Verification

- `./gradlew test --rerun-tasks`
- `./gradlew bootRun` DTSX inventory generation to `docs/dtsx-inventory/priority-13-17-inventory.json`
- `jq` package summary over variables, precedence constraints, SQL statements
- `rg` secret/password grep over generated inventory
