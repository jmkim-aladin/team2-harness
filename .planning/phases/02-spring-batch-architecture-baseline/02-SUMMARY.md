---
phase: 2
phase_name: Spring Batch Architecture Baseline
status: executed
completed: 2026-06-19
plans:
  - 02-PLAN.md
requirements:
  - ARCH-01
  - ARCH-02
  - ARCH-03
  - ARCH-04
  - BATCH-01
  - BATCH-02
  - BATCH-03
  - BATCH-04
  - OPS-01
  - OPS-02
  - OPS-04
---

# Phase 2 Summary: Spring Batch Architecture Baseline

## Result

Phase 2 created the architecture baseline for the new Kotlin + Spring Boot 4.1.x + Spring Batch 6.0.x `partner-integration-batch` application.

## Created

- `02-ARCHITECTURE.md` - repo/package boundaries, ports, dependency rule, feed job candidates, G1 deferred list
- `02-BATCH-MAPPING.md` - SSIS to Spring Batch mapping, canonical job flow, JobParameters, restart/rebuild/retransfer rules
- `02-OPERATIONS.md` - manifest schema, artifact lifecycle, lock key, delivery bridge, approval matrix, observability

## Key Decisions Locked

- Internal model is partner integration artifact, not file-only feed.
- Start as a modular monolith; Gradle submodules are deferred.
- Use root package `kr.co.aladin.partner.integration.batch`.
- Keep Spring Batch metadata and `IntegrationManifest` separate.
- Keep SP/SQL names inside typed `LegacyDbAdapter` methods only.
- Use `runPurpose` or equivalent identifying parameter so shadow, production, and retransfer runs do not collide.
- Preserve file/HTTP/FTP/API delivery through a v1 compatibility bridge.
- Keep `naverRankingFeedJob` blocked until G1 evidence resolves row 15 scope.

## Not Done By Design

- No repo was created.
- No Kotlin production code was implemented.
- No DB, SP, SQL Agent, production endpoint, YouTrack, KB, git commit, push, PR, or prod changes were made.
- No delivery modernization was started.

## Next

Phase 3 should define the validation harness: golden output collection shape, byte/checksum/row-count comparison, shadow run rules, and publish/readback verification criteria.

Decision G1 is still required before implementation evidence can be treated as canonical.
