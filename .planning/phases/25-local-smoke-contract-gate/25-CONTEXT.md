---
phase_name: Local Smoke Contract Gate
status: complete
updated: 2026-06-19
---

# Phase 25 Context: Local Smoke Contract Gate

Phase 24 proved that the local skeleton matrix creates the expected 19 artifacts. The next useful local proof is format validation across the same matrix, because SSIS equivalence depends on file contract details before byte-level golden comparison can pass.

This phase keeps the same no-DB/no-prod boundary. It strengthens local evidence only.

## Scope

- Reuse `ContractFormatValidator` inside `LocalSmokeMatrixRunner`.
- Record contract-format report id, conclusion, passed files, and total files per target.
- Fail a runnable matrix target when contract-format validation is not `PASSED`.
- Keep `naverRankingFeedJob` as `BLOCKED_EXPECTED` without executing it.

## Out Of Scope

- Golden-output equivalence.
- Partner-facing publish.
- SQL Agent/SP/DTSX runtime evidence collection.
