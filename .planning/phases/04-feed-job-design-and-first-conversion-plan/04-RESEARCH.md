---
phase: 4
phase_name: Feed Job Design And First Conversion Plan
status: research_complete
created: 2026-06-19
source: multi_agent_v1 explorers and local DTSX inspection
---

# Phase 4 Research: Feed Job Design And First Conversion Plan

## RESEARCH COMPLETE

## Cross-Feed Decisions

- Use stable jobs: `naverBookFeedJob`, `naverShoppingFeedJob`, `googleShoppingFeedJob`, `kakaoDaumFeedJob`, `feedRetentionJob`.
- Use `mode=FULL|TODAY`, not separate job names, unless later schedule isolation proves necessary.
- Add identifying `scheduleSlot` or `windowKey` when the same integration/mode/businessDate can run more than once.
- Publish only after validation and manifest recording.
- `ContractOutputSpec` owns format, artifact names, encoding, delimiter, newline, sort, and target alias.

## Naver

### `naverBookFeedJob`

Candidates:

- `DTS_NaverDBFile_Make_V2.dtsx`
- `DTS_NaverDBFile_Make_V2_Today.dtsx`

Full mode likely includes staging, bestseller JSONL, relative JSONL, product `.jsonl.js`, author intro, and sales calculation. Today mode generates `product_aladdin_today.jsonl.js`.

Unknowns:

- active SQL Agent package
- SP schema/order for `Naver_*`
- whether `.jsonl.js` is wrapped JavaScript or plain JSONL with `.js` extension
- whether bestseller/relative artifacts are partner-visible or internal

### `naverShoppingFeedJob`

Candidates:

- `DTS_NaverShopDBFile_Make.dtsx`
- `DTS_NaverShopDBFile_Make_Today.dtsx`

Full mode likely generates `product_aladin.txt` and `sales_aladin.txt`. Today mode generates `product_aladin_today.txt`.

Unknowns:

- exact TXT encoding
- header/body schema from SP result sets
- whether sales artifact should be same integration or separate artifact target
- retention safety around existing delete behavior

### `naverRankingFeedJob`

Blocked. Candidate evidence conflicts:

- `DTS_NaverDBFile_BestSellerMake.dtsx` writes dated bestseller text and has a validation-needed annotation.
- `DTS_NaverDBFile_Make_V2.dtsx` includes bestseller flow that may belong to Naver book.
- `naver.dtsx` appears to be old product feed, not ranking.
- `product_aladdin_unicode.txt` may be an intermediate for `.jsonl.js`.

## Google

Candidates:

- `DTS_GoogleShop_DBFile_Make_TSV_V2.dtsx`
- `DTS_GoogleShop_DBFile_Make_Today_TSV_V2.dtsx`

Full mode:

- truncate `GoogleShopProduct_V2`
- stage `GoogleShop_Product_TargetItems_Get_V2`
- prune adult/negative-price exceptions
- delete old Google v2 files
- generate five TSV files using `GoogleShop_Product_Get_V2 @isToday=0, @groupId=1..5`

Today mode:

- run `GoogleShop_Product_TargetItems_Today_Make_V2`
- prune adult items
- generate `product_aladin_today.txt` using `GoogleShop_Product_Get_V2 @isToday=1, @groupId=0`

Unknowns:

- actual partition rule behind `@groupId`
- header policy
- encoding/codepage details
- same-day schedule slots
- UNC vs FTP published target mapping

## Kakao/Daum

Candidates:

- `KakaoDaum.dtsx`
- `DTS_DaumDBFile_OldDataDelete.dtsx`
- exclude `wonderwmp.dtsx`

Six XML outputs:

| Order | Output | SP | Encoding evidence |
|---:|---|---|---|
| 1 | `yyyyMMdd000000_selling.xml` | `KakaoDaum_Book_Selling @IsEBook=0` | CP949/MS949 |
| 2 | `yyyyMMdd000000_ebook_selling.xml` | `KakaoDaum_Book_Selling @IsEBook=1` | CP949/MS949 |
| 3 | `yyyyMMdd000000_event.xml` | `KakaoDaum_Book_Event @IsEBook=0` | UTF-8 |
| 4 | `yyyyMMdd000000_ebook_event.xml` | `KakaoDaum_Book_Event @IsEBook=1` | UTF-8 |
| 5 | `yyyyMMdd000000_eventbook.xml` | `KakaoDaum_Book_EventBook @IsEBook=0` | CP949/MS949 |
| 6 | `yyyyMMdd000000_ebook_eventbook.xml` | `KakaoDaum_Book_EventBook @IsEBook=1` | CP949/MS949 |

The enabled path appears to be the direct-write `* New` chain; do not recreate the disabled temp-file copy-script path.

Recommendation: choose `kakaoDaumFeedJob` as the first vertical slice after G1/repo approval because it has the clearest local output mapping.
