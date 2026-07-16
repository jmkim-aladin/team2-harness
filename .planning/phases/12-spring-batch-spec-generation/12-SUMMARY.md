---
phase: 12
phase_name: Spring Batch Spec Generation
status: implemented_local_evidence
completed: 2026-06-19
requirements:
  - BATCH-01
  - INV-02
  - INV-03
---

# Phase 12 Summary: Spring Batch Spec Generation

## Result

The Kotlin repo can now convert local DTSX inventory evidence into a Spring Batch migration spec. The generated spec is not production code; it is the rebuild checklist that ties SSIS tasks to Spring Batch mapping candidates.

## Implemented

- `DtsxMigrationSpec`
- `DtsxMigrationSpecGenerator`
- `DtsxMigrationSpecCommandLineRunner`
- `DtsxMigrationSpecGeneratorTest`
- tracked spec JSON:

```text
/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/dtsx-spec/priority-13-17-migration-spec.json
```

## Generated Scope

- Packages: 8
- Step candidates: 77
- Transition candidates: 53
- Manual review step candidates: 17

Manual review currently means Script Task, loop container, or unknown executable type. These are the parts most likely to need Kotlin service/tasklet implementation or a partition/decider design.

## Not Complete

- The generated spec is based on downloaded DTSX files, not SQL Agent canonical deployment evidence.
- Script Task internals still need deeper inspection or reimplementation.
- SP definitions and golden-output validation remain blocked by G1.
