---
phase: 6
phase_name: Incremental Cutover Plan
artifact: cutover_checklist
status: drafted
created: 2026-06-19
requirements:
  - OPS-03
  - OPS-04
---

# Phase 6 Cutover Checklist

## Cutover Unit

Default unit:

```text
integrationId + mode + contractVersion + targetAlias
```

Required ownership fields:

```yaml
cutoverUnit:
  integrationId:
  mode:
  contractVersion:
  targetAlias:
  owner:
  backupOwner:
  rollbackOwner:
  approvalGateId:
  changeWindowKst:
  ssisScheduleId:
  springScheduleId:
  validationReportIds:
  rollbackRehearsalId:
  previousKnownGoodArtifactIds:
```

G5 is blocked until `owner`, `backupOwner`, and `rollbackOwner` are named humans.

## Global Entry Gate

| Gate | Required evidence |
|---|---|
| G1 evidence locked | SQL Agent job/step/package/schedule, deployed DTSX drift check, SP definitions, golden outputs, publish/readback access |
| Runtime approved | runtime account, private network allowlist, secret source, alert route |
| Owner assigned | `owner`, `backupOwner`, `rollbackOwner` |
| Shadow clean-run evidence | three consecutive clean TODAY/daily runs per unit; one clean FULL run where applicable |
| Validation clean | zero diffs; exact row/node, byte, checksum, schema, encoding, newline, delimiter, null, sort, aggregate match |
| Rollback rehearsal | passed rehearsal with manifest event IDs |
| Contract unchanged | v1 release note proves no partner-visible delivery contract change |

## Required Approval Packet

Each cutover packet must contain:

- validation report JSON
- validation report Markdown
- golden SSIS artifact IDs
- candidate run IDs and artifact IDs
- row or node count, byte count, SHA-256, encoding, newline, delimiter or schema evidence
- aggregate totals and reject count comparison
- manifest event IDs for generation, validation, promotion, publish/readback rehearsal
- duration ratio against SSIS baseline
- proof shadow paths stayed under `candidate/...`
- rollback rehearsal evidence
- release note stating partner-visible contract is unchanged
- named `owner`, `backupOwner`, `rollbackOwner`

Diff artifacts may exist only for blocked candidates. An approved cutover packet must have zero blocking diff.

## Feed-By-Feed Go/No-Go

| Unit | Go criteria | No-go criteria |
|---|---|---|
| `naverBookFeedJob` FULL/TODAY | JSONL/JSONL.js wrapper, sort order, SP behavior, and target aliases proven; evidence covers expected book artifacts and TODAY artifact | G1 missing, wrapper mismatch, sort/order mismatch, unchecked target alias |
| `naverShoppingFeedJob` FULL/TODAY | TXT encoding, schema/header policy, sales/product target split, and restart safety around staging/delete proven | encoding mismatch, target split unclear, unsafe staging/delete behavior |
| `naverRankingFeedJob` row 15 | G1 confirms active SQL Agent scope, deployed package, SP definitions, golden outputs | any row 15 scope uncertainty |
| `googleShoppingFeedJob` FULL/TODAY | five-file FULL split, `groupId` partition rule, `scheduleSlot/windowKey`, UNC-to-FTP mapping, per-partition aggregates proven | split mismatch, partition aggregate mismatch, same-day run collision risk |
| `kakaoDaumFeedJob` FULL | six XML files present for same `businessDate`; expected order, encoding, checksum, XML well-formedness, retention dry-run whitelist proven | missing XML, malformed XML, unsafe retention/delete scope, artifact group incomplete |

## Go / No-Go Rule

Go only for one cutover unit at a time, during an approved window, with owner, backup owner, and rollback owner present.

No-go if:

- any G1 item is missing
- any validation diff exists
- rollback rehearsal is missing
- shadow touched partner-facing paths
- runtime, secret, network, or alert approval is absent
- duration exceeds 200% of SSIS baseline or breaches the schedule window
- retention/delete scope is unsafe
- the release would change partner-visible contract
