# Phase 31 Plan: Derived File Generation Building Block

## Objective

Implement the local building block for the remaining three DTSX derived-file-generation work items.

## Tasks

1. Add derived generation request/result/status models.
2. Add `DerivedFileGenerationService`.
3. Enforce source name, field count, delimiter/newline, overwrite, symlink, and field safety checks.
4. Add tests for successful generation, field count mismatch, invalid field value, overwrite block, and empty artifact handling.
5. Update README, migration ledger, and GSD state.

## Verification

- focused manualops tests
- full Gradle tests
