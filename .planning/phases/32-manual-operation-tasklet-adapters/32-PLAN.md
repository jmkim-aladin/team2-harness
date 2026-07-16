# Phase 32 Plan: Manual Operation Tasklet Adapters

## Objective

Connect local manual operation building blocks to Spring Batch Tasklet execution shape.

## Tasks

1. Add `ManualOperationTasklets`.
2. Add execution-context keys for operation status/counts.
3. Fail tasklets when the underlying operation status is blocking.
4. Add tests for success context recording and failure behavior.
5. Update README, migration ledger, and GSD state.

## Verification

- focused tasklet adapter tests
- full Gradle tests
