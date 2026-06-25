---
phase: 16
phase_name: G1 Evidence Pack Validation
status: context
created: 2026-06-19
requirements:
  - INV-04
  - VAL-01
  - VAL-02
  - OPS-04
---

# Phase 16 Context: G1 Evidence Pack Validation

## Why

G1 approval will produce several pieces of read-only evidence: SQL Agent active job/step/schedule, deployed DTSX, SP definitions, golden outputs, publish/readback target, and runtime/network evidence. The project needs a strict offline pack validator so partial evidence cannot be treated as sufficient.

## Scope

- Define a G1 evidence pack JSON model.
- Validate required target coverage for runnable feeds.
- Require read-only export source type for pass.
- Require SQL Agent, deployed DTSX, SP definitions, golden files, publish/readback target, and runtime evidence.
- Generate a sample pack/report that remains blocked because it is synthetic.

## Non-Scope

- No DB/SP/SQL Agent/prod access.
- No real evidence collection.
- No production schedule or publish change.
