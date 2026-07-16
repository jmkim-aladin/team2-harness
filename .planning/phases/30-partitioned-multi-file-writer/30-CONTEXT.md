# Phase 30 Context: Partitioned Multi-File Writer

## Problem

Phase 28 identified one loop work item for Google TSV split output:

- `DTS_GoogleShop_DBFile_Make_TSV_V2`
- `TSV 출력 루프 - 파일쪼개기`
- nested data flow calls `GoogleShop_Product_Get_V2 @isToday=0, @groupId=?`

The actual SQL Agent/SP/golden evidence is still blocked on G1 approval, but the local split-file writer behavior can be implemented without touching DB, SQL Agent, FTP, SMB, HTTP, API, or production endpoints.

## Target

Add a local Kotlin service that can back a future Spring Batch partition/MultiResource writer:

- explicit partition key
- deterministic file naming rule
- max-record or max-byte split rule
- overwrite/symlink/path safety
- byte/SHA-256 readback stats

## Non-Goal

This does not connect to the Google job flow yet and does not reduce the DTSX coverage gate by itself.
