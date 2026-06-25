---
phase: 8
phase_name: Repo Skeleton Implementation
plan: 08
type: execute
status: executed
created: 2026-06-19
requirements:
  - ARCH-01
  - ARCH-02
  - ARCH-03
  - BATCH-01
  - BATCH-02
  - FEED-05
  - OPS-01
  - VAL-04
---

# Phase 8 Plan: Repo Skeleton Implementation

## Objective

Create the standalone Kotlin Spring Batch repo and implement the first local vertical slice without touching external systems.

## Tasks

1. Create `/Users/jm/Documents/workspace/b2b/partner-integration-batch`.
2. Add Gradle wrapper and Boot 4/Kotlin 2.2 build files.
3. Implement common contracts, job parameters, manifest models, artifact store, validator, publisher, and no-op legacy adapter.
4. Implement `kakaoDaumFeedJob` tasklet flow.
5. Add unit tests for parameter parsing, validation blocking, and manifest separation.
6. Run local smoke with golden comparison disabled to verify artifact and manifest creation.

## Acceptance

- `./gradlew test` passes.
- `kakaoDaumFeedJob` local smoke completes.
- Exactly six Kakao/Daum XML artifacts are created.
- Manifest has completed run, validation report, publish attempt, and event log.
- Default validation still blocks SSIS equivalence when golden comparison is required.
