---
phase: 2
phase_name: Spring Batch Architecture Baseline
artifact: operations
status: drafted
created: 2026-06-19
requirements:
  - OPS-01
  - OPS-02
  - OPS-04
  - ARCH-04
---

# Phase 2 Operations Baseline

## Manifest Model

Spring Batch metadata is execution metadata. The `IntegrationManifest` is partner-domain truth for artifacts, validation, publish/readback, audit, rerun, and rollback.

| Table/document | Purpose | Minimum fields |
|---|---|---|
| `integration_run` | one logical integration execution | `runId`, `jobExecutionId`, `integrationId`, `partnerId`, `mode`, `businessDate`, `contractVersion`, `runPurpose`, `status`, `startedAt`, `endedAt`, `errorCode`, `errorMessageMasked` |
| `integration_artifact` | generated artifact metadata | `artifactId`, `runId`, `artifactType`, `sequence`, `fileName`, `contentType`, `encoding`, `newline`, `delimiter`, `storageUri`, `byteCount`, `rowCount`, `sha256`, `validationStatus` |
| `integration_publish_attempt` | publish/readback attempt | `publishAttemptId`, `artifactId`, `targetType`, `targetAlias`, `destinationMasked`, `adapterVersion`, `status`, `attemptNo`, `remoteSize`, `remoteChecksum`, `readbackStatus` |
| `integration_validation_result` | validation rule result | `runId`, `artifactId`, `ruleName`, `expected`, `actual`, `tolerance`, `status`, `diffSummary`, `diffArtifactUri` |
| `integration_manifest_event` | append-only audit | `eventId`, `runId`, `artifactId`, `eventType`, `actor`, `detailMasked`, `createdAt` |

Status path:

```text
PLANNED -> LOCKED -> PREPARING -> GENERATING -> VALIDATING -> VALIDATED -> PUBLISHING -> PUBLISHED -> READBACK_PASSED -> COMPLETED
```

Failure states preserve the last successful artifact and append events rather than overwriting history.

## Artifact Lifecycle

Artifact zones:

- `work`
- `validated`
- `archive`

Generation writes to:

```text
work/{integrationId}/{businessDate}/{runId}
```

Rules:

- Validate before publish.
- Promote to `validated` only after checksum is stable and manifest is committed.
- Publish must use validated artifacts, not work output.
- Archive immutable artifacts by `contractVersion/integrationId/businessDate/artifactId`.
- Rebuild creates a new artifact.
- Retransfer republishes an existing validated artifact.

## Locking

Use a domain lock in addition to Spring Batch `JobInstance` protection.

Lock key:

```text
integrationId + mode + businessDate + contractVersion + targetAlias
```

Minimum lock fields:

- `ownerRunId`
- `heartbeatAt`
- `expiresAt`
- `status`

Expired lock takeover requires explicit operator action and an `integration_manifest_event`.

## Delivery Compatibility Bridge

The v1 migration preserves current delivery contracts through `IntegrationPublisher`. Delivery modernization is v2 after DB migration.

| Publisher | Target |
|---|---|
| `FilePublisher` | local/SMB/share style file target |
| `StaticHttpFilePublisher` | backing storage for existing `www2` static HTTP URLs |
| `FtpPublisher` | existing FTP target |
| `ApiPublisher` | non-file or request/response integration target |

Core batch code uses `targetAlias`; concrete paths, hosts, credentials, and protocols live in delivery configuration/adapters.

## Approval Matrix

| Approval item | Needed for | Phase 2 treatment |
|---|---|---|
| SQL Agent `msdb` job/step/package/schedule | canonical active package evidence | G1 approval required |
| operational DTSX deployment | repo/deployed drift check | G1 approval required |
| SP definitions | side effects, output DTOs, ordering | G1 approval required |
| golden outputs | equivalence baseline | G1 approval required |
| publish/readback access | delivery bridge verification | G1 approval required |
| runtime account | DB/artifact/publish/readback permissions | OPS-04 approval item |
| private network allowlist | runtime to DB, storage, FTP, HTTP, API, observability | OPS-04 approval item |
| secret source | secret manager refs and masking rules | OPS-04 approval item |

Secret values must never be written to manifests, logs, docs, commits, or tickets.

## Observability

Metrics:

- job and step duration
- row count
- byte count
- checksum
- validation failure count
- publish attempt count
- readback failure count
- lock wait and stale lock count
- shadow diff count

Structured log keys:

- `runId`
- `jobExecutionId`
- `artifactId`
- `integrationId`
- `businessDate`
- `contractVersion`
- `targetAlias`

Alerts:

- job failure
- validation diff
- readback failure
- partial publish/temp artifact left behind
- stale lock
- missing scheduled run
- repeated FTP/API failure
- secret expiry
