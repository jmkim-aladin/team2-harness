---
phase: 5
phase_name: Shadow Run And Operational Hardening
artifact: runbook
status: drafted
created: 2026-06-19
requirements:
  - OPS-03
---

# Phase 5 Operator Runbook

## Required Inputs

Every operator action needs:

- `runId`
- `jobExecutionId`
- `artifactId` or `artifactGroupId`
- `integrationId`
- `mode`
- `businessDate`
- `contractVersion`
- `targetAlias`
- `requestedBy`
- masked `reason`

## Restart

Use restart when the same Spring Batch `JobInstance` can safely continue after a transient failure.

Allowed:

- same identifying parameters
- same `runId` and intended artifact identity
- no source data or contract correction needed
- work state is reusable
- manifest says no invalid partner-facing publish occurred

Forbidden:

- changing source query or contract
- regenerating a corrupted artifact as if it were the same artifact
- publishing unless the manifest artifact is `VALIDATED`

Events:

```text
RESTART_REQUESTED
RUN_PLANNED
RUN_COMPLETED
RUN_FAILED
```

Exit criteria:

- failed Step completes or fails with new manifest event
- no artifact overwrite without manifest event
- lock is released or heartbeat is active

## Manual Rebuild

Use manual rebuild when a new source read, generation, or validation attempt is required.

Rules:

- create new `runId`
- create new `artifactId`
- never overwrite previous artifact
- append link to previous run through `supersedesRunId` when applicable
- include identifying `rerunKey` or attempt identity in `runPurpose`

`forceRebuild` may exist as a non-identifying convenience flag, but it is not enough to define artifact identity.

Events:

```text
REBUILD_REQUESTED
RUN_PLANNED
GENERATION_STARTED
VALIDATION_STARTED
VALIDATION_PASSED
VALIDATION_FAILED
```

Exit criteria:

- new validation report exists
- previous artifact remains immutable
- cutover eligibility recalculates from the new run

## Retransfer

Use retransfer when the partner or operator needs the same already validated artifact delivered again.

Rules:

- only use existing `VALIDATED` or archived artifact
- retransfer cannot query DB/SP/generation
- use identifying `retransferArtifactId`, `targetAlias`, and `attemptKey`
- write a new `integration_publish_attempt`
- preserve original artifact checksum

Events:

```text
RETRANSFER_REQUESTED
PUBLISH_STARTED
PUBLISH_COMMITTED
READBACK_STARTED
READBACK_PASSED
READBACK_FAILED
RETRANSFER_COMPLETED
```

Exit criteria:

- readback proves remote artifact matches manifest, or failure is recorded as retryable/final
- no source generation Step ran
- original artifact remains immutable

## Rollback

Rollback is a business operation, not a Spring Batch restart.

Scenarios:

- pre-publish failure: no external rollback; keep or discard candidate artifact by manifest status
- partial publish: mark `PARTIAL`, alert, perform publisher-specific cleanup or restore, then retransfer known-good artifact if approved
- completed wrong artifact: require approval to retransfer previous known-good artifact
- schedule issue: restore or re-enable legacy SSIS schedule only after explicit cutover rollback approval

Events:

```text
ROLLBACK_REHEARSAL_PASSED
ROLLBACK_STARTED
ROLLBACK_COMPLETED
LEGACY_SCHEDULE_RESTORE_COMPLETED
```

Exit criteria:

- partner-visible destination matches known-good artifact or legacy schedule is restored
- validation/readback report exists for restored state
- incident/change record references manifest event IDs

## Failure Decision Tree

```text
Alert/operator request
|
|-- Is this shadow/candidate mode?
|   |-- yes: no production publish/rollback. Record manifest event, keep artifacts, rerun shadow only.
|   |-- no: continue.
|
|-- Is run already COMPLETED / READBACK_PASSED?
|   |-- partner needs same artifact again:
|   |   -> Retransfer existing validated/archive artifact.
|   |-- artifact later found wrong:
|       -> Business rollback: approve previous known-good artifact retransfer.
|
|-- Did failure happen before VALIDATED?
|   |-- parameter/lock/prep/generation transient:
|   |   -> Restart same JobInstance if snapshot/work state is reusable.
|   |-- source data, code, contract, or artifact corruption issue:
|   |   -> Manual rebuild with new run/artifact identity.
|   |-- validation diff:
|       -> Stop. No publish. Record validation result and diff artifact.
|
|-- Did failure happen after VALIDATED but before partner-visible publish?
|   |-- no remote bytes / temp artifact only:
|   |   -> Cleanup temp if needed, then restart publish or retransfer validated artifact.
|   |-- remote final object may exist:
|       -> Treat as partial publish. Run rollback/readback handling first.
|
|-- Did failure happen during publish?
|   |-- transient network/FTP/API:
|   |   -> Retry within policy; if exhausted, mark PUBLISH_FAILED.
|   |-- partial partner-visible artifact:
|       -> Mark PARTIAL, alert, cleanup/restore by publisher, then retransfer.
|
|-- Did failure happen during readback?
|   |-- remote size/checksum matches manifest:
|   |   -> allow operator-confirmed READBACK_PASSED event.
|   |-- remote missing/mismatch/unknown:
|       -> Treat as partial publish, rollback/cleanup, then retransfer.
|
|-- Is lock stale?
    -> Verify owner run inactive, require explicit operator takeover, append manifest event.
```

## Lock Takeover

Stale lock takeover requires:

- owner run inactive confirmation
- operator identity
- masked reason
- event `LOCK_STALE_DETECTED`
- event `LOCK_TAKEOVER_APPROVED`
- previous owner run status preserved

## First Slice Limitation

For `kakaoDaumFeedJob` first vertical slice, production-side commands stay disabled until cutover approval. Phase 5 can model rollback/retransfer, but executable commands must target only candidate storage.
