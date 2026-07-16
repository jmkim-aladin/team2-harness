---
phase: 12
phase_name: Spring Batch Spec Generation
status: planned
created: 2026-06-19
requirements:
  - BATCH-01
  - INV-02
  - INV-03
---

# Phase 12 Plan: Spring Batch Spec Generation

## Tasks

1. Add migration spec models for package evidence, steps, transitions, operation type, and Spring Batch mapping.
2. Implement a generator that topologically orders DTSX executable refs from precedence constraints.
3. Classify DTSX executable types into Spring Batch mapping candidates.
4. Add a command-line runner to generate tracked spec JSON from inventory JSON.
5. Add unit tests and generate the priority 13-17 migration spec.

## Verification

- `./gradlew test --rerun-tasks`
- `./gradlew bootRun` with `partner.integration.dtsx-spec.enabled=true`
- `jq` mapping/manual-review summary
- secret/password grep over generated spec
