---
phase: 7
phase_name: Post-Migration Delivery Modernization
plan: 07
type: execute
wave: 1
depends_on:
  - 06-incremental-cutover-plan
files_modified:
  - .planning/phases/07-post-migration-delivery-modernization/07-CONTEXT.md
  - .planning/phases/07-post-migration-delivery-modernization/07-RESEARCH.md
  - .planning/phases/07-post-migration-delivery-modernization/07-PLAN.md
  - .planning/phases/07-post-migration-delivery-modernization/07-DELIVERY-OPTIONS.md
  - .planning/phases/07-post-migration-delivery-modernization/07-RETENTION-LIFECYCLE.md
  - .planning/phases/07-post-migration-delivery-modernization/07-PARTNER-MIGRATION.md
  - .planning/phases/07-post-migration-delivery-modernization/07-SUMMARY.md
  - .planning/phases/07-post-migration-delivery-modernization/07-VERIFICATION.md
autonomous: true
requirements:
  - DELIV-01
  - DELIV-02
  - DELIV-03
---

# Phase 7 Plan: Post-Migration Delivery Modernization

<objective>
Define post-migration delivery modernization options without changing v1 partner-visible contracts.
</objective>

<must_haves>
- Compare private web endpoint, SFTP/FTPS, object-storage style delivery, and API/payload delivery.
- Define retention/lifecycle replacement for SSIS delete/cleanup tasks.
- Define partner communication, compatibility period, versioning, rollback, and approval gates.
- Keep v1 migration and delivery modernization separate.
</must_haves>

<tasks>

<task id="T1" type="execute">
<title>Create delivery option comparison</title>
<action>
Create `07-DELIVERY-OPTIONS.md` comparing private endpoint, SFTP/FTPS, object storage/private CDN-style delivery, and API/payload delivery for partner integration artifacts.
</action>
<acceptance_criteria>
- Contains private communication requirement.
- Compares at least four delivery options.
- Covers file and non-file artifacts.
- Recommends default evaluation path, not immediate implementation.
</acceptance_criteria>
</task>

<task id="T2" type="execute">
<title>Create retention lifecycle modernization</title>
<action>
Create `07-RETENTION-LIFECYCLE.md` defining storage lifecycle/retention model and safety gates replacing SSIS delete/cleanup tasks after migration.
</action>
<acceptance_criteria>
- Contains candidate/work/validated/archive separation.
- Contains partner-facing path safety rule.
- Covers non-file artifacts.
- Separates retention policy from v1.
</acceptance_criteria>
</task>

<task id="T3" type="execute">
<title>Create partner migration plan</title>
<action>
Create `07-PARTNER-MIGRATION.md` defining communication, versioning, compatibility period, evidence, rollback, and approval gates for post-migration delivery modernization.
</action>
<acceptance_criteria>
- Contains DNS/protocol/path/auth change gates.
- Contains compatibility period.
- Contains rollback plan.
- States v1 remains unchanged.
</acceptance_criteria>
</task>

<task id="T4" type="execute">
<title>Update state and traceability</title>
<action>
Update `.planning/STATE.md`, `.planning/REQUIREMENTS.md`, and `.planning/ROADMAP.md` to reflect Phase 7 planning completion and implementation blockers.
</action>
<acceptance_criteria>
- DELIV-01, DELIV-02, and DELIV-03 are marked specified.
- Current focus is Phase 7.
- Roadmap next phase says planning is complete and implementation awaits approval.
</acceptance_criteria>
</task>

</tasks>

<verification>

Run these checks:

```bash
test -f .planning/phases/07-post-migration-delivery-modernization/07-DELIVERY-OPTIONS.md
test -f .planning/phases/07-post-migration-delivery-modernization/07-RETENTION-LIFECYCLE.md
test -f .planning/phases/07-post-migration-delivery-modernization/07-PARTNER-MIGRATION.md
rg -n "private|SFTP|FTPS|object storage|API|non-file" .planning/phases/07-post-migration-delivery-modernization/07-DELIVERY-OPTIONS.md
rg -n "candidate/work|candidate/validated|candidate/archive|partner-facing|retention|lifecycle" .planning/phases/07-post-migration-delivery-modernization/07-RETENTION-LIFECYCLE.md
rg -n "DNS|protocol|path|auth|compatibility period|rollback|v1 remains unchanged" .planning/phases/07-post-migration-delivery-modernization/07-PARTNER-MIGRATION.md
```

</verification>

<success_criteria>
1. Delivery modernization is specified as a post-migration option set.
2. v1 migration remains contract-compatible and unchanged.
3. Private communication and non-file artifact handling are covered.
4. Partner-visible changes require separate approval and communication.
</success_criteria>
