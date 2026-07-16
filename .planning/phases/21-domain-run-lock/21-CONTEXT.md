---
phase_name: Domain Run Lock
status: complete
updated: 2026-06-19
---

# Phase 21 Context: Domain Run Lock

SSIS replacement must prevent overlapping feed runs that can mutate shared staging tables or publish the same partner-visible contract. G1 evidence is still pending, but local Spring Batch flow can already enforce a conservative same feed/businessDate lock.

## Scope

- Define domain lock key as `integrationId + businessDate`.
- Add local file-backed atomic lock repository under manifest root.
- Add in-memory repository for focused tests.
- Acquire lock before run planning and artifact generation.
- Release lock with Spring Batch job listener after job end.

## Boundaries

- No production DB lock table or takeover policy yet.
- No DB/SP/SQL Agent/prod access.
- No commit, push, PR, YouTrack, or KB update.
