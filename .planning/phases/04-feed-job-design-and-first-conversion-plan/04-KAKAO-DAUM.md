---
phase: 4
phase_name: Feed Job Design And First Conversion Plan
artifact: kakao_daum
status: drafted
created: 2026-06-19
requirements:
  - FEED-05
---

# Phase 4 Kakao/Daum Feed Design

## Candidates

- `KakaoDaum.dtsx`: primary feed generator
- `DTS_DaumDBFile_OldDataDelete.dtsx`: retention/delete job
- `wonderwmp.dtsx`: excluded; this belongs to WonderWMP products, not Kakao/Daum

## `kakaoDaumFeedJob`

Common parameters:

- `integrationId=KAKAO_DAUM`
- `mode=FULL`
- `businessDate`
- `contractVersion=v1`
- `runPurpose=PRODUCTION|SHADOW|RETRANSFER`

The DTSX appears to use current date in filename generation. The Spring Batch design uses `businessDate` for deterministic naming, but this remains G1-sensitive because the legacy SPs and scripts may depend on runtime date.

## Six XML Outputs

Filename pattern:

```text
yyyyMMdd000000_*.xml
```

| Order | Output | SP call | Encoding evidence |
|---:|---|---|---|
| 1 | `yyyyMMdd000000_selling.xml` | `KakaoDaum_Book_Selling @IsEBook=0` | CP949/MS949 |
| 2 | `yyyyMMdd000000_ebook_selling.xml` | `KakaoDaum_Book_Selling @IsEBook=1` | CP949/MS949 |
| 3 | `yyyyMMdd000000_event.xml` | `KakaoDaum_Book_Event @IsEBook=0` | UTF-8 |
| 4 | `yyyyMMdd000000_ebook_event.xml` | `KakaoDaum_Book_Event @IsEBook=1` | UTF-8 |
| 5 | `yyyyMMdd000000_eventbook.xml` | `KakaoDaum_Book_EventBook @IsEBook=0` | CP949/MS949 |
| 6 | `yyyyMMdd000000_ebook_eventbook.xml` | `KakaoDaum_Book_EventBook @IsEBook=1` | CP949/MS949 |

## Steps

1. `validateParameters`
2. `acquireIntegrationLock`
3. `generateSellingXml`
4. `generateEbookSellingXml`
5. `generateEventXml`
6. `generateEbookEventXml`
7. `generateEventBookXml`
8. `generateEbookEventBookXml`
9. `validateArtifacts`
10. `recordManifestValidated`
11. `publishToCompatibilityTarget`
12. `readbackSmoke`
13. `markRunComplete`

The disabled temp-file copy script path is not recreated. The v1 design streams the SP-returned XML text exactly rather than rebuilding XML with JAXB/domain objects.

## Validation

- `XmlComparator`
- named six-artifact group validation
- byte count and SHA-256 first
- XML/XPath diagnostics only after byte diff
- encoding/newline validation per output
- row/record count or XML node count where parseable
- malformed XML diagnostics
- aggregate checks only if SP output exposes parseable fields

Golden output must include all six XML files for the same `businessDate`.

## `feedRetentionJob`

Retention is a separate job, not hidden in `kakaoDaumFeedJob` publish.

Design rules:

- use target alias, not hardcoded UNC path
- support dry-run/shadow mode
- whitelist the six Kakao/Daum XML filename patterns
- record manifest/audit events for deletion candidates and actual deletes
- never delete candidate/shadow paths

## G1 Blockers

- SQL Agent enabled job/step/package/schedule
- deployed DTSX drift check
- `KakaoDaum_*` SP definitions
- six golden outputs
- publish/readback path access
- runtime account/private network/secret allowlist
