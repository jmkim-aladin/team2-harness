---
phase: 2
phase_name: Spring Batch Architecture Baseline
status: research_complete
created: 2026-06-19
source: multi_agent_v1 explorers
---

# Phase 2 Research: Spring Batch Architecture Baseline

## RESEARCH COMPLETE

## Architecture Shape

Use one Kotlin/Spring Boot batch application in `partner-integration-batch`, with strong package boundaries:

| Package | Responsibility |
|---|---|
| `app` | Boot entrypoint, config binding, Actuator/ops wiring, job launch policy |
| `batch` | Spring Batch `Job`, `Step`, flow/decider configuration, listeners, parameter validation |
| `contract` | `IntegrationId`, `FeedMode`, `ContractVersion`, delivery contract, schema/format contract |
| `legacy` | `LegacyDbAdapter` port and JDBC implementation; SP/SQL names stay here only |
| `artifact` | JSONL/TXT/TSV/XML and future non-file artifact generation; work/validated/archive store |
| `manifest` | `IntegrationManifest`, run/artifact/validation/publish/readback state, append-only events |
| `validation` | schema, format, checksum, golden/shadow comparison interfaces |
| `delivery` | v1 compatibility bridge for file/HTTP/FTP/API targets |
| `feed.*` | feed-specific contract and mappings; `naverranking` remains blocked until G1 |

## Required Ports

- `LegacyDbAdapter`
- `IntegrationArtifactGenerator`
- `ArtifactStore`
- `IntegrationValidator`
- `IntegrationPublisher`
- `IntegrationManifestRepository`
- `IntegrationLockService`
- `ReadbackSmokeClient`
- `IntegrationJobParameters`
- `IntegrationManifest`
- `ArtifactDescriptor`
- `ValidationReport`
- `PublishResult`

## SSIS To Spring Batch Mapping

| SSIS | Kotlin/Spring Batch Mapping |
|---|---|
| Package | One `Job` per integration |
| Control Flow | `Step`, `Flow`, `JobExecutionDecider`, explicit `ExitStatus` |
| Data Flow | chunk-oriented `Step` with paging/range/partition reader and streaming writer |
| Execute SQL Task | `TaskletStep` calling typed `LegacyDbAdapter` method |
| Script Task | Kotlin service or tasklet with semantic names, not script text translation |
| Precedence Constraint | step transition and fail/stop conditions |
| Foreach Loop | partitioned step or `ContractOutputSpec` loop with `StepExecutionContext` |
| Error Output | fail-fast by default; explicit `SkipPolicy`, `SkipListener`, reject artifact only when contract allows |
| Checkpoint | Spring Batch `JobRepository` and `ExecutionContext` plus domain `IntegrationManifest` |

## Job Parameter Model

Spring Batch `JobInstance` is determined by `Job + identifying JobParameters`, so shadow/rebuild/retransfer cannot be an afterthought.

Recommended:

- identifying: `integrationId`, `mode`, `businessDate`, `contractVersion`, `runPurpose`
- non-identifying: `forceRebuild`, `requestedBy`, `reason`
- retransfer job identifying: `retransferArtifactId`, `targetAlias`, `attemptKey`

If `shadowRun` remains a boolean, it must be identifying or encoded in `runPurpose`/`mode`; otherwise a shadow run can collide with a production publish run for the same business date.

## Manifest-First Operations

Keep Spring Batch metadata and partner-domain manifest separate:

| Table/Document | Minimum Fields |
|---|---|
| `integration_run` | `runId`, `jobExecutionId`, `integrationId`, `partnerId`, `mode`, `businessDate`, `contractVersion`, `runPurpose`, `status`, timestamps, masked error |
| `integration_artifact` | `artifactId`, `runId`, `artifactType`, `sequence`, `fileName`, `contentType`, `encoding`, `newline`, `delimiter`, `storageUri`, `byteCount`, `rowCount`, `sha256`, `validationStatus` |
| `integration_publish_attempt` | `publishAttemptId`, `artifactId`, `targetType`, `targetAlias`, masked destination, status, attempt number, remote size/checksum, readback status |
| `integration_validation_result` | `runId`, `artifactId`, `ruleName`, expected/actual/tolerance, status, diff summary, diff artifact URI |
| `integration_manifest_event` | append-only state transition, manual rerun, retransfer, rollback, lock override events |

Recommended status path:

`PLANNED -> LOCKED -> PREPARING -> GENERATING -> VALIDATING -> VALIDATED -> PUBLISHING -> PUBLISHED -> READBACK_PASSED -> COMPLETED`

## Artifact Lifecycle

- Generate only into `work/{integrationId}/{businessDate}/{runId}`.
- Validate before publish.
- Promote to `validated` only after checksum is stable and manifest is committed.
- Publish from `validated`, never from generator work output.
- Archive immutable artifacts by `contractVersion/integrationId/businessDate/artifactId`.
- Rebuild creates a new artifact. Retransfer republishes an existing validated artifact.

## Locking

Use a domain lock in addition to Spring Batch instance protection.

Recommended key:

`integrationId + mode + businessDate + contractVersion + targetAlias`

Lock row fields:

- `ownerRunId`
- `heartbeatAt`
- `expiresAt`
- `status`

Expired lock takeover must require explicit operator action and append a manifest event.

## Delivery Bridge

Core batch code should know only `targetAlias`, not concrete paths, credentials, or protocol details.

Publisher implementations:

- `FilePublisher`
- `StaticHttpFilePublisher`
- `FtpPublisher`
- `ApiPublisher`

Delivery modernization remains v2 after DB migration.

## Defer Until G1

- Row 15 exact job/package/scope.
- Exact SP DTOs and `LegacyDbAdapter` method signatures.
- SP side effects, transaction boundaries, ordering, null handling.
- Field schemas, delimiters, encoding, newline, JSONL `.js` wrapping, TSV split rules.
- Chunk sizes, partition keys, and performance tuning.
- Golden-file thresholds and acceptable differences.
- Concrete publisher implementations needing credentials/network path access.
- Production cutover and SSIS schedule disablement.
