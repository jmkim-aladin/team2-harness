---
phase: 2
phase_name: Spring Batch Architecture Baseline
artifact: batch_mapping
status: drafted
created: 2026-06-19
requirements:
  - BATCH-01
  - BATCH-02
  - BATCH-03
  - BATCH-04
  - ARCH-03
---

# Phase 2 Batch Mapping

## Canonical Flow

All integration jobs follow this logical flow unless the integration contract explicitly states otherwise:

```text
validateParameters
-> acquireIntegrationLock
-> legacyPrepareSnapshot
-> generateWorkArtifacts
-> validateArtifacts
-> recordManifestValidated
-> publishToCompatibilityTarget
-> readbackSmoke
-> markRunComplete
```

`publishToCompatibilityTarget` must not run unless validation passed and the manifest recorded validated artifacts.

## SSIS To Kotlin/Spring Batch

| SSIS concept | Kotlin/Spring Batch mapping | Rule |
|---|---|---|
| Package | `Job` | one stable job per partner integration |
| Control Flow | `Step`, `Flow`, `JobExecutionDecider`, `ExitStatus` | model success, no-data, validation-failed, publish-failed, and readback-failed states explicitly |
| Data Flow | chunk-oriented `Step` | use cursor/paging/range/partition readers and streaming writers |
| Execute SQL Task | `TaskletStep` calling `LegacyDbAdapter` | SP/SQL names are exposed only inside `legacy` adapters |
| Script Task | Kotlin service or tasklet | convert script behavior into semantic classes, not script text translation |
| Precedence Constraint | step transition and decider rule | validation failure must fail or stop before publish |
| Foreach Loop | partitioned step or `ContractOutputSpec` loop | partition/output key must be visible in `StepExecutionContext` |
| Error Output | fail-fast default; `SkipPolicy`, `SkipListener`, reject artifact when allowed | skip only if the partner contract allows row-level reject |
| Checkpoint | `JobRepository`, `ExecutionContext`, and `IntegrationManifest` | Spring Batch metadata handles execution; manifest handles partner artifact state |

## JobParameters

Spring Batch `JobInstance` is defined by `Job + identifying JobParameters`, so these values are part of the architecture contract.

Identifying parameters for generation jobs:

- `integrationId`
- `mode`
- `businessDate`
- `contractVersion`
- `runPurpose`

Non-identifying parameters:

- `forceRebuild`
- `requestedBy`
- `reason`

Retransfer job identifying parameters:

- `retransferArtifactId`
- `targetAlias`
- `attemptKey`

`shadowRun` cannot be a non-identifying flag if it changes publish semantics. Use `runPurpose` or mode values such as `PRODUCTION`, `SHADOW`, and `RETRANSFER` to avoid collisions between shadow and partner-visible runs.

## Restart, Rebuild, Retransfer

| Operation | DB/SP | Generation | Publish | Rule |
|---|---|---|---|---|
| Restart | resumes same failed job instance | resumes or regenerates from stable snapshot | only if validation already passed | same identifying parameters |
| Rebuild | allowed | creates new artifact | optional after validation | new run/artifact identity |
| Retransfer | forbidden | forbidden | required | uses existing validated artifact only |

Retransfer must not execute DB/SP/generation steps.

## Data Volume Rule

Full feed processing must use paging/range/partition readers and streaming writers. `JdbcTemplate.query()` into a full in-memory `List` is disallowed for partner feed generation.

## Failure Policy

- Default to fail-fast.
- Retry only transient publish/readback/network failures by default.
- Skip only contract-approved row-level errors.
- Reject count, reject sample, and reject artifact URI must be recorded in `IntegrationManifest`.
- A partial partner-visible artifact is a failed publish and must trigger readback/rollback handling.
