---
phase: 6
phase_name: Incremental Cutover Plan
artifact: release_note
status: drafted
created: 2026-06-19
requirements:
  - OPS-04
---

# Phase 6 v1 Release Note Guardrail

## v1 Contract Claim

v1 changes the internal batch runtime from SSIS to Kotlin Spring Batch, but does not change partner-visible delivery contracts.

Existing URL, FTP, API, WWW, SMB-facing targets, file names or artifact keys, format, encoding, schedule semantics, authentication path, and readback expectations remain unchanged.

Delivery modernization is post-migration work, not part of v1.

## Evidence Required Per Cutover Unit

The contract claim must be proven per:

```text
integrationId + mode + contractVersion + targetAlias
```

Required evidence:

- golden SSIS output
- byte/checksum/row or node validation
- schema, encoding, newline, delimiter, null handling, sort order, and aggregate validation
- publish/readback smoke
- manifest events
- rollback rehearsal
- owner, backup owner, and rollback owner sign-off

## Partner Integration Artifact Model

Use `partner integration artifact`, not only `file feed`.

Supported v1 artifact shapes:

- file artifact
- HTTP/static payload
- FTP payload
- SMB/UNC output
- API request/response payload
- other partner-facing payload contract

For non-file/API contracts, define:

- `contractOutputKey`
- `contentType`
- payload hash
- `targetAlias`
- request/response schema
- idempotency rule
- retry rule
- readback or probe evidence

Partner-visible unchanged means the existing endpoint, request/response shape, authentication behavior, timing, status semantics, and readback expectations stay the same.

## Runtime And Private Network Approval Checklist

Approval is required for:

- SQL Agent active job/step/package/schedule evidence
- deployed DTSX evidence
- SP definitions
- golden outputs
- publish/readback access
- runtime account least-privilege access
- JobRepository access
- manifest store access
- artifact store access
- candidate storage access
- publish target access
- readback target access
- private network allowlist to DB, storage, FTP, HTTP/static backing target, SMB/UNC if used, API targets if used, and alert/metrics route
- secret source and masking rules
- alert route
- owner, backup owner, rollback owner
- rollback rehearsal evidence
- G5 human cutover approval

Secret values must not appear in manifests, logs, docs, tickets, or commits.

## Explicitly Out Of v1

Reject v1 scope if it includes:

- DNS change
- URL change
- protocol change
- path change
- authentication change
- retention lifecycle replacement
- SFTP/FTPS migration
- private endpoint redesign
- S3/CloudFront redesign
- partner communication for contract change

Those belong to Phase 7 / post-migration delivery modernization.

## Draft Release Note Text

```text
This release migrates the internal partner integration batch runtime from SSIS to Kotlin Spring Batch for the approved cutover units.

Partner-visible delivery contracts are unchanged. Existing artifact keys, file names where applicable, payload format, encoding, schedule semantics, authentication path, endpoint/target alias, and readback expectations remain the same.

The release was approved only for cutover units with locked SSIS evidence, clean shadow-run validation, rollback rehearsal, runtime/private-network approval, and named owner/backup/rollback owner.

Delivery modernization is intentionally excluded and will be handled after the DB migration as a separate change.
```
