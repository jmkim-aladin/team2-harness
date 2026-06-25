---
phase_name: G1 Evidence Template Generation
status: complete
updated: 2026-06-19
requirements:
  - INV-04
  - VAL-01
  - VAL-02
  - OPS-04
---

# Phase 18 Plan: G1 Evidence Template Generation

## Goal

Implement a local G1 evidence template generator that prepares the exact JSON shape required after read-only G1 approval.

## Tasks

1. Extract required G1 target list.
   - Verify: validator and generator both use the same required target list.

2. Implement template generator.
   - Verify: every required target has SQL Agent, deployed DTSX, SP, golden output, and publish target placeholders.
   - Verify: golden output placeholders use expected contract file names for the supplied business date.

3. Implement command-line runner.
   - Verify: business date, captured by, optional evidence pack id, optional captured timestamp, and output path are accepted.

4. Add tests.
   - Verify: generated template has all seven required targets.
   - Verify: generated template validation does not pass until real evidence replaces placeholders.

5. Generate deterministic sample template and update docs.
   - Verify: `docs/g1-evidence/template-pack.json` exists.
   - Verify: validation report for the template is `FAILED`, not `PASSED`.

## Success Criteria

- `./gradlew test --rerun-tasks` passes.
- Template runner writes deterministic sample output.
- Validator reports the template as failed until evidence is filled.
- No DB/SP/SQL Agent/prod access occurs.
