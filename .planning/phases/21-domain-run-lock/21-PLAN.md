---
phase_name: Domain Run Lock
status: complete
updated: 2026-06-19
requirements:
  - OPS-01
  - OPS-02
---

# Phase 21 Plan: Domain Run Lock

## Objective

Prevent concurrent runs for the same integration and business date before artifact generation.

## Tasks

1. Add lock key, lock model, repository interface, and duplicate lock exception.
2. Implement file-backed atomic lock repository and in-memory test repository.
3. Add Spring Batch listener to release locks after job termination.
4. Insert acquire lock step before `planRun`.
5. Record `LOCK_ACQUIRED` manifest event.
6. Verify repository tests, listener test, local job smoke, full tests, secret scan, and lock cleanup.

## Acceptance Criteria

- Same `integrationId + businessDate` cannot be acquired twice.
- Same feed FULL/TODAY for one date conflicts conservatively.
- Wrong owner cannot release a lock.
- Successful local job leaves zero lock files.
- Production lock store remains an explicit G2 decision.
