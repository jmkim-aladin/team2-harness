---
phase: 13
phase_name: Golden Comparison Harness
status: context
created: 2026-06-19
requirements:
  - VAL-01
  - VAL-02
  - VAL-03
---

# Phase 13 Context: Golden Comparison Harness

## Why

SSIS equivalence cannot be claimed from local skeleton output. The migration needs a repeatable comparator that can prove byte/count/checksum parity between a Spring Batch candidate output and an SSIS golden output once G1 evidence is available.

## Scope

- Add a local file-based golden comparison engine.
- Compare candidate and golden files by relative path.
- Record byte count, line count, SHA-256, and file-level status.
- Produce a JSON report for audit.

## Non-Scope

- No DB/SP/SQL Agent/prod access.
- No actual SSIS golden output acquisition.
- No partner publish/readback.
- No equivalence claim.
