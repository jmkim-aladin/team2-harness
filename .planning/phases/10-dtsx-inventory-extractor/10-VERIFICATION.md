---
phase: 10
phase_name: DTSX Inventory Extractor
status: passed_local_verification
verified: 2026-06-19
requirements:
  - INV-01
  - INV-02
  - INV-03
---

# Phase 10 Verification

## Commands Run

```bash
./gradlew test --rerun-tasks

./gradlew bootRun --args='--partner.integration.dtsx-inventory.enabled=true --partner.integration.dtsx-inventory.output=build/dtsx-inventory/priority-13-17-inventory.json --partner.integration.dtsx-inventory.paths=/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_DaumDBFile_Make/KakaoDaum.dtsx,/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_GoogleShop_DBFile/DTS_GoogleShop_DBFile_Make_TSV_V2.dtsx,/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_GoogleShop_DBFile/DTS_GoogleShop_DBFile_Make_Today_TSV_V2.dtsx,/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_NaverDBFile/DTS_NaverDBFile_BestSellerMake.dtsx,/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_NaverDBFile/DTS_NaverDBFile_Make_V2.dtsx,/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_NaverDBFile/DTS_NaverDBFile_Make_V2_Today.dtsx,/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_NaverDBFile/DTS_NaverShopDBFile_Make.dtsx,/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_NaverDBFile/DTS_NaverShopDBFile_Make_Today.dtsx --logging.level.root=WARN'

jq 'map({packageName, connections:(.connections|length), executables:(.executables|length), sqlStatements:(.sqlStatements|length)})' build/dtsx-inventory/priority-13-17-inventory.json
```

## Result

- Tests passed: 10 test methods.
- Inventory generation succeeded.
- Inventory size: 51,414 bytes.
- Raw password/secret grep returned no matches.

## Residual Risk

- Parser currently captures the fields needed for first inventory evidence only.
- Active deployed package confirmation still requires G1 read-only SQL Agent evidence.
- Script Task internals and precedence constraints still need a follow-up extractor pass if they become cutover-critical.
