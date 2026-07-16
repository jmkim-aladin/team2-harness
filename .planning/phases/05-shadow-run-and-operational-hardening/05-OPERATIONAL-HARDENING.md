---
phase: 5
phase_name: Shadow Run And Operational Hardening
artifact: operational_hardening
status: drafted
created: 2026-06-19
requirements:
  - VAL-04
  - OPS-03
---

# Phase 5 Operational Hardening

## Manifest Hardening

Harden the Phase 2 manifest model. Do not create a separate operations truth store.

| Entity | Add or confirm fields |
|---|---|
| `integration_run` | `runTrigger`, `requestedBy`, `reason`, `lockKey`, `candidateNamespace`, `goldenSetId`, `baselineRunId`, `cleanRunSequence`, `durationMs`, `scheduleId`, `rollbackPlanId`, `supersedesRunId` |
| `integration_artifact` | `artifactGroupId`, `artifactKey`, `contractOutputKey`, `zone`, `partnerVisible`, `expectedEncoding`, `detectedEncoding`, `detectedNewline`, `schemaRef`, `baselineArtifactId`, `promotedAt`, `archivedAt` |
| `integration_publish_attempt` | `readbackScope`, `publishStrategy`, `tempDestinationMasked`, `finalDestinationMasked`, `remoteLastModified`, `readbackProbeType`, `readbackStrength`, `retryable`, `failureClass`, `startedAt`, `endedAt` |
| `integration_validation_result` | `ruleScope`, `severity`, `validationProfileId`, `baselineArtifactId`, `baselineSha256`, `candidateSha256`, `comparatorVersion`, `exceptionApprovalId` |
| `integration_manifest_event` | `correlationId`, `actorType`, `reasonCode`, `previousStatus`, `nextStatus`, `detailMasked` |

Secret values, credentials, host passwords, tokens, and unmasked private paths must never be written to manifest, logs, docs, commits, or tickets.

## Event Vocabulary

Use append-only events:

```text
RUN_PLANNED
LOCK_ACQUIRED
LOCK_STALE_DETECTED
LOCK_TAKEOVER_APPROVED
GENERATION_STARTED
GENERATION_FAILED
ARTIFACT_CHECKSUM_RECORDED
VALIDATION_STARTED
VALIDATION_PASSED
VALIDATION_FAILED
ARTIFACT_PROMOTED_VALIDATED
PUBLISH_STARTED
PUBLISH_TEMP_WRITTEN
PUBLISH_COMMITTED
PUBLISH_FAILED
READBACK_STARTED
READBACK_PASSED
READBACK_FAILED
RUN_COMPLETED
RUN_FAILED
RESTART_REQUESTED
REBUILD_REQUESTED
RETRANSFER_REQUESTED
RETRANSFER_COMPLETED
ROLLBACK_REHEARSAL_PASSED
ROLLBACK_STARTED
ROLLBACK_COMPLETED
LEGACY_SCHEDULE_RESTORE_COMPLETED
```

## Status Model

Do not collapse run, artifact validation, publish, and readback into one status.

`publishStatus`:

```text
NOT_REQUESTED
BLOCKED_VALIDATION
READY
PUBLISHING
TEMP_WRITTEN
COMMITTING
PUBLISHED
FAILED_RETRYABLE
FAILED_FINAL
PARTIAL
ROLLED_BACK
SUPERSEDED
RETRANSFERRED
```

`readbackStatus`:

```text
NOT_REQUIRED
PENDING
SKIPPED_SHADOW
PROBING
PASSED
REMOTE_MISSING
SIZE_MISMATCH
CHECKSUM_MISMATCH
CONTENT_MISMATCH
PERMISSION_DENIED
TIMEOUT
FAILED_RETRYABLE
FAILED_FINAL
```

Production `COMPLETED` requires:

- every required artifact `VALIDATED`
- publish `PUBLISHED`
- readback `PASSED`

Shadow `COMPLETED` requires:

- every required artifact `VALIDATED`
- no partner-facing publish
- readback `SKIPPED_SHADOW` or candidate readback smoke passed

## Metrics

Use low-cardinality metric labels only:

```text
integrationId
mode
contractVersion
runPurpose
targetAlias
adapter
artifactType
```

Keep `runId` and `artifactId` in logs and manifest, not in metric labels.

Metrics:

- `integration_run_duration_seconds`
- `step_duration_seconds`
- `validation_duration_seconds`
- `publish_duration_seconds`
- `readback_duration_seconds`
- `artifact_row_count`
- `artifact_byte_count`
- `artifact_expected_count`
- `artifact_missing_count`
- `validation_rule_failures_total`
- `validation_diff_count`
- `checksum_mismatch_total`
- `encoding_mismatch_total`
- `publish_attempts_total`
- `publish_partial_total`
- `readback_failures_total`
- `retransfer_total`
- `lock_wait_seconds`
- `stale_lock_total`
- `lock_takeover_total`
- `shadow_clean_run_streak`
- `duration_vs_ssis_baseline_ratio`
- `kakao_daum_xml_group_complete`
- `kakao_daum_xml_malformed_total`
- `kakao_daum_encoding_mismatch_total`

## Alerts

P1:

- production job failure
- missed scheduled run
- validation diff on cutover candidate
- partial partner-visible publish
- readback final failure
- rollback failure
- stale lock blocking SLA

P2:

- repeated FTP/API/readback retry failures
- duration over 150% of SSIS baseline
- shadow clean-run streak reset
- artifact count mismatch
- secret expiry warning

Safety alert:

- retention or delete candidate includes non-candidate or partner-facing path

## Validation Report Shape

Produce machine-readable JSON and human-readable Markdown from the same `ValidationReportAssembler`.

Top-level report sections:

```text
summary
  reportVersion, generatedAt, runId, jobExecutionId, integrationId, mode,
  businessDate, contractVersion, runPurpose, conclusion, blockingReasons

baseline
  goldenSetId, baselineRunId, baselineArtifactIds, ssisDurationMs

candidate
  candidateRunId, candidateNamespace, artifactGroupId, durationMs

artifacts[]
  artifactKey, sequence, fileName, format, expectedEncoding, detectedEncoding,
  byteCountBaseline, byteCountCandidate, sha256Baseline, sha256Candidate,
  rowOrNodeCountBaseline, rowOrNodeCountCandidate, exactByteEqual,
  comparatorName, comparatorVersion, diffSummary, diffArtifactUri

rules[]
  ruleName, ruleScope, severity, expected, actual, tolerance, status,
  exceptionApprovalId

aggregates[]
  metricName, baselineValue, candidateValue, delta, tolerance, status

publishReadback
  targetAlias, readbackScope, publishStatus, readbackStatus, remoteSize,
  remoteChecksum, probeType, readbackStrength, attempts

operations
  lockWaitMs, retries, retransferAllowed, rollbackReady, auditEventIds

decision
  eligibleForCutover, requiredCleanRunsMet, rollbackRehearsalStatus, nextAction
```

For Kakao/Daum, the report must assert exactly six XML files, same `businessDate`, expected order, expected encoding per file, and no partner-facing publish during shadow.
