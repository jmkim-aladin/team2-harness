---
phase: 11
phase_name: Control Flow Evidence Extraction
status: passed_local_verification
verified: 2026-06-19
requirements:
  - INV-02
  - INV-03
---

# Phase 11 Verification

## Commands Run

```bash
./gradlew test --rerun-tasks

./gradlew bootRun --args='--partner.integration.dtsx-inventory.enabled=true --partner.integration.dtsx-inventory.output=docs/dtsx-inventory/priority-13-17-inventory.json --partner.integration.dtsx-inventory.paths=/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_DaumDBFile_Make/KakaoDaum.dtsx,/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_GoogleShop_DBFile/DTS_GoogleShop_DBFile_Make_TSV_V2.dtsx,/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_GoogleShop_DBFile/DTS_GoogleShop_DBFile_Make_Today_TSV_V2.dtsx,/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_NaverDBFile/DTS_NaverDBFile_BestSellerMake.dtsx,/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_NaverDBFile/DTS_NaverDBFile_Make_V2.dtsx,/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_NaverDBFile/DTS_NaverDBFile_Make_V2_Today.dtsx,/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_NaverDBFile/DTS_NaverShopDBFile_Make.dtsx,/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_NaverDBFile/DTS_NaverShopDBFile_Make_Today.dtsx --logging.level.root=WARN'

jq 'map({packageName, variables:(.variables|length), precedenceConstraints:(.precedenceConstraints|length), sqlStatements:(.sqlStatements|length)})' docs/dtsx-inventory/priority-13-17-inventory.json

rg -n "secret|Password=[^<]|Pwd=[^<]" docs/dtsx-inventory/priority-13-17-inventory.json
```

## Result

- Tests passed: 10 test methods.
- Inventory generation succeeded.
- Tracked inventory size: 72 KB.
- Raw secret/password grep returned no matches.

## Residual Risk

- Variable and precedence extraction is structural evidence only.
- It does not prove active deployment, schedule, SP behavior, or output equivalence.
