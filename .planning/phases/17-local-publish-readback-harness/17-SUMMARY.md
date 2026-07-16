---
phase_name: Local Publish Readback Harness
status: complete
updated: 2026-06-19
---

# Phase 17 Summary: Local Publish Readback Harness

The Kotlin repo now contains a local publish/readback harness for compatibility-bridge smoke evidence.

## Implemented

- `LocalPublishReadbackReport`, file result/status/conclusion models.
- `LocalPublishReadbackVerifier`:
  - discovers source files or accepts explicit relative paths
  - copies files to a local target root
  - reads back target files
  - compares byte count and SHA-256
  - blocks no-file and missing-source cases
- `LocalPublishReadbackCommandLineRunner`.
- `LocalPublishReadbackVerifierTest`.
- Sample source and report under `docs/publish-readback/`.

## Verification

- `./gradlew test --rerun-tasks` passed with 36 tests.
- `./gradlew bootRun` generated `build/local-publish-readback/report.json`.
- `docs/publish-readback/sample-report.json` is kept as a sanitized static sample.
- `jq` confirmed sample conclusion `PASSED`, `totalFiles=1`, `publishedFiles=1`, `failedFiles=0`.
- secret-pattern scan returned no matches for the sample report/source.

## Boundaries

No DB/SP/SQL Agent/prod access, partner-facing publish, FTP/SMB/HTTP/API call, schedule change, delivery modernization, YouTrack/KB update, commit, push, or PR action was performed.

The harness proves only local transfer/readback mechanics. Real SSIS equivalence still requires G1 read-only evidence, real golden outputs, and real publish/readback target proof.
