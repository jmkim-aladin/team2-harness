# Research: Architecture

## Component Boundaries

```text
batch-core
  -> jobs
  -> step/tasklet config
  -> JobRepository / JobLauncher / JobOperator

legacy-db-adapter
  -> typed SP/SQL calls
  -> staging preparation
  -> read paging/range APIs

integration-contract
  -> field/schema or message contract
  -> filename/path/endpoint/mode rules
  -> encoding/newline/delimiter/null/sort contract

artifact-generator
  -> JSONL/TXT/TSV/XML streaming writers
  -> non-file artifact builders where needed

artifact-store
  -> work artifact
  -> validated artifact
  -> archive

validation
  -> schema/encoding/count/checksum/diff

delivery-bridge
  -> v1 compatibility publisher for file/HTTP/FTP/API targets
  -> post-migration implementation hidden behind interface

manifest
  -> run/artifact/publish/readback metadata
```

## Common Job Flow

```text
validateParameters
-> acquireIntegrationLock
-> legacyPrepareSnapshot
-> generateWorkArtifacts
-> validateArtifacts
-> commitArtifactManifest
-> publishToCompatibilityTarget
-> readbackSmoke
-> markRunComplete
```

## Job Candidates

| Integration | Job | Notes |
|------|-----|-------|
| Naver book | `naverBookFeedJob` | full/today JSONL or JSONL.js |
| Naver shopping | `naverShoppingFeedJob` | product/sales/today TXT |
| Naver ranking | `naverRankingFeedJob` | blocked until row 15 active package is confirmed |
| Google shopping | `googleShoppingFeedJob` | partition by `groupId` or confirmed split rule |
| Kakao/Daum | `kakaoDaumFeedJob` | six XML outputs, clearest first vertical slice |
| Retention | `feedRetentionJob` | replace SSIS delete tasks with lifecycle where possible |

## Runtime Model

- Individual partner integration work is Spring Batch `Job`.
- Complex cross-package schedule/dependency can be external orchestrator later.
- Job identity: `integrationId + mode + businessDate + contractVersion`.
- Conservative restart: regenerate from stable snapshot rather than append-resume partial files.
