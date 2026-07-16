---
phase: 13
phase_name: Golden Comparison Harness
status: planned
created: 2026-06-19
requirements:
  - VAL-01
  - VAL-02
  - VAL-03
---

# Phase 13 Plan: Golden Comparison Harness

## Tasks

1. Add golden comparison report models.
2. Implement candidate-vs-golden file comparator.
3. Add command-line runner for report generation.
4. Add unit tests for match, missing golden, and checksum mismatch.
5. Generate a sample report under docs.

## Verification

- `./gradlew test --rerun-tasks`
- `./gradlew bootRun` with `partner.integration.golden-compare.enabled=true`
- `jq` report summary
- secret/password grep over generated report
