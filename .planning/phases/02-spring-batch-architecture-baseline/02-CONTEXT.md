---
phase: 2
phase_name: Spring Batch Architecture Baseline
status: ready_for_planning
created: 2026-06-19
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

# Phase 2: Spring Batch Architecture Baseline - Context

## Phase Boundary

Phase 2 defines the architecture contract for the new Kotlin + Spring Boot 4.1.x + Spring Batch 6.0.x application. It does not scaffold the repo, implement feed logic, access DB/prod systems, or claim SSIS equivalence.

## Locked Decisions

### Stack

- Kotlin is mandatory.
- Spring baseline is Spring Boot 4.1.x, Spring Batch 6.0.x, Kotlin 2.2+.
- The target repo is `/Users/jm/Documents/workspace/b2b/partner-integration-batch`.
- The app should start as a modular monolith with strong package boundaries. Gradle submodules are deferred unless enforcement becomes necessary.

### Architecture

- Internal model is partner integration artifact, not file-only feed.
- File, HTTP, FTP, and API delivery are v1 compatibility bridge implementations behind an `IntegrationPublisher` port.
- Spring Batch metadata tracks execution mechanics; `IntegrationManifest` tracks partner artifact truth, validation, publish/readback, audit, and operator actions.
- Existing SP/SQL must be isolated behind typed `LegacyDbAdapter` methods. No generic `callSp(name, args)` in batch core.
- Rebuild and retransfer are separate workflows. Retransfer must not rerun DB/SP/generation.
- Row 15 `naverRankingFeedJob` remains disabled/stubbed until active SQL Agent evidence confirms scope.

### Governance

- No DB/SP/prod access without explicit approval.
- No repo creation, commit, push, PR, YouTrack, or KB changes without user confirmation.
- Phase 2 may proceed while G1 evidence waits because it is architecture-only.

## Canonical References

- `.planning/PROJECT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/LEDGER.md`
- `.planning/research/STACK.md`
- `.planning/research/ARCHITECTURE.md`
- `.planning/research/PITFALLS.md`
- `.planning/phases/01-dtsx-evidence-lock/01-SUMMARY.md`
- `.planning/phases/01-dtsx-evidence-lock/01-VERIFICATION.md`
- `/Users/jm/Documents/workspace/team2/policies/gstack-override-policy.md`

## Required Phase 2 Output

- Architecture decision record for repo/package boundaries.
- Batch mapping spec from SSIS Package/Control Flow/Data Flow/Execute SQL/Script/Precedence/Foreach/Error Output/Checkpoint to Spring Batch/Kotlin constructs.
- Port/interface catalog for `LegacyDbAdapter`, artifact generation, validation, publishing, manifest, locking, readback, and job parameters.
- Manifest/lock/artifact lifecycle design.
- Runtime account, private network, secret, and observability approval matrix.
- Explicit deferred list for anything blocked by G1 evidence.
