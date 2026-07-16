# Research: Stack

## Recommendation

Use a new standalone repository named `partner-integration-batch` for a Kotlin + Spring Boot 4.1.x + Spring Batch 6.0.x application.

## Core Stack

| Area | Choice | Rationale |
|------|--------|-----------|
| Language | Kotlin | team direction prefers Kotlin for new backend work. |
| Runtime | Spring Boot 4.1.x | current Spring Boot 4 stable line according to official Spring project docs checked on 2026-06-19. |
| Batch engine | Spring Batch 6.0.x | current Batch 6 line aligned with Spring Boot 4 and Spring Framework 7. |
| JVM | Java 25 preferred, Java 17 minimum | Boot 4.1.0 requires Java 17+; use current LTS unless team runtime constrains it. |
| Kotlin | Kotlin 2.2+ | Spring Boot 4 migration guide requires Kotlin 2.2 or later. |
| Repository | New repo | keeps SSIS migration specs, manifests, validation harness, and compatibility bridge isolated from existing B2B batch code. |
| DB access | `JdbcTemplate` or MyBatis behind `LegacyDbAdapter` | keeps existing SP/SQL isolated while allowing typed adapter methods. |
| File generation | Jackson streaming, flat-file writer/custom delimited writer, StAX/Jackson XML | supports JSONL, TXT/TSV, XML without full-memory materialization. |
| Artifact storage | run-scoped work artifact plus immutable archive | enables rebuild/retransfer separation and rollback. |
| Publish bridge | compatibility `FeedPublisher` | v1 preserves existing file delivery contract; protocol modernization is post-migration. |
| Metadata | Spring Batch metadata plus feed manifest | Spring Batch tracks execution, manifest tracks partner artifact contract and validation. |

## Not Chosen For V1

- DTSX-to-Kotlin automatic code generation: keep to report/skeleton level only.
- Pure Spring scheduler with custom pipeline: too much restart/retry/metadata must be rebuilt manually.
- Apache Camel as the primary engine: useful for routing, but weaker fit for SSIS Data Flow equivalence and batch restart semantics.
- File delivery redesign in v1: explicitly deferred until after migration.
- Extending the existing B2B batch repo as the default: useful as reference, but risks coupling this migration to unrelated B2B batch responsibilities.

## Official Version Sources

- Spring Boot project page: `https://spring.io/projects/spring-boot`
- Spring Boot system requirements: `https://docs.spring.io/spring-boot/system-requirements.html`
- Spring Boot 4 migration guide: `https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide`
- Spring Batch project page: `https://spring.io/projects/spring-batch`
- Spring Batch 6 reference: `https://docs.spring.io/spring-batch/reference/whatsnew.html`
