# Phase 29 Plan: Manual File Operation Building Blocks

## Objective

Implement local building blocks for DTSX copy/transcode/cleanup Script Task replacements.

## Tasks

1. Add `manualops` models for file stats, copy, transcode, and cleanup results.
2. Add safe path/checksum helper.
3. Add `ArtifactCopyOperationService`.
4. Add `EncodingTranscodeOperationService`.
5. Add `RetentionCleanupOperationService`.
6. Add tests for pass and blocking cases.
7. Document the worklist coverage.

## Verification

- focused manualops tests
- full Gradle tests
