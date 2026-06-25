---
phase: 9
phase_name: Feed Skeleton Expansion
plan: 09
type: execute
status: executed
created: 2026-06-19
requirements:
  - FEED-01
  - FEED-02
  - FEED-03
  - FEED-04
  - FEED-05
  - BATCH-01
  - VAL-04
---

# Phase 9 Plan: Feed Skeleton Expansion

## Objective

Make the local Spring Batch skeleton cover all priority feed rows that can be represented without G1 evidence.

## Tasks

1. Replace Kakao/Daum-only tasklets with common `IntegrationJobTasklets`.
2. Add `FeedContractRegistry` for expected artifact file names.
3. Add jobs for Naver book, Naver shopping, Google, Kakao/Daum, and blocked Naver ranking.
4. Add local placeholder generator for non-Kakao configured feeds.
5. Update validation to compare artifacts against registry expected files.
6. Add registry tests.
7. Run tests and local smoke jobs.

## Acceptance

- `./gradlew test` passes.
- Naver book FULL/TODAY smoke runs.
- Naver shopping FULL/TODAY smoke runs.
- Google FULL/TODAY smoke runs.
- Kakao/Daum FULL smoke runs.
- Naver ranking smoke fails with G1 blocked message.
- Artifact count after smoke is 19.
- Manifest run count after successful smoke is 7.
