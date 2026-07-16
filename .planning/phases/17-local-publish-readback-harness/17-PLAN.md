---
phase_name: Local Publish Readback Harness
status: complete
updated: 2026-06-19
requirements:
  - ARCH-04
  - VAL-04
  - OPS-01
---

# Phase 17 Plan: Local Publish Readback Harness

## Goal

Implement a local publish/readback harness that can prove candidate artifact transfer integrity without touching real partner endpoints.

## Tasks

1. Add local publish/readback report models.
   - Verify: model compiles and serializes through existing Jackson configuration.

2. Add verifier service.
   - Verify: copied files are read back with matching byte count and SHA-256.
   - Verify: missing source files, invalid relative paths, no discovered files, and copy/readback mismatch do not pass.

3. Add command-line runner.
   - Verify: runner accepts source root, target root, target alias, optional relative paths, and output path.

4. Add tests.
   - Verify: success, no-file block, and missing-source failure cases pass.

5. Add sample report and documentation.
   - Verify: runner output is generated under `build/local-publish-readback/report.json`.
   - Verify: committed sample report is sanitized under `docs/publish-readback/sample-report.json`.
   - Verify: sample does not contain secrets or production endpoints.

## Success Criteria

- Local source -> target publish/readback runner exists.
- Readback records byte count and SHA-256.
- Sample report is `PASSED` only for the local sample fixture.
- Full Gradle test suite passes.
- README, migration ledger, and GSD ledger mention the harness and its limitations.
