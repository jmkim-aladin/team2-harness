---
phase_name: Local Smoke Matrix Runner
status: complete
updated: 2026-06-19
---

# Phase 24 Context: Local Smoke Matrix Runner

Phase 9 required local smoke coverage for 13, 14, 16, and 17 skeletons, with row 15 blocked until G1 evidence. Before this phase, each job could be launched individually, but there was no single report that proved the current local matrix.

The goal is not SSIS equivalence. The runner is local-only and requires `golden-comparison-required=false`, so it cannot be confused with golden-output proof.

## Scope

- Run `naverBookFeedJob` FULL/TODAY.
- Run `naverShoppingFeedJob` FULL/TODAY.
- Run `googleShoppingFeedJob` FULL/TODAY.
- Run `kakaoDaumFeedJob` FULL.
- Record `naverRankingFeedJob` as blocked until G1 evidence resolves row 15.
- Produce a JSON report with expected/actual artifact counts.

## Out Of Scope

- SQL Server, SQL Agent, SP, FTP, SMB, HTTP, API, or production access.
- Partner-facing publish.
- Golden-output equivalence.
- Row 15 implementation.
