---
phase: 6
phase_name: Incremental Cutover Plan
artifact: schedule_rollback
status: drafted
created: 2026-06-19
requirements:
  - OPS-03
  - OPS-04
---

# Phase 6 Schedule And Rollback Procedure

## Pre-Approval Actions

Pre-approval actions do not change production.

- Confirm G1 evidence: SQL Agent job/step/package/schedule, deployed DTSX, SP definitions, golden outputs, publish/readback access.
- Confirm G2/OPS-04 evidence: repo, JobRepository, manifest store, artifact store, runtime account, secret source, private network allowlist, alert route.
- Assign `owner`, `backupOwner`, and `rollbackOwner`.
- Capture legacy SSIS baseline:
  - enabled state
  - schedule ID
  - next run
  - job step command/package
  - last successful run
  - owner/operator
- Prepare but do not run SSIS schedule disable command.
- Prepare but do not run Spring Batch production schedule enable command.
- Prepare validation report and rollback rehearsal packet.
- Prepare release note stating v1 partner-visible contract is unchanged.

## Human Approval Gate

G5 approval must explicitly name:

- cutover unit
- change window in KST
- approver
- owner
- backup owner
- rollback owner
- rollback trigger criteria
- validation report IDs
- rollback rehearsal ID
- legacy schedule snapshot

Without G5 approval, no SSIS schedule or Spring Batch production schedule can be changed.

## Post-Approval Actions

Only after G5 approval:

1. Open change window and record approver/time in KST.
2. Verify no active legacy SSIS execution.
3. Verify no conflicting Spring Batch lock.
4. Disable only the approved SSIS schedule/job for the approved cutover unit.
5. Capture before/after evidence of the SSIS schedule change.
6. Run first controlled Spring Batch production execution or enable one-time production schedule.
7. Verify manifest events:
   - `RUN_PLANNED`
   - `VALIDATION_PASSED`
   - `PUBLISH_COMMITTED`
   - `READBACK_PASSED`
   - `RUN_COMPLETED`
8. Enable recurring Spring Batch production schedule only after first success.
9. Keep rollback owner available until the first recurrence completes or the approved watch window ends.

## Rollback To Legacy SSIS

Rollback requires explicit human approval unless the rollback owner has pre-approved incident authority for the cutover window.

Steps:

1. Disable or pause the Spring Batch production schedule.
2. Confirm no active Spring Batch publish/readback lock remains.
3. If partner-visible artifact is partial or wrong, perform publisher cleanup/restore or retransfer previous known-good artifact.
4. Re-enable the captured legacy SSIS schedule state exactly as recorded pre-cutover.
5. Optionally run legacy SSIS manually only with owner approval to avoid duplicate publish.
6. Verify legacy output/readback or schedule restoration evidence.
7. Append manifest events:
   - `ROLLBACK_STARTED`
   - `ROLLBACK_COMPLETED`
   - `LEGACY_SCHEDULE_RESTORE_COMPLETED`
8. Link change or incident record to manifest event IDs.

## Audit Evidence

Keep evidence masked. No credentials, tokens, secret values, or unmasked private paths.

Required bundle:

- G5 approval record
- legacy schedule snapshot
- Spring schedule configuration
- validation report JSON/Markdown
- clean-run history
- rollback rehearsal proof
- manifest event IDs
- publish/readback status
- schedule disable/enable before/after output
- final go/no-go or rollback decision log
