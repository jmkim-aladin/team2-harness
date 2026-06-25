---
phase: 2
phase_name: Spring Batch Architecture Baseline
plan: 02
type: execute
wave: 1
depends_on:
  - 01-dtsx-evidence-lock
files_modified:
  - .planning/phases/02-spring-batch-architecture-baseline/02-CONTEXT.md
  - .planning/phases/02-spring-batch-architecture-baseline/02-RESEARCH.md
  - .planning/phases/02-spring-batch-architecture-baseline/02-PLAN.md
  - .planning/phases/02-spring-batch-architecture-baseline/02-ARCHITECTURE.md
  - .planning/phases/02-spring-batch-architecture-baseline/02-BATCH-MAPPING.md
  - .planning/phases/02-spring-batch-architecture-baseline/02-OPERATIONS.md
autonomous: true
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

# Phase 2 Plan: Spring Batch Architecture Baseline

<objective>
Create the architecture baseline for the new Kotlin + Spring Boot 4.1.x + Spring Batch 6.0.x `partner-integration-batch` application. Define package boundaries, ports, Spring Batch mapping, manifest/lock/artifact lifecycle, and approval gates. Do not implement production code or access DB/prod systems.
</objective>

<must_haves>
- Architecture uses Kotlin and Spring Boot 4.1.x + Spring Batch 6.0.x.
- Architecture treats the domain as partner integration artifact, not file-only feed.
- Spring Batch metadata and `IntegrationManifest` responsibilities are separate.
- Existing SP/SQL is isolated behind typed `LegacyDbAdapter` methods.
- JobParameters distinguish restart, rebuild, shadow, and retransfer semantics.
- v1 delivery is a compatibility bridge for file/HTTP/FTP/API; modernization is deferred.
- Row 15 remains blocked until G1 SQL Agent evidence confirms exact scope.
- No repo creation, DB/prod access, YouTrack/KB changes, commit, push, or PR occurs in this phase.
</must_haves>

<tasks>

<task id="T1" type="execute">
<title>Create architecture baseline document</title>
<read_first>
- `.planning/PROJECT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/LEDGER.md`
- `.planning/research/STACK.md`
- `.planning/research/ARCHITECTURE.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-CONTEXT.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-RESEARCH.md`
</read_first>
<action>
Create `.planning/phases/02-spring-batch-architecture-baseline/02-ARCHITECTURE.md`. It must define the target repo path `/Users/jm/Documents/workspace/b2b/partner-integration-batch`, root package `kr.co.aladin.partner.integration.batch`, modular monolith decision, package boundaries `app`, `batch`, `contract`, `legacy`, `artifact`, `manifest`, `validation`, `delivery`, and `feed.*`, and the required ports `LegacyDbAdapter`, `IntegrationArtifactGenerator`, `ArtifactStore`, `IntegrationValidator`, `IntegrationPublisher`, `IntegrationManifestRepository`, `IntegrationLockService`, and `ReadbackSmokeClient`.
</action>
<acceptance_criteria>
- `02-ARCHITECTURE.md` contains `Kotlin + Spring Boot 4.1.x + Spring Batch 6.0.x`.
- `02-ARCHITECTURE.md` contains `/Users/jm/Documents/workspace/b2b/partner-integration-batch`.
- `02-ARCHITECTURE.md` contains `kr.co.aladin.partner.integration.batch`.
- `02-ARCHITECTURE.md` contains all package names `app`, `batch`, `contract`, `legacy`, `artifact`, `manifest`, `validation`, `delivery`, and `feed.*`.
- `02-ARCHITECTURE.md` states that Gradle submodules are deferred.
- `02-ARCHITECTURE.md` states that `naverranking` is disabled or blocked until G1 evidence resolves row 15.
</acceptance_criteria>
</task>

<task id="T2" type="execute">
<title>Create SSIS to Spring Batch mapping document</title>
<read_first>
- `.planning/LEDGER.md`
- `.planning/research/PITFALLS.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-RESEARCH.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-ARCHITECTURE.md`
</read_first>
<action>
Create `.planning/phases/02-spring-batch-architecture-baseline/02-BATCH-MAPPING.md`. It must map SSIS Package, Control Flow, Data Flow, Execute SQL Task, Script Task, Precedence Constraint, Foreach Loop, Error Output, and Checkpoint to Kotlin/Spring Batch constructs. It must define the canonical flow `validateParameters -> acquireIntegrationLock -> legacyPrepareSnapshot -> generateWorkArtifacts -> validateArtifacts -> recordManifestValidated -> publishToCompatibilityTarget -> readbackSmoke -> markRunComplete`. It must define JobParameters with identifying `integrationId`, `mode`, `businessDate`, `contractVersion`, `runPurpose`, non-identifying `forceRebuild`, `requestedBy`, `reason`, and retransfer identifying `retransferArtifactId`, `targetAlias`, `attemptKey`.
</action>
<acceptance_criteria>
- `02-BATCH-MAPPING.md` contains each SSIS concept listed in the action.
- `02-BATCH-MAPPING.md` contains `TaskletStep`, `JobExecutionDecider`, `ExitStatus`, `ExecutionContext`, and `JobRepository`.
- `02-BATCH-MAPPING.md` contains `runPurpose`.
- `02-BATCH-MAPPING.md` states `shadowRun` cannot be a non-identifying flag if it changes publish semantics.
- `02-BATCH-MAPPING.md` states full feed processing must use paging/range/partition readers and streaming writers.
- `02-BATCH-MAPPING.md` states retransfer must not execute DB/SP/generation steps.
</acceptance_criteria>
</task>

<task id="T3" type="execute">
<title>Create manifest, artifact, delivery, and operations document</title>
<read_first>
- `.planning/REQUIREMENTS.md`
- `.planning/LEDGER.md`
- `.planning/research/PITFALLS.md`
- `.planning/phases/01-dtsx-evidence-lock/01-SUMMARY.md`
- `.planning/phases/01-dtsx-evidence-lock/01-VERIFICATION.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-RESEARCH.md`
</read_first>
<action>
Create `.planning/phases/02-spring-batch-architecture-baseline/02-OPERATIONS.md`. It must define `integration_run`, `integration_artifact`, `integration_publish_attempt`, `integration_validation_result`, and `integration_manifest_event`. It must define artifact zones `work`, `validated`, and `archive`. It must define the lock key `integrationId + mode + businessDate + contractVersion + targetAlias`. It must define compatibility publishers `FilePublisher`, `StaticHttpFilePublisher`, `FtpPublisher`, and `ApiPublisher`. It must define approval points for runtime account, private network allowlist, secret source, SQL Agent, operational DTSX, SP definitions, golden outputs, and publish/readback access.
</action>
<acceptance_criteria>
- `02-OPERATIONS.md` contains all five manifest table/document names.
- `02-OPERATIONS.md` contains status path `PLANNED -> LOCKED -> PREPARING -> GENERATING -> VALIDATING -> VALIDATED -> PUBLISHING -> PUBLISHED -> READBACK_PASSED -> COMPLETED`.
- `02-OPERATIONS.md` contains `work/{integrationId}/{businessDate}/{runId}`.
- `02-OPERATIONS.md` states publish must use validated artifacts, not work output.
- `02-OPERATIONS.md` contains all four publisher class names.
- `02-OPERATIONS.md` states delivery modernization is v2 after DB migration.
</acceptance_criteria>
</task>

<task id="T4" type="execute">
<title>Update project state and requirement traceability</title>
<read_first>
- `.planning/STATE.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-ARCHITECTURE.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-BATCH-MAPPING.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-OPERATIONS.md`
</read_first>
<action>
Update `.planning/STATE.md` so the current focus is Phase 2 architecture baseline planning, and update `.planning/REQUIREMENTS.md` traceability for ARCH-01, ARCH-02, ARCH-03, ARCH-04, BATCH-01, BATCH-02, BATCH-03, BATCH-04, OPS-01, OPS-02, and OPS-04 to Planned. Update `.planning/ROADMAP.md` next phase guidance to point to `/gsd:execute-phase 2` after plan verification.
</action>
<acceptance_criteria>
- `.planning/STATE.md` contains `Phase 2 - Spring Batch Architecture Baseline`.
- `.planning/STATE.md` contains `/gsd:execute-phase 2`.
- `.planning/REQUIREMENTS.md` marks all Phase 2 requirement IDs as `Planned`.
- `.planning/ROADMAP.md` contains `/gsd:execute-phase 2`.
</acceptance_criteria>
</task>

</tasks>

<verification>

Run these checks:

```bash
test -f .planning/phases/02-spring-batch-architecture-baseline/02-ARCHITECTURE.md
test -f .planning/phases/02-spring-batch-architecture-baseline/02-BATCH-MAPPING.md
test -f .planning/phases/02-spring-batch-architecture-baseline/02-OPERATIONS.md
rg -n "Kotlin \\+ Spring Boot 4\\.1\\.x \\+ Spring Batch 6\\.0\\.x|kr\\.co\\.aladin\\.partner\\.integration\\.batch|LegacyDbAdapter|IntegrationPublisher|IntegrationManifestRepository" .planning/phases/02-spring-batch-architecture-baseline
rg -n "Package|Control Flow|Data Flow|Execute SQL Task|Script Task|Precedence Constraint|Foreach Loop|Error Output|Checkpoint|runPurpose|retransferArtifactId" .planning/phases/02-spring-batch-architecture-baseline/02-BATCH-MAPPING.md
rg -n "integration_run|integration_artifact|integration_publish_attempt|integration_validation_result|integration_manifest_event|FilePublisher|StaticHttpFilePublisher|FtpPublisher|ApiPublisher|delivery modernization is v2" .planning/phases/02-spring-batch-architecture-baseline/02-OPERATIONS.md
rg -n "ARCH-01.*Planned|BATCH-01.*Planned|OPS-01.*Planned" .planning/REQUIREMENTS.md
```

</verification>

<success_criteria>
1. Phase 2 has explicit architecture, batch mapping, and operations design documents.
2. All Phase 2 requirements are covered by concrete deliverables.
3. The design keeps Kotlin/Spring Batch as the implementation baseline.
4. The design preserves the file/HTTP/FTP/API compatibility bridge and avoids file-only naming.
5. The design does not require DB/prod access or repo creation.
</success_criteria>
