# Phase 40 Plan - G1 Approval Packet

## Goal

Create a local G1 approval packet generator and command runner that turn the current readiness blockers and request bundle into one approval-facing JSON artifact.

## Steps

1. Add RED tests for generator and command runner.
2. Add `G1ApprovalPacket` model with status, blocking gates, counts, forbidden actions, and import command.
3. Add `G1ApprovalPacketGenerator`.
4. Add `G1ApprovalPacketCommandLineRunner`.
5. Generate `docs/g1-evidence/approval-packet.json`.
6. Update README, G1 import guide, migration ledger, and GSD planning ledger.
7. Run focused tests, runner smoke, G1 focused suite, and full tests.
8. Commit small local b2b change.

## Acceptance

- Approval packet status is `APPROVAL_REQUIRED` while readiness is blocked or request approval is required.
- Packet lists four current blocking gates: DTSX spec coverage, DTSX manual step plan, G1 evidence, equivalence.
- Packet records 7 fragments, 7 targets, 4 read-only query ids, and 6 forbidden actions.
- No external system is contacted.
