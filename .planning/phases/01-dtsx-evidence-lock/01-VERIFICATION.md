---
phase: 1
phase_name: DTSX Evidence Lock
status: passed_with_external_evidence_gate
verified: 2026-06-19
requirements:
  - INV-01
  - INV-02
  - INV-03
  - INV-04
---

# Phase 1 Verification

## Verification Result

Local Phase 1 verification passed for the ledger, stack baseline, DTSX candidate list, and approval-required evidence table.

External production evidence is intentionally not verified in this phase because team2 policy requires explicit approval before DB/SP/prod access. This is recorded as Decision Gate G1, not silently assumed.

## Checks Run

```bash
test -f .planning/LEDGER.md
test -f .planning/phases/01-dtsx-evidence-lock/01-CONTEXT.md
test -f .planning/phases/01-dtsx-evidence-lock/01-RESEARCH.md
test -f .planning/phases/01-dtsx-evidence-lock/01-PLAN.md
rg -n "Kotlin \\+ Spring Boot 4\\.1\\.x \\+ Spring Batch 6\\.0\\.x|Kotlin 2\\.2\\+" .planning
rg -n "DTS_NaverDBFile_Make_V2\\.dtsx|DTS_NaverShopDBFile_Make\\.dtsx|DTS_GoogleShop_DBFile_Make_TSV_V2\\.dtsx|KakaoDaum\\.dtsx" .planning/LEDGER.md
rg -n "SQL Agent|SP definition|golden files|Missing|Required" .planning/LEDGER.md
```

## Acceptance Matrix

| Acceptance | Status | Evidence |
|---|---|---|
| `.planning/LEDGER.md` exists | Passed | File exists. |
| Excel physical rows 15-19 map to 업무 번호 13-17 | Passed | Ledger target mapping table. |
| DTSX candidates are listed | Passed | Ledger target mapping table and phase research. |
| Row 15 is blocked or scope ambiguous | Passed | Ledger canonical status: `Blocked: scope 모호`. |
| Operation classification exists | Passed | Ledger `DTSX Operation Classification`. |
| Required evidence table exists | Passed | Ledger `Required Evidence`. |
| Each required evidence row is Missing/Required | Passed | Ledger required evidence table. |
| Kotlin/Spring baseline is locked | Passed | PROJECT, STATE, STACK, and phase research. |

## Residual Risk

- Local DTSX candidates may drift from deployed operational DTSX.
- SQL Agent may use a package variant not currently inferred from local repo names.
- SP side effects, ordering, encoding, and output differences cannot be verified without read-only DB/SP and golden-output evidence.

## Gate

G1 approval is required before claiming canonical operational equivalence or starting implementation against production behavior.
