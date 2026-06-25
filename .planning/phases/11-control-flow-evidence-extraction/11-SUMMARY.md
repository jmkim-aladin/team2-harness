---
phase: 11
phase_name: Control Flow Evidence Extraction
status: implemented_local_evidence
completed: 2026-06-19
requirements:
  - INV-02
  - INV-03
---

# Phase 11 Summary: Control Flow Evidence Extraction

## Result

The DTSX inventory now includes variables and precedence constraints. This moves the migration evidence closer to an SSIS control-flow specification that can be mapped to Spring Batch steps and transitions.

## Implemented

- `DtsxVariable`
- `DtsxPrecedenceConstraint`
- variable extraction with value masking
- precedence constraint extraction with `from`, `to`, `logicalAnd`
- test coverage for variables and precedence constraints
- tracked inventory JSON:

```text
/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/dtsx-inventory/priority-13-17-inventory.json
```

## Package Summary

| Package | Variables | Precedence constraints | SQL candidates |
|---|---:|---:|---:|
| `KakaoDaum` | 7 | 16 | 12 |
| `DTS_GoogleShop_DBFile_Make_TSV_V2` | 1 | 4 | 4 |
| `DTS_GoogleShop_DBFile_Make_Today_TSV_V2` | 2 | 2 | 3 |
| `DTS_NaverDBFile_BestSellerMake` | 1 | 2 | 2 |
| `DTS_NaverDBFile_Make_V2` | 5 | 19 | 17 |
| `DTS_NaverDBFile_Make_V2_Today` | 2 | 4 | 4 |
| `DTS_NaverShopDBFile_Make` | 3 | 5 | 3 |
| `DTS_NaverShopDBFile_Make_Today` | 2 | 1 | 1 |

## Not Complete

- SQL Agent canonical package confirmation remains blocked by G1.
- Script Task source and publish/readback side effects are not fully classified yet.
- SSIS equivalence remains blocked until golden output comparison.
