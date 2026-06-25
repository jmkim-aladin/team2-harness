---
phase: 6
phase_name: Incremental Cutover Plan
artifact: research
status: drafted
created: 2026-06-19
requirements:
  - OPS-03
  - OPS-04
---

# Phase 6 Research: Incremental Cutover Plan

## Research Sources

This phase used existing planning artifacts plus three parallel read-only agent passes:

- feed-by-feed cutover gate and evidence design
- schedule disable/enable and legacy restore rollback flow
- v1 release note and partner-visible contract guardrail

No agents edited files. No DB, SQL Agent, YouTrack, KB, git, or production target was touched.

## Findings

### Cutover Unit

Use this as the approval and execution unit:

```text
integrationId + mode + contractVersion + targetAlias
```

`kakaoDaumFeedJob` can cut over as an artifact group because its six XML outputs are contractually coupled.

### Global Entry Gate

No cutover unit can enter G5 approval unless all are true:

- G1 evidence is locked.
- Runtime account, private network allowlist, secret source, and alert route are approved.
- `owner`, `backupOwner`, and `rollbackOwner` are assigned.
- Shadow clean-run evidence exists.
- Validation report shows zero diff.
- Rollback rehearsal passed.
- v1 release note proves partner-visible contract is unchanged.

### Pre-Approval Means No Production Change

Pre-approval work may collect evidence, prepare commands, capture legacy schedule state, and assemble validation packets. It must not disable SSIS, enable Spring Batch production recurrence, publish partner-facing artifacts, or run rollback against production.

### Release Note Must Be Evidence-Backed

The v1 claim is:

```text
The internal runtime changes from SSIS to Kotlin Spring Batch.
Partner-visible delivery contracts are unchanged.
Delivery modernization is post-migration work, not part of v1.
```

This is not a bare assertion. It must be backed per cutover unit by golden SSIS output, validation report, publish/readback smoke, manifest events, rollback rehearsal, and owner sign-off.

### Not File-Only

Use `partner integration artifact`, not only `file feed`. A v1 artifact can be file, HTTP/static payload, FTP payload, SMB output, API request/response payload, or another partner contract. Internal code should see `contractOutputKey`, `contentType`, hash, target alias, idempotency rule, and readback/probe evidence.
