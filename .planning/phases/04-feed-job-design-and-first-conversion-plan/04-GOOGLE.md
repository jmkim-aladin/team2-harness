---
phase: 4
phase_name: Feed Job Design And First Conversion Plan
artifact: google
status: drafted
created: 2026-06-19
requirements:
  - FEED-04
---

# Phase 4 Google Feed Design

## `googleShoppingFeedJob`

Candidate DTSX:

- `DTS_GoogleShop_DBFile_Make_TSV_V2.dtsx`
- `DTS_GoogleShop_DBFile_Make_Today_TSV_V2.dtsx`

Historical candidates:

- non-V2 TSV full/today packages
- script-based full/today packages annotated as not used

Treat historical packages as clues only unless SQL Agent evidence says otherwise.

## Common Parameters

- `integrationId=GOOGLE_SHOPPING`
- `mode=FULL|TODAY`
- `businessDate`
- `contractVersion=v1`
- `runPurpose=PRODUCTION|SHADOW|RETRANSFER`
- identifying `scheduleSlot` or `windowKey` for same-day today runs

`scheduleSlot`/`windowKey` is required if today mode runs multiple times per day. Otherwise Spring Batch may treat same-day today reruns as the same completed `JobInstance`.

## FULL Mode

Likely steps:

1. `validateParameters`
2. `acquireIntegrationLock`
3. `truncateGoogleShopProductV2`
4. `stageTargetItemsV2`
5. `pruneFullExceptions`
6. `deleteOldGoogleV2Files`
7. `generateFullTsvPartitions`
8. `validateArtifacts`
9. `recordManifestValidated`
10. `publishToCompatibilityTarget`
11. `readbackSmoke`
12. `markRunComplete`

Full output artifacts:

- `product_aladin_1.txt`
- `product_aladin_2.txt`
- `product_aladin_3.txt`
- `product_aladin_4.txt`
- `product_aladin_5.txt`

`groupId` is a `StepExecutionContext` partition key. It is not a top-level `JobParameter`.

## TODAY Mode

Likely steps:

1. `validateParameters`
2. `acquireIntegrationLock`
3. `makeTodayTargetItemsV2`
4. `pruneTodayExceptions`
5. `generateTodayTsv`
6. common validate/manifest/publish/readback tail

Today output artifact:

- `product_aladin_today.txt`

## ContractOutputSpec

Known local assumptions:

- format: TSV-like text
- output target path in DTSX: UNC under `b2b/google/v2`
- ledger target: `ftp.aladin.co.kr`
- full partition count: `5`
- today partition key: `groupId=0`

Unknowns blocked by G1/golden output:

- actual `@groupId` partition rule
- header policy
- exact encoding/codepage
- column width/truncation behavior
- UNC-to-FTP publish mapping
- same-day schedule slots

## Validation

- `MultiResourceTsvComparator` for FULL mode
- `TsvComparator` for TODAY mode
- file naming/order validation
- per-file and aggregate row counts
- byte count and SHA-256
- encoding/newline
- column count
- product count, price sums, availability/category distribution, null/min/max, reject count, per-partition totals

## G1 Blockers

- SQL Agent enabled job/step/package/schedule
- deployed DTSX drift check
- SP definitions for `GoogleShop_*`
- golden output files for five full split files and today schedule slots
- publish/readback path access
- runtime account/private network/secret allowlist
