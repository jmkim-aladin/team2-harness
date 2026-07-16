---
phase: 3
phase_name: Validation Harness Specification
status: passed_with_external_evidence_gate
verified: 2026-06-19
requirements:
  - VAL-01
  - VAL-02
  - VAL-03
---

# Phase 3 Verification

## Verification Result

Phase 3 verification passed for local specification artifacts. Real golden file acquisition and production equivalence remain blocked by G1 approval.

## Checks Run

```bash
test -f .planning/phases/03-validation-harness-specification/03-GOLDEN-SET.md
test -f .planning/phases/03-validation-harness-specification/03-VALIDATION-HARNESS.md
test -f .planning/phases/03-validation-harness-specification/03-SHADOW-RUN.md
rg -n "exact raw byte equality|SHA-256|row count|byte count|outside git|Row 15.*G1|row 15.*G1" .planning/phases/03-validation-harness-specification/03-GOLDEN-SET.md
rg -n "IntegrationValidator|ArtifactComparator|ByteFingerprint|JsonlComparator|TxtComparator|TsvComparator|XmlComparator|integration_validation_result|streaming" .planning/phases/03-validation-harness-specification/03-VALIDATION-HARNESS.md
rg -n "runPurpose=SHADOW|candidate/\\{integrationId\\}/\\{mode\\}/\\{businessDate\\}/\\{contractVersion\\}/\\{runId\\}|partner-facing|>150%|>200%|Shadow diff count|shadow diff count" .planning/phases/03-validation-harness-specification/03-SHADOW-RUN.md
rg -n "VAL-01.*G1|VAL-02.*Specified|VAL-03.*Specified" .planning/REQUIREMENTS.md
```

## Acceptance Matrix

| Acceptance | Status | Evidence |
|---|---|---|
| Golden-set specification exists | Passed | `03-GOLDEN-SET.md` |
| Real golden files are kept outside git | Passed | `03-GOLDEN-SET.md` |
| Byte equality default is explicit | Passed | `03-GOLDEN-SET.md`, `03-VALIDATION-HARNESS.md` |
| Validation harness package/classes are specified | Passed | `03-VALIDATION-HARNESS.md` |
| Format comparators cover JSONL.js, TXT, TSV, XML | Passed | `03-VALIDATION-HARNESS.md` |
| Streaming rule exists | Passed | `03-VALIDATION-HARNESS.md` |
| Shadow uses candidate paths only | Passed | `03-SHADOW-RUN.md` |
| Partner-facing target is blocked for shadow | Passed | `03-SHADOW-RUN.md` |
| Phase 3 requirements are traceable | Passed | `.planning/REQUIREMENTS.md` |

## Residual Risk

- Actual golden files are missing until G1 is approved.
- Active SQL Agent package, SP schema, and operational DTSX drift are still unverified.
- Phase 3 proves the validation design, not SSIS equivalence.
