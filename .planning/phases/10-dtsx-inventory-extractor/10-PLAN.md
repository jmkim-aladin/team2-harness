---
phase: 10
phase_name: DTSX Inventory Extractor
status: planned
created: 2026-06-19
requirements:
  - INV-01
  - INV-02
  - INV-03
---

# Phase 10 Plan: DTSX Inventory Extractor

## Tasks

1. Inspect representative DTSX XML structure for connection managers, executables, Execute SQL Task, and pipeline `SqlCommand`.
2. Implement a Kotlin read-only parser using standard XML APIs.
3. Add a Spring command-line runner gated by `--partner.integration.dtsx-inventory.enabled=true`.
4. Add parser tests with password masking coverage.
5. Generate the priority 13-17 inventory report and verify package/task/SQL counts.

## Verification

- `./gradlew test`
- `./gradlew bootRun` with inventory arguments against local DTSX files
- Check that generated inventory does not retain raw connection password values.
