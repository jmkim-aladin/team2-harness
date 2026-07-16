---
phase: 5
phase_name: Shadow Run And Operational Hardening
plan: 05
type: execute
wave: 1
depends_on:
  - 02-spring-batch-architecture-baseline
  - 03-validation-harness-specification
  - 04-feed-job-design-and-first-conversion-plan
files_modified:
  - .planning/phases/05-shadow-run-and-operational-hardening/05-CONTEXT.md
  - .planning/phases/05-shadow-run-and-operational-hardening/05-RESEARCH.md
  - .planning/phases/05-shadow-run-and-operational-hardening/05-PLAN.md
  - .planning/phases/05-shadow-run-and-operational-hardening/05-SHADOW-LIFECYCLE.md
  - .planning/phases/05-shadow-run-and-operational-hardening/05-OPERATIONAL-HARDENING.md
  - .planning/phases/05-shadow-run-and-operational-hardening/05-RUNBOOK.md
  - .planning/phases/05-shadow-run-and-operational-hardening/05-SUMMARY.md
  - .planning/phases/05-shadow-run-and-operational-hardening/05-VERIFICATION.md
autonomous: true
requirements:
  - VAL-04
  - OPS-03
---

# Phase 5 Plan: Shadow Run And Operational Hardening

<objective>
Define the shadow-run lifecycle and operational hardening needed before the Kotlin Spring Batch replacement can be cut over feed by feed.
</objective>

<must_haves>
- Shadow runs use isolated candidate storage, not partner-facing final paths.
- Manifest records run, artifact, validation, publish/readback, and audit evidence.
- Restart, manual rebuild, retransfer, and rollback are separate runbook actions.
- Publish/readback status is recorded separately from job status.
- `kakaoDaumFeedJob` has six-XML artifact-group shadow criteria.
- Phase remains local-only until G1 and repo approval.
</must_haves>

<tasks>

<task id="T1" type="execute">
<title>Create shadow lifecycle specification</title>
<action>
Create `05-SHADOW-LIFECYCLE.md` covering candidate namespace, work/validated/archive lifecycle, clean-run criteria, readback smoke, and cutover eligibility.
</action>
<acceptance_criteria>
- Contains `candidate/{integrationId}/{mode}/{businessDate}/{contractVersion}/{runId}`.
- Contains `candidate/work`, `candidate/validated`, and `candidate/archive`.
- States partner-facing final paths are blocked during shadow.
- Defines three daily/today clean runs and one full clean run where applicable.
- Contains Kakao/Daum six XML group rule.
</acceptance_criteria>
</task>

<task id="T2" type="execute">
<title>Create operational hardening specification</title>
<action>
Create `05-OPERATIONAL-HARDENING.md` covering manifest hardening fields, event vocabulary, publish/readback status enums, metrics, alerts, and validation report shape.
</action>
<acceptance_criteria>
- Contains `integration_run`, `integration_artifact`, `integration_publish_attempt`, `integration_validation_result`, and `integration_manifest_event`.
- Contains `publishStatus` and `readbackStatus`.
- Contains `RETRANSFER_REQUESTED`, `ROLLBACK_STARTED`, and `LEGACY_SCHEDULE_RESTORE_COMPLETED`.
- Contains low-cardinality metric label rule.
- Contains machine-readable JSON and human-readable Markdown validation report guidance.
</acceptance_criteria>
</task>

<task id="T3" type="execute">
<title>Create operator runbook</title>
<action>
Create `05-RUNBOOK.md` covering restart, manual rebuild, retransfer, rollback, failure decision tree, lock takeover, and required operator inputs.
</action>
<acceptance_criteria>
- Separates restart, manual rebuild, retransfer, and rollback.
- States retransfer cannot query DB/SP or regenerate artifacts.
- States rebuild requires new `runId` and artifact identity.
- Contains failure decision tree.
- States production-side commands stay disabled until cutover approval.
</acceptance_criteria>
</task>

<task id="T4" type="execute">
<title>Update traceability and state</title>
<action>
Update `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, and `.planning/STATE.md` so Phase 5 local design is reflected without claiming executable shadow proof.
</action>
<acceptance_criteria>
- `VAL-04` is marked Specified with execution blocked by G1/repo/access.
- `OPS-03` is marked Specified.
- state current focus is Phase 5.
- roadmap next phase points to Phase 6 cutover planning after external gates.
</acceptance_criteria>
</task>

</tasks>

<verification>

Run these checks:

```bash
test -f .planning/phases/05-shadow-run-and-operational-hardening/05-SHADOW-LIFECYCLE.md
test -f .planning/phases/05-shadow-run-and-operational-hardening/05-OPERATIONAL-HARDENING.md
test -f .planning/phases/05-shadow-run-and-operational-hardening/05-RUNBOOK.md
rg -n "candidate/\\{integrationId\\}/\\{mode\\}/\\{businessDate\\}/\\{contractVersion\\}/\\{runId\\}|candidate/work|candidate/validated|candidate/archive|partner-facing|clean" .planning/phases/05-shadow-run-and-operational-hardening/05-SHADOW-LIFECYCLE.md
rg -n "integration_run|integration_artifact|integration_publish_attempt|integration_validation_result|integration_manifest_event|publishStatus|readbackStatus|RETRANSFER_REQUESTED|ROLLBACK_STARTED|LEGACY_SCHEDULE_RESTORE_COMPLETED" .planning/phases/05-shadow-run-and-operational-hardening/05-OPERATIONAL-HARDENING.md
rg -n "Restart|Manual rebuild|Retransfer|Rollback|rerunKey|retransfer.*DB/SP/generation|failure decision tree" .planning/phases/05-shadow-run-and-operational-hardening/05-RUNBOOK.md
rg -n "VAL-04.*Specified|OPS-03.*Specified" .planning/REQUIREMENTS.md
```

</verification>

<success_criteria>
1. VAL-04 and OPS-03 are covered by local design artifacts.
2. Phase 5 does not claim actual shadow execution.
3. The first executable path remains gated by G1, repo creation, and storage/runtime approval.
4. Cutover can only be considered after validation reports and rollback rehearsal exist.
</success_criteria>
