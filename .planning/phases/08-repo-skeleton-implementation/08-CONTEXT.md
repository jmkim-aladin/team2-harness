---
phase: 8
phase_name: Repo Skeleton Implementation
artifact: context
status: implemented_local_slice
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

# Phase 8 Context: Repo Skeleton Implementation

## Purpose

Phase 8 starts implementation in the new Kotlin Spring Batch repository.

Repo path:

```text
/Users/jm/Documents/workspace/b2b/partner-integration-batch
```

## Scope Implemented

- Gradle Kotlin DSL project with Spring Boot 4.1.0, Spring Batch 6.0.4, Kotlin 2.2.21.
- Spring Batch `kakaoDaumFeedJob` local vertical slice.
- File-backed `IntegrationManifest` ledger.
- Local artifact store.
- No-op `LegacyDbAdapter`.
- No-op `IntegrationPublisher` that skips partner-facing publish for `SHADOW`.
- Basic validator that blocks equivalence when SSIS golden comparison is required.
- Local smoke run that creates six Kakao/Daum XML placeholder artifacts and manifest records.

## Explicit Limits

- No DB/SP/SQL Agent/prod access.
- No partner-facing FTP/HTTP/SMB/API publish.
- No SSIS golden output comparison.
- No equivalence claim.
- No git init, commit, push, PR, YouTrack, or KB change.

Actual SSIS parity remains blocked by G1 evidence and golden outputs.
