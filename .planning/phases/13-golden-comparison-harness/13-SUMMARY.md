---
phase: 13
phase_name: Golden Comparison Harness
status: implemented_local_tooling
completed: 2026-06-19
requirements:
  - VAL-01
  - VAL-02
  - VAL-03
---

# Phase 13 Summary: Golden Comparison Harness

## Result

The Kotlin repo now includes a golden comparison harness. It compares candidate and golden artifact directories, records file-level byte count, line count, SHA-256, and reports whether equivalence is passed, failed, or blocked by missing files.

## Implemented

- `GoldenComparisonReport`
- `GoldenArtifactComparator`
- `GoldenComparisonCommandLineRunner`
- `GoldenArtifactComparatorTest`
- sample report:

```text
/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/golden-comparison/sample-report.json
```

## Sample Report Behavior

The sample intentionally includes one match, one checksum mismatch, and one missing golden file. The report conclusion is `BLOCKED_MISSING_FILES`, which prevents a false equivalence claim.

## Not Complete

- Real SSIS golden files are still missing.
- Golden comparison has not been run against actual Spring Batch candidate output and SSIS output.
- SP/SQL Agent/prod evidence remains blocked by G1 approval.
