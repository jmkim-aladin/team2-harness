---
phase: 16
phase_name: G1 Evidence Pack Validation
status: planned
created: 2026-06-19
requirements:
  - INV-04
  - VAL-01
  - VAL-02
  - OPS-04
---

# Phase 16 Plan: G1 Evidence Pack Validation

## Tasks

1. Add G1 evidence pack models.
2. Implement validator over required feed/mode targets.
3. Add CLI runner for JSON report generation.
4. Add tests for read-only pass, synthetic blocked, and missing golden outputs.
5. Add sample evidence pack and sample validation report.

## Verification

- `./gradlew test --rerun-tasks`
- `./gradlew bootRun` with `partner.integration.g1-evidence.enabled=true`
- `jq` sample report summary
- raw password grep over sample pack/report
