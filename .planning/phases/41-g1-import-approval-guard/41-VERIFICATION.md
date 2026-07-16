# Phase 41 Verification - G1 Import Approval Guard

## Commands

```bash
./gradlew test --tests 'kr.co.aladin.partner.integration.batch.g1.G1EvidenceDirectoryImporterTest' --tests 'kr.co.aladin.partner.integration.batch.g1.G1EvidenceImportCommandLineRunnerTest'
```

## Expected

- approval-required import without decision fails before output pack write
- approved import records approval packet id/request id/decision status
- existing non-guarded import still passes
- no external endpoint, DB, SQL Agent, DTSX execution, or partner-facing publish is touched

## Actual

- RED compile failure confirmed before implementation.
- focused importer/runner tests: 8 passed.
- G1 focused suite: 21 passed.
- `PENDING` approval decision template rejected by actual `bootRun` with `G1 approval decision must be APPROVED_READ_ONLY_EXPORT`.
- full Gradle test: 122 tests, 0 failures/errors.
