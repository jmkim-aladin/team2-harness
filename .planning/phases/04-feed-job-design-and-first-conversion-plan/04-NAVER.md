---
phase: 4
phase_name: Feed Job Design And First Conversion Plan
artifact: naver
status: drafted
created: 2026-06-19
requirements:
  - FEED-01
  - FEED-02
  - FEED-03
---

# Phase 4 Naver Feed Design

## Common Parameters

- `integrationId`
- `mode=FULL|TODAY`
- `businessDate`
- `contractVersion=v1`
- `runPurpose=PRODUCTION|SHADOW|RETRANSFER`
- optional `scheduleSlot` or `windowKey` if SQL Agent evidence shows same-day repeated runs

## `naverBookFeedJob`

Candidate DTSX:

- `DTS_NaverDBFile_Make_V2.dtsx`
- `DTS_NaverDBFile_Make_V2_Today.dtsx`

### FULL Mode

Likely steps:

1. `validateParameters`
2. `acquireIntegrationLock`
3. `prepareNaverProductV2Snapshot`
4. `prepareAuthorIntro`
5. `generateNaverBookBestsellerJsonl`
6. `generateNaverBookRelativeJsonl`
7. `runNaverProductSalesMake`
8. `generateNaverBookProductJsonlJs`
9. `validateArtifacts`
10. `recordManifestValidated`
11. `publishToCompatibilityTarget`
12. `readbackSmoke`
13. `markRunComplete`

Likely artifacts:

- `bestseller_aladdin.jsonl`
- `relative_aladdin.jsonl`
- `product_aladdin.jsonl.js`

Primary ledger target:

- `www2.aladin.co.kr/b2b/navershoppingbook/product_aladdin.jsonl.js`

### TODAY Mode

Likely steps:

1. `prepareNaverProductV2TodaySnapshot`
2. `generateNaverBookProductTodayJsonlJs`
3. common validate/manifest/publish/readback tail

Likely artifact:

- `product_aladdin_today.jsonl.js`

Validation:

- `JsonlComparator` for `.jsonl`
- `JsonlComparator` + `JsonlJsEnvelopeHandler` for `.jsonl.js`
- byte count, SHA-256, line count, malformed JSONL, newline, encoding, order mismatch
- aggregate diagnostics: product count, price sums, availability/status/category distributions

Unknowns blocked by G1:

- active SQL Agent package/schedule
- SP definitions and sort order for `Naver_*`
- whether `.jsonl.js` has wrapper bytes or plain JSONL with `.js` extension
- whether bestseller/relative artifacts are partner-visible or internal side effects
- whether DTSX `getdate()` behavior should be replaced by deterministic `businessDate`

## `naverShoppingFeedJob`

Candidate DTSX:

- `DTS_NaverShopDBFile_Make.dtsx`
- `DTS_NaverShopDBFile_Make_Today.dtsx`

### FULL Mode

Likely steps:

1. `validateParameters`
2. `acquireIntegrationLock`
3. `truncateNaverShopProduct`
4. `stageNaverShopProduct`
5. `applyNaverShopExceptionDeletes`
6. `runNaverShopProductRemoveItem`
7. `deleteOldNaverShoppingFiles`
8. `generateNaverShoppingProductTxt`
9. `generateNaverShoppingSalesTxt`
10. common validate/manifest/publish/readback tail

Likely artifacts:

- `product_aladin.txt`
- `sales_aladin.txt`

### TODAY Mode

Likely steps:

1. `runNaverShopProductTodayMake`
2. `generateNaverShoppingProductTodayTxt`
3. common validate/manifest/publish/readback tail

Likely artifact:

- `product_aladin_today.txt`

Validation:

- `TxtComparator`
- byte equality, line sequence, header policy, delimiter or fixed-width shape, null token, trailing delimiter, newline
- aggregate diagnostics: product count, sale stats count/sums, availability/status/category distributions

Unknowns blocked by G1:

- exact TXT encoding from legacy writer
- header/body schema from SP result sets
- whether `sales_aladin.txt` is same integration artifact or separate target alias
- restart safety around staging truncate and retention delete

## `naverRankingFeedJob`

Status: blocked until G1.

Reason:

- `DTS_NaverDBFile_BestSellerMake.dtsx` appears to generate dated bestseller text and carries validation-needed history.
- `DTS_NaverDBFile_Make_V2.dtsx` contains bestseller flow that may belong inside `naverBookFeedJob`.
- `naver.dtsx` appears to be old product feed, not ranking.
- `product_aladdin_unicode.txt` may be an intermediate before `.jsonl.js`, not the external row 15 contract.

No `ContractOutputSpec`, validation profile, or implementation slice should be finalized for `naverRankingFeedJob` before SQL Agent enabled job/step/package evidence, deployed DTSX, SP definitions, and golden outputs are confirmed.
