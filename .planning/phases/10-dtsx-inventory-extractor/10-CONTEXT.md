---
phase: 10
phase_name: DTSX Inventory Extractor
status: context
created: 2026-06-19
requirements:
  - INV-01
  - INV-02
  - INV-03
---

# Phase 10 Context: DTSX Inventory Extractor

## Why

Phase 9 created runnable Kotlin/Spring Batch skeleton jobs, but those jobs still use placeholder artifacts. The next useful local step before DB approval is to extract structured evidence from the downloaded DTSX XML files.

## Scope

- Add a read-only DTSX parser to `partner-integration-batch`.
- Extract package name, connection managers, executable/task tree, and SQL/SP command candidates.
- Generate a JSON inventory report for the priority 13-17 DTSX candidates.

## Non-Scope

- No DB/SP/SQL Agent access.
- No SSIS execution.
- No partner-facing publish/readback.
- No claim of SSIS equivalence.
