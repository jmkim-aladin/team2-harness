---
phase: 16
phase_name: G1 Evidence Pack Validation
status: implemented_local_tooling
completed: 2026-06-19
requirements:
  - INV-04
  - VAL-01
  - VAL-02
  - OPS-04
---

# Phase 16 Summary: G1 Evidence Pack Validation

## Result

The Kotlin repo now includes an offline G1 evidence pack validator. It defines the shape of read-only evidence required before active SSIS packages and golden outputs can be treated as canonical.

## Implemented

- `G1EvidencePack`
- `G1EvidencePackValidator`
- `G1EvidenceValidationCommandLineRunner`
- `G1EvidencePackValidatorTest`
- sample pack and report:

```text
/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/g1-evidence/sample-pack.json
/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/g1-evidence/sample-report.json
```

## Gate Behavior

The sample pack has complete shape but `sourceType=SYNTHETIC_SAMPLE`, so the report conclusion is `BLOCKED_SAMPLE_ONLY`. Real G1 can pass only with `sourceType=READ_ONLY_EXPORT` and complete evidence.

## Not Complete

- No real SQL Agent evidence has been collected.
- No deployed DTSX/SP/golden-output evidence has been collected.
- No SSIS equivalence report exists yet for a real feed/businessDate.
