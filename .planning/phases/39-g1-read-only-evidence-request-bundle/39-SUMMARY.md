# Phase 39 Summary - G1 Read-only Evidence Request Bundle

## Result

`partner-integration-batch`에 G1 read-only evidence request bundle generator와 command runner를 추가했다. 이 bundle은 승인 전 운영자에게 전달할 수 있는 수집 manifest이며, 실제 SQL Server, SQL Agent, FTP, SMB, HTTP, API, production endpoint에는 접속하지 않는다.

## Changes

- Added `G1EvidenceRequestBundle` model.
- Added `G1EvidenceRequestBundleGenerator`.
- Added `G1EvidenceRequestCommandLineRunner`.
- Added deterministic sample request bundle:
  - `docs/g1-evidence/request-bundle.json`
- Updated README, G1 fragment import guide, and migration ledger.

## Request Bundle Contents

- `approvalRequired=true`
- `collectionMode=READ_ONLY_OPERATOR_EXPORT`
- required fragments: 7
- target requests: 7
- read-only evidence query templates:
  - `msdb-active-job-steps`
  - `stored-procedure-definition`
  - `dtsx-checksum`
  - `golden-output-checksum`
- forbidden actions:
  - DB write
  - SQL Agent disable
  - schedule change
  - DTSX execution
  - partner publish
  - production file modification

## Remaining Blocker

G1 read-only evidence collection still requires user/human approval before any actual SQL Agent, DTSX, SP, or golden output evidence is collected.
