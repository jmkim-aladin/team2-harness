---
phase: 6
phase_name: Incremental Cutover Plan
plan: 06
type: execute
wave: 1
depends_on:
  - 03-validation-harness-specification
  - 04-feed-job-design-and-first-conversion-plan
  - 05-shadow-run-and-operational-hardening
files_modified:
  - .planning/phases/06-incremental-cutover-plan/06-CONTEXT.md
  - .planning/phases/06-incremental-cutover-plan/06-RESEARCH.md
  - .planning/phases/06-incremental-cutover-plan/06-PLAN.md
  - .planning/phases/06-incremental-cutover-plan/06-CUTOVER-CHECKLIST.md
  - .planning/phases/06-incremental-cutover-plan/06-SCHEDULE-ROLLBACK.md
  - .planning/phases/06-incremental-cutover-plan/06-RELEASE-NOTE.md
  - .planning/phases/06-incremental-cutover-plan/06-SUMMARY.md
  - .planning/phases/06-incremental-cutover-plan/06-VERIFICATION.md
autonomous: true
requirements:
  - OPS-03
  - OPS-04
---

# Phase 6 Plan: Incremental Cutover Plan

<objective>
Define feed-by-feed cutover gates for moving from SSIS schedules to Kotlin Spring Batch jobs without changing partner-visible contracts.
</objective>

<must_haves>
- Cutover gate, owner, backup owner, and rollback owner are required per feed/job.
- Production schedule disable/enable is split into pre-approval preparation and post-approval execution.
- Validation report and rollback rehearsal are mandatory.
- v1 release note states partner-visible contract is unchanged.
- Runtime account, private network allowlist, secret source, and alert route are explicit approval inputs.
</must_haves>

<tasks>

<task id="T1" type="execute">
<title>Create cutover checklist</title>
<action>
Create `06-CUTOVER-CHECKLIST.md` defining feed-by-feed gate states, required evidence, go/no-go criteria, owner fields, and execution checklist.
</action>
<acceptance_criteria>
- Contains `owner`, `backupOwner`, and `rollbackOwner`.
- Contains validation report and rollback rehearsal gates.
- Contains clean-run evidence gates.
- Contains per-feed go/no-go table.
</acceptance_criteria>
</task>

<task id="T2" type="execute">
<title>Create schedule and rollback procedure</title>
<action>
Create `06-SCHEDULE-ROLLBACK.md` separating approval-before and approval-after actions for SSIS schedule disable, Spring Batch schedule enable, rollback, and legacy schedule restore.
</action>
<acceptance_criteria>
- Pre-approval actions do not change production.
- Post-approval actions include SSIS disable and Spring Batch enable.
- Rollback includes legacy SSIS schedule restore.
- Includes manifest/audit evidence requirements.
</acceptance_criteria>
</task>

<task id="T3" type="execute">
<title>Create v1 release note and communication guardrail</title>
<action>
Create `06-RELEASE-NOTE.md` documenting that v1 preserves file/HTTP/FTP/API delivery contracts and treats internal outputs as integration artifacts, not file-only feeds.
</action>
<acceptance_criteria>
- States partner-visible contract is unchanged.
- States delivery modernization is post-migration.
- Covers non-file/API artifact contracts.
- Lists runtime/private network approval checklist.
</acceptance_criteria>
</task>

<task id="T4" type="execute">
<title>Update project state and traceability</title>
<action>
Update `.planning/STATE.md`, `.planning/REQUIREMENTS.md`, and `.planning/ROADMAP.md` to reflect Phase 6 local cutover planning without claiming production execution.
</action>
<acceptance_criteria>
- Current focus is Phase 6.
- OPS-03 and OPS-04 show Phase 6 cutover-planning coverage.
- Next phase points to post-migration delivery modernization.
</acceptance_criteria>
</task>

</tasks>

<verification>

Run these checks:

```bash
test -f .planning/phases/06-incremental-cutover-plan/06-CUTOVER-CHECKLIST.md
test -f .planning/phases/06-incremental-cutover-plan/06-SCHEDULE-ROLLBACK.md
test -f .planning/phases/06-incremental-cutover-plan/06-RELEASE-NOTE.md
rg -n "owner|backupOwner|rollbackOwner|validation report|rollback rehearsal|go/no-go" .planning/phases/06-incremental-cutover-plan/06-CUTOVER-CHECKLIST.md
rg -n "pre-approval|post-approval|SSIS schedule|Spring Batch schedule|legacy SSIS schedule restore|human approval" .planning/phases/06-incremental-cutover-plan/06-SCHEDULE-ROLLBACK.md
rg -n "partner-visible contract|unchanged|delivery modernization|post-migration|non-file|private network" .planning/phases/06-incremental-cutover-plan/06-RELEASE-NOTE.md
```

</verification>

<success_criteria>
1. Phase 6 defines cutover gates but performs no production action.
2. Each feed cutover has required evidence, owners, and rollback path.
3. v1 contract compatibility remains explicit.
4. Delivery modernization remains Phase 7/post-migration.
</success_criteria>
