---
phase: 15
phase_name: Contract Format Validation
status: planned
created: 2026-06-19
requirements:
  - VAL-03
---

# Phase 15 Plan: Contract Format Validation

## Tasks

1. Add contract-format report models and statuses.
2. Implement candidate-root validator using `FeedContractRegistry`.
3. Add command-line runner.
4. Add tests for JSONL pass, missing file, malformed XML, and TSV format failure.
5. Generate sample report and wire contract-format report into equivalence gate.

## Verification

- `./gradlew test --rerun-tasks`
- `./gradlew bootRun` with `partner.integration.contract-format.enabled=true`
- `./gradlew bootRun` with `partner.integration.equivalence-gate.enabled=true` and contract-format report
- `jq` report summaries
- secret/password grep over generated reports
