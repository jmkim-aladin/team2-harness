---
phase: 2
phase_name: Spring Batch Architecture Baseline
artifact: architecture
status: drafted
created: 2026-06-19
requirements:
  - ARCH-01
  - ARCH-02
  - ARCH-03
  - ARCH-04
  - OPS-04
---

# Phase 2 Architecture Baseline

## Baseline

The implementation target is a new Kotlin + Spring Boot 4.1.x + Spring Batch 6.0.x application.

- Repo path: `/Users/jm/Documents/workspace/b2b/partner-integration-batch`
- Root package: `kr.co.aladin.partner.integration.batch`
- Runtime model: one Spring Boot batch application as a modular monolith
- Module decision: defer Gradle submodules until package boundaries need compile-time enforcement

The domain model is partner integration artifact, not file-only feed. File, HTTP, FTP, and API delivery are protocol-specific delivery contracts behind a compatibility bridge.

## Package Boundaries

| Package | Responsibility |
|---|---|
| `app` | Spring Boot entrypoint, config binding, Actuator/ops wiring, job launch policy |
| `batch` | Spring Batch `Job`, `Step`, flow, decider, listener, and parameter validation configuration |
| `contract` | `IntegrationId`, `FeedMode`, `ContractVersion`, delivery contract, schema/format contract |
| `legacy` | `LegacyDbAdapter` port and JDBC implementation; SP/SQL names stay here only |
| `artifact` | JSONL/TXT/TSV/XML and future non-file artifact generation; work/validated/archive storage |
| `manifest` | `IntegrationManifest`, run/artifact/validation/publish/readback state, append-only events |
| `validation` | schema, format, checksum, golden/shadow comparison interfaces |
| `delivery` | v1 compatibility bridge for file/HTTP/FTP/API targets |
| `feed.*` | feed-specific contracts and mappings, such as `feed.naverbook`, `feed.navershopping`, `feed.google`, `feed.kakaodaum`, `feed.naverranking` |

`feed.naverranking` is disabled or blocked until G1 evidence resolves row 15 exact scope.

## Required Ports

| Port | Direction | Responsibility |
|---|---|---|
| `LegacyDbAdapter` | outbound | typed legacy SP/SQL and staging calls |
| `IntegrationArtifactGenerator` | internal | converts source rows/snapshots into artifacts |
| `ArtifactStore` | outbound | stores work, validated, and archive artifacts |
| `IntegrationValidator` | internal | validates schema, bytes, counts, checksum, and contract rules |
| `IntegrationPublisher` | outbound | publishes validated artifacts through compatibility target aliases |
| `IntegrationManifestRepository` | outbound | persists run, artifact, validation, publish, readback, and event state |
| `IntegrationLockService` | outbound | prevents duplicate integration/date/target execution |
| `ReadbackSmokeClient` | outbound | verifies partner-visible readback where allowed |

Supporting DTOs:

- `IntegrationJobParameters`
- `IntegrationManifest`
- `ArtifactDescriptor`
- `ValidationReport`
- `PublishResult`

## Dependency Rule

`batch` may orchestrate ports, but it must not contain SP names, publish paths, FTP credentials, static web paths, or partner-specific byte-format details.

```text
batch
  -> contract
  -> legacy port
  -> artifact port
  -> validation port
  -> manifest port
  -> delivery port

feed.*
  -> contract
  -> artifact mapping
  -> validation rules
```

Concrete adapters live under `legacy`, `artifact`, `manifest`, and `delivery`. Secrets are referenced by secret names only and never written to manifests or logs.

## Feed Job Candidates

| Integration | Job | Phase 2 stance |
|---|---|---|
| Naver book | `naverBookFeedJob` | architecture contract only |
| Naver shopping | `naverShoppingFeedJob` | architecture contract only |
| Naver ranking | `naverRankingFeedJob` | disabled/blocked until G1 |
| Google shopping | `googleShoppingFeedJob` | architecture contract only |
| Kakao/Daum | `kakaoDaumFeedJob` | likely first vertical slice after Phase 3 validation spec |
| Retention | `feedRetentionJob` | separate job, not hidden inside publish |

## Deferred Until G1

- exact operational DTSX package and SQL Agent schedule
- row 15 scope
- SP signatures and output DTOs
- side effects, transaction boundaries, ordering, null handling
- exact artifact schemas, delimiters, newline, encoding, and sort contracts
- concrete publisher credentials and private network paths
- production cutover or SSIS schedule changes
