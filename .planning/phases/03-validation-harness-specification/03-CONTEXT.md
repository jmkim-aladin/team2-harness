---
phase: 3
phase_name: Validation Harness Specification
status: ready_for_planning
created: 2026-06-19
requirements:
  - VAL-01
  - VAL-02
  - VAL-03
---

# Phase 3: Validation Harness Specification - Context

## Phase Boundary

Phase 3 defines the validation harness and equivalence criteria for proving that new Kotlin/Spring Batch outputs match current SSIS outputs. It does not collect real production golden files, run DB jobs, access partner-facing paths, or execute shadow runs.

## Locked Decisions

- Default equivalence is exact raw byte equality.
- Any tolerated difference must be feed-specific, approved, documented, and recorded in `integration_validation_result`.
- Real SSIS golden outputs stay outside git.
- Sanitized validation fixtures may live under `src/test/resources` after the repo exists.
- Validation is a runtime harness behind `IntegrationValidator`, not only unit tests.
- `runPurpose=SHADOW` is required for shadow validation. Do not model shadow semantics as a non-identifying boolean only.
- Shadow validation writes only under isolated candidate paths and never to partner-facing FTP/WWW/final paths.
- Row 15 remains excluded from golden/shadow readiness until G1 confirms active scope.

## Canonical References

- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/LEDGER.md`
- `.planning/research/PITFALLS.md`
- `.planning/phases/01-dtsx-evidence-lock/01-SUMMARY.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-ARCHITECTURE.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-BATCH-MAPPING.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-OPERATIONS.md`

## Required Phase 3 Output

- Golden-set collection specification.
- Byte-level and format-aware comparator specification.
- Fixture layout for sanitized tests and external real golden files.
- Shadow-run safety and isolated candidate area rules.
- Failure thresholds and approval gates.
- Manifest recording requirements for validation results and diff artifacts.

## Out Of Scope

- real golden output collection before G1 approval
- DB/SP/SQL Agent reads
- production or partner-facing publish
- repo scaffolding or Kotlin implementation
- cutover readiness claim
