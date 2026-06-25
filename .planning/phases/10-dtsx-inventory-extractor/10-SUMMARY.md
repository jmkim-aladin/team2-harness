---
phase: 10
phase_name: DTSX Inventory Extractor
status: implemented_local_evidence
completed: 2026-06-19
requirements:
  - INV-01
  - INV-02
  - INV-03
---

# Phase 10 Summary: DTSX Inventory Extractor

## Result

The Kotlin repo now contains a local read-only DTSX inventory extractor. It parses downloaded DTSX XML files and writes package, connection manager, executable, and SQL/SP command candidates to JSON.

## Implemented

- `DtsxInventory`
- `DtsxInventoryParser`
- `DtsxInventoryCommandLineRunner`
- `DtsxInventoryParserTest`
- README inventory command documentation

## Generated Inventory

Output:

```text
/Users/jm/Documents/workspace/b2b/partner-integration-batch/build/dtsx-inventory/priority-13-17-inventory.json
```

Package summary:

| Package | Connections | Executables | SQL candidates |
|---|---:|---:|---:|
| `KakaoDaum` | 7 | 19 | 12 |
| `DTS_GoogleShop_DBFile_Make_TSV_V2` | 4 | 7 | 4 |
| `DTS_GoogleShop_DBFile_Make_Today_TSV_V2` | 4 | 4 | 3 |
| `DTS_NaverDBFile_BestSellerMake` | 3 | 4 | 2 |
| `DTS_NaverDBFile_Make_V2` | 9 | 27 | 17 |
| `DTS_NaverDBFile_Make_V2_Today` | 3 | 6 | 4 |
| `DTS_NaverShopDBFile_Make` | 3 | 7 | 3 |
| `DTS_NaverShopDBFile_Make_Today` | 2 | 3 | 1 |

## Not Complete

- This is local repo evidence, not SQL Agent canonical evidence.
- It does not fully classify precedence constraints, variables, Script Task code, or publish/readback behavior yet.
- SSIS equivalence remains blocked until G1 evidence and golden output comparison.
