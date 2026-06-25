---
phase: 12
phase_name: Spring Batch Spec Generation
status: context
created: 2026-06-19
requirements:
  - BATCH-01
  - INV-02
  - INV-03
---

# Phase 12 Context: Spring Batch Spec Generation

## Why

The project needs to move from raw DTSX evidence toward a Spring Batch rebuild plan. The local inventory already captures DTSX tasks and edges; the next step is to classify those tasks into Spring Batch mapping candidates.

## Scope

- Read the generated DTSX inventory JSON.
- Produce migration spec JSON for Spring Batch Job/Flow/Tasklet/Chunk Step mapping.
- Mark Script Task, loop, and unknown executable types as manual review.
- Keep the generated spec as tracked migration evidence.

## Non-Scope

- No automatic production implementation from DTSX.
- No DB/SP/SQL Agent/prod access.
- No golden-output equivalence claim.
