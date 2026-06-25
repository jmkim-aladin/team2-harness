# Project State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-06-19)

**Core value:** 기존 SSIS가 생성하던 파트너 연동 산출물을 검증 가능한 Spring Batch 실행 단위로 재현하고, 이관 중에는 기존 파일/HTTP/FTP/API 제공 계약을 깨지 않는다.
**Current focus:** Phase 53 완료 - 준비도와 승인 패킷 메시지 한글화

## Status

- Project initialized: 2026-06-19
- Current phase: Phase 53
- Current mode: 실제 운영 read-only fragment 필요
- Commit status: b2b repo는 `d4bf29e`까지 로컬 커밋 완료. Phase 53 readiness/approval 메시지 한글화가 로컬 커밋되어 있고, team2 planning/harness 변경은 push되지 않았으며 일부는 커밋되지 않은 상태다.
- Instruction file generation: skipped. Existing team2 `AGENTS.md` is source of truth and should not be regenerated automatically.

## Multi-Agent Notes

GSD required agents were not installed for this runtime:

- `gsd-project-researcher`
- `gsd-research-synthesizer`
- `gsd-roadmapper`

Fallback used:

- `multi_agent_v1` explorer for DTSX inventory/reverse engineering
- `multi_agent_v1` explorer for Spring Batch architecture
- `multi_agent_v1` explorer for operations/validation/roadmap

## Locked User Decisions

- Use recommended baseline.
- Build a new standalone Kotlin + Spring Boot + Spring Batch app in a new repo.
- Kotlin is mandatory. Spring baseline is Spring Boot 4.1.x, Spring Batch 6.0.x, Kotlin 2.2+.
- New repo name/path: `/Users/jm/Documents/workspace/b2b/partner-integration-batch`.
- Treat DTSX as current batch specification, not as source code to auto-convert.
- Wrap existing SP/SQL with `LegacyDbAdapter` for first migration.
- File delivery/protocol/path modernization is after DB migration, not part of v1.
- Internal model is partner integration artifact, not file-only. File/HTTP/FTP/API are delivery contracts behind a compatibility bridge.

## Open Decisions

- SQL Agent active package confirmation approval.
- Repo owner, JobRepository metadata DB, and feed manifest/artifact storage location.
- Orchestrator/scheduler choice for cross-DTSX dependencies.
- full/today split as separate jobs or one parameterized job.
- row 15 exact scope after active job confirmation.
- feed-by-feed vs bundled cutover.
- candidate storage/runtime account/alert route for shadow execution.

## Blockers

- No implementation until active SQL Agent package/job/schedule is confirmed.
- No equivalence claim until golden outputs are secured.
- No shadow-run proof until candidate storage, manifest store, and readback target are approved.
- No production cutover without human approval and rollback plan.
- No schedule disable/enable without G5 human cutover approval.
- No file delivery modernization in v1.
- No delivery modernization implementation until v1 migration is stable and separately approved.
- No SSIS equivalence claim from local placeholder artifacts.
- No SQL Agent canonical package claim from local DTSX inventory alone.
- No G1 pass claim from imported placeholder/template fragments.
- No operator evidence overwrite without explicit `allow-overwrite`.
- No production lock store/takeover claim before G2 storage decision.
- No partner-facing retransfer claim until G5 cutover/publish approval.
- No real G1 evidence pass claim until operator `READ_ONLY_EXPORT` fragments for SQL Agent/SP/golden/publish/runtime are available and imported.

## Completed Planning Artifacts

- `.planning/LEDGER.md` - initial SSIS equivalence ledger
- `.planning/phases/01-dtsx-evidence-lock/01-CONTEXT.md`
- `.planning/phases/01-dtsx-evidence-lock/01-RESEARCH.md`
- `.planning/phases/01-dtsx-evidence-lock/01-PLAN.md`
- `.planning/phases/01-dtsx-evidence-lock/01-SUMMARY.md`
- `.planning/phases/01-dtsx-evidence-lock/01-VERIFICATION.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-CONTEXT.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-RESEARCH.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-PLAN.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-ARCHITECTURE.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-BATCH-MAPPING.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-OPERATIONS.md`
- `.planning/phases/03-validation-harness-specification/03-CONTEXT.md`
- `.planning/phases/03-validation-harness-specification/03-RESEARCH.md`
- `.planning/phases/03-validation-harness-specification/03-PLAN.md`
- `.planning/phases/03-validation-harness-specification/03-GOLDEN-SET.md`
- `.planning/phases/03-validation-harness-specification/03-VALIDATION-HARNESS.md`
- `.planning/phases/03-validation-harness-specification/03-SHADOW-RUN.md`
- `.planning/phases/03-validation-harness-specification/03-SUMMARY.md`
- `.planning/phases/03-validation-harness-specification/03-VERIFICATION.md`
- `.planning/phases/04-feed-job-design-and-first-conversion-plan/04-CONTEXT.md`
- `.planning/phases/04-feed-job-design-and-first-conversion-plan/04-RESEARCH.md`
- `.planning/phases/04-feed-job-design-and-first-conversion-plan/04-PLAN.md`
- `.planning/phases/04-feed-job-design-and-first-conversion-plan/04-NAVER.md`
- `.planning/phases/04-feed-job-design-and-first-conversion-plan/04-GOOGLE.md`
- `.planning/phases/04-feed-job-design-and-first-conversion-plan/04-KAKAO-DAUM.md`
- `.planning/phases/04-feed-job-design-and-first-conversion-plan/04-FIRST-SLICE.md`
- `.planning/phases/04-feed-job-design-and-first-conversion-plan/04-SUMMARY.md`
- `.planning/phases/04-feed-job-design-and-first-conversion-plan/04-VERIFICATION.md`
- `.planning/phases/05-shadow-run-and-operational-hardening/05-CONTEXT.md`
- `.planning/phases/05-shadow-run-and-operational-hardening/05-RESEARCH.md`
- `.planning/phases/05-shadow-run-and-operational-hardening/05-PLAN.md`
- `.planning/phases/05-shadow-run-and-operational-hardening/05-SHADOW-LIFECYCLE.md`
- `.planning/phases/05-shadow-run-and-operational-hardening/05-OPERATIONAL-HARDENING.md`
- `.planning/phases/05-shadow-run-and-operational-hardening/05-RUNBOOK.md`
- `.planning/phases/05-shadow-run-and-operational-hardening/05-SUMMARY.md`
- `.planning/phases/05-shadow-run-and-operational-hardening/05-VERIFICATION.md`
- `.planning/phases/06-incremental-cutover-plan/06-CONTEXT.md`
- `.planning/phases/06-incremental-cutover-plan/06-RESEARCH.md`
- `.planning/phases/06-incremental-cutover-plan/06-PLAN.md`
- `.planning/phases/06-incremental-cutover-plan/06-CUTOVER-CHECKLIST.md`
- `.planning/phases/06-incremental-cutover-plan/06-SCHEDULE-ROLLBACK.md`
- `.planning/phases/06-incremental-cutover-plan/06-RELEASE-NOTE.md`
- `.planning/phases/06-incremental-cutover-plan/06-SUMMARY.md`
- `.planning/phases/06-incremental-cutover-plan/06-VERIFICATION.md`
- `.planning/phases/07-post-migration-delivery-modernization/07-CONTEXT.md`
- `.planning/phases/07-post-migration-delivery-modernization/07-RESEARCH.md`
- `.planning/phases/07-post-migration-delivery-modernization/07-PLAN.md`
- `.planning/phases/07-post-migration-delivery-modernization/07-DELIVERY-OPTIONS.md`
- `.planning/phases/07-post-migration-delivery-modernization/07-RETENTION-LIFECYCLE.md`
- `.planning/phases/07-post-migration-delivery-modernization/07-PARTNER-MIGRATION.md`
- `.planning/phases/07-post-migration-delivery-modernization/07-SUMMARY.md`
- `.planning/phases/07-post-migration-delivery-modernization/07-VERIFICATION.md`
- `.planning/phases/08-repo-skeleton-implementation/08-CONTEXT.md`
- `.planning/phases/08-repo-skeleton-implementation/08-PLAN.md`
- `.planning/phases/08-repo-skeleton-implementation/08-SUMMARY.md`
- `.planning/phases/08-repo-skeleton-implementation/08-VERIFICATION.md`
- `.planning/phases/09-feed-skeleton-expansion/09-CONTEXT.md`
- `.planning/phases/09-feed-skeleton-expansion/09-PLAN.md`
- `.planning/phases/09-feed-skeleton-expansion/09-SUMMARY.md`
- `.planning/phases/09-feed-skeleton-expansion/09-VERIFICATION.md`
- `.planning/phases/10-dtsx-inventory-extractor/10-CONTEXT.md`
- `.planning/phases/10-dtsx-inventory-extractor/10-PLAN.md`
- `.planning/phases/10-dtsx-inventory-extractor/10-SUMMARY.md`
- `.planning/phases/10-dtsx-inventory-extractor/10-VERIFICATION.md`
- `.planning/phases/11-control-flow-evidence-extraction/11-CONTEXT.md`
- `.planning/phases/11-control-flow-evidence-extraction/11-PLAN.md`
- `.planning/phases/11-control-flow-evidence-extraction/11-SUMMARY.md`
- `.planning/phases/11-control-flow-evidence-extraction/11-VERIFICATION.md`
- `.planning/phases/12-spring-batch-spec-generation/12-CONTEXT.md`
- `.planning/phases/12-spring-batch-spec-generation/12-PLAN.md`
- `.planning/phases/12-spring-batch-spec-generation/12-SUMMARY.md`
- `.planning/phases/12-spring-batch-spec-generation/12-VERIFICATION.md`
- `.planning/phases/13-golden-comparison-harness/13-CONTEXT.md`
- `.planning/phases/13-golden-comparison-harness/13-PLAN.md`
- `.planning/phases/13-golden-comparison-harness/13-SUMMARY.md`
- `.planning/phases/13-golden-comparison-harness/13-VERIFICATION.md`
- `.planning/phases/14-equivalence-gate/14-CONTEXT.md`
- `.planning/phases/14-equivalence-gate/14-PLAN.md`
- `.planning/phases/14-equivalence-gate/14-SUMMARY.md`
- `.planning/phases/14-equivalence-gate/14-VERIFICATION.md`
- `.planning/phases/15-contract-format-validation/15-CONTEXT.md`
- `.planning/phases/15-contract-format-validation/15-PLAN.md`
- `.planning/phases/15-contract-format-validation/15-SUMMARY.md`
- `.planning/phases/15-contract-format-validation/15-VERIFICATION.md`
- `.planning/phases/16-g1-evidence-pack-validation/16-CONTEXT.md`
- `.planning/phases/16-g1-evidence-pack-validation/16-PLAN.md`
- `.planning/phases/16-g1-evidence-pack-validation/16-SUMMARY.md`
- `.planning/phases/16-g1-evidence-pack-validation/16-VERIFICATION.md`
- `.planning/phases/17-local-publish-readback-harness/17-CONTEXT.md`
- `.planning/phases/17-local-publish-readback-harness/17-PLAN.md`
- `.planning/phases/17-local-publish-readback-harness/17-REVIEW.md`
- `.planning/phases/17-local-publish-readback-harness/17-SUMMARY.md`
- `.planning/phases/17-local-publish-readback-harness/17-VERIFICATION.md`
- `.planning/phases/18-g1-evidence-template-generation/18-CONTEXT.md`
- `.planning/phases/18-g1-evidence-template-generation/18-PLAN.md`
- `.planning/phases/18-g1-evidence-template-generation/18-SUMMARY.md`
- `.planning/phases/18-g1-evidence-template-generation/18-VERIFICATION.md`
- `.planning/phases/19-g1-evidence-directory-import/19-CONTEXT.md`
- `.planning/phases/19-g1-evidence-directory-import/19-PLAN.md`
- `.planning/phases/19-g1-evidence-directory-import/19-SUMMARY.md`
- `.planning/phases/19-g1-evidence-directory-import/19-VERIFICATION.md`
- `.planning/phases/20-g1-fragment-template-directory-generation/20-CONTEXT.md`
- `.planning/phases/20-g1-fragment-template-directory-generation/20-PLAN.md`
- `.planning/phases/20-g1-fragment-template-directory-generation/20-SUMMARY.md`
- `.planning/phases/20-g1-fragment-template-directory-generation/20-VERIFICATION.md`
- `.planning/phases/21-domain-run-lock/21-CONTEXT.md`
- `.planning/phases/21-domain-run-lock/21-PLAN.md`
- `.planning/phases/21-domain-run-lock/21-SUMMARY.md`
- `.planning/phases/21-domain-run-lock/21-VERIFICATION.md`
- `.planning/phases/22-rebuild-retransfer-intent-separation/22-CONTEXT.md`
- `.planning/phases/22-rebuild-retransfer-intent-separation/22-PLAN.md`
- `.planning/phases/22-rebuild-retransfer-intent-separation/22-SUMMARY.md`
- `.planning/phases/22-rebuild-retransfer-intent-separation/22-VERIFICATION.md`
- `.planning/phases/23-manifest-based-retransfer/23-CONTEXT.md`
- `.planning/phases/23-manifest-based-retransfer/23-PLAN.md`
- `.planning/phases/23-manifest-based-retransfer/23-SUMMARY.md`
- `.planning/phases/23-manifest-based-retransfer/23-VERIFICATION.md`
- `.planning/phases/24-local-smoke-matrix-runner/24-CONTEXT.md`
- `.planning/phases/24-local-smoke-matrix-runner/24-PLAN.md`
- `.planning/phases/24-local-smoke-matrix-runner/24-SUMMARY.md`
- `.planning/phases/24-local-smoke-matrix-runner/24-VERIFICATION.md`
- `.planning/phases/25-local-smoke-contract-gate/25-CONTEXT.md`
- `.planning/phases/25-local-smoke-contract-gate/25-PLAN.md`
- `.planning/phases/25-local-smoke-contract-gate/25-SUMMARY.md`
- `.planning/phases/25-local-smoke-contract-gate/25-VERIFICATION.md`
- `.planning/phases/26-migration-readiness-bundle/26-CONTEXT.md`
- `.planning/phases/26-migration-readiness-bundle/26-PLAN.md`
- `.planning/phases/26-migration-readiness-bundle/26-SUMMARY.md`
- `.planning/phases/26-migration-readiness-bundle/26-VERIFICATION.md`
- `.planning/phases/27-dtsx-spec-coverage-gate/27-CONTEXT.md`
- `.planning/phases/27-dtsx-spec-coverage-gate/27-PLAN.md`
- `.planning/phases/27-dtsx-spec-coverage-gate/27-SUMMARY.md`
- `.planning/phases/27-dtsx-spec-coverage-gate/27-VERIFICATION.md`
- `.planning/phases/28-dtsx-manual-review-worklist/28-CONTEXT.md`
- `.planning/phases/28-dtsx-manual-review-worklist/28-PLAN.md`
- `.planning/phases/28-dtsx-manual-review-worklist/28-SUMMARY.md`
- `.planning/phases/28-dtsx-manual-review-worklist/28-VERIFICATION.md`
- `.planning/phases/29-manual-file-operation-building-blocks/29-CONTEXT.md`
- `.planning/phases/29-manual-file-operation-building-blocks/29-PLAN.md`
- `.planning/phases/29-manual-file-operation-building-blocks/29-SUMMARY.md`
- `.planning/phases/29-manual-file-operation-building-blocks/29-VERIFICATION.md`
- `.planning/phases/30-partitioned-multi-file-writer/30-CONTEXT.md`
- `.planning/phases/30-partitioned-multi-file-writer/30-PLAN.md`
- `.planning/phases/30-partitioned-multi-file-writer/30-SUMMARY.md`
- `.planning/phases/30-partitioned-multi-file-writer/30-VERIFICATION.md`
- `.planning/phases/31-derived-file-generation-building-block/31-CONTEXT.md`
- `.planning/phases/31-derived-file-generation-building-block/31-PLAN.md`
- `.planning/phases/31-derived-file-generation-building-block/31-SUMMARY.md`
- `.planning/phases/31-derived-file-generation-building-block/31-VERIFICATION.md`
- `.planning/phases/32-manual-operation-tasklet-adapters/32-CONTEXT.md`
- `.planning/phases/32-manual-operation-tasklet-adapters/32-PLAN.md`
- `.planning/phases/32-manual-operation-tasklet-adapters/32-SUMMARY.md`
- `.planning/phases/32-manual-operation-tasklet-adapters/32-VERIFICATION.md`
- `.planning/phases/33-manual-implementation-coverage-gate/33-CONTEXT.md`
- `.planning/phases/33-manual-implementation-coverage-gate/33-PLAN.md`
- `.planning/phases/33-manual-implementation-coverage-gate/33-SUMMARY.md`
- `.planning/phases/33-manual-implementation-coverage-gate/33-VERIFICATION.md`
- `.planning/phases/34-integration-exchange-contract-catalog/34-CONTEXT.md`
- `.planning/phases/34-integration-exchange-contract-catalog/34-PLAN.md`
- `.planning/phases/34-integration-exchange-contract-catalog/34-SUMMARY.md`
- `.planning/phases/34-integration-exchange-contract-catalog/34-VERIFICATION.md`
- `.planning/phases/35-exchange-catalog-readiness-gate/35-CONTEXT.md`
- `.planning/phases/35-exchange-catalog-readiness-gate/35-PLAN.md`
- `.planning/phases/35-exchange-catalog-readiness-gate/35-SUMMARY.md`
- `.planning/phases/35-exchange-catalog-readiness-gate/35-VERIFICATION.md`

## Implemented Code Artifacts

- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/build.gradle.kts`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/app/PartnerIntegrationBatchApplication.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/batch/KakaoDaumJobConfig.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/batch/KakaoDaumJobTasklets.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/contract/FeedContractRegistry.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/feed/ConfiguredFeedArtifactGenerator.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/manifest/FileBackedIntegrationManifestRepository.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/feed/kakaodaum/KakaoDaumArtifactGenerator.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/manualops/ManualFileOperationModels.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/manualops/ManualFileOperationSupport.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/manualops/ArtifactCopyOperationService.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/manualops/EncodingTranscodeOperationService.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/manualops/RetentionCleanupOperationService.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/manualops/PartitionedMultiFileWriterService.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/manualops/DerivedFileGenerationService.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/batch/ManualOperationTasklets.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/exchange/IntegrationExchangeModels.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/exchange/IntegrationExchangeCatalog.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/exchange/IntegrationExchangeCatalogCommandLineRunner.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/manualops/ArtifactCopyOperationServiceTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/manualops/EncodingTranscodeOperationServiceTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/manualops/RetentionCleanupOperationServiceTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/manualops/PartitionedMultiFileWriterServiceTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/manualops/DerivedFileGenerationServiceTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/batch/ManualOperationTaskletsTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/exchange/IntegrationExchangeCatalogTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/dtsx/DtsxInventory.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/dtsx/DtsxInventoryParser.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/dtsx/DtsxInventoryCommandLineRunner.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/dtsx/DtsxInventoryParserTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/dtsxspec/DtsxMigrationSpec.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/dtsxspec/DtsxMigrationSpecGenerator.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/dtsxspec/DtsxMigrationSpecCommandLineRunner.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/dtsxspec/DtsxMigrationSpecGeneratorTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/dtsxspec/DtsxSpecCoverage.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/dtsxspec/DtsxSpecCoverageEvaluator.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/dtsxspec/DtsxSpecCoverageCommandLineRunner.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/dtsxspec/DtsxSpecCoverageEvaluatorTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/dtsxspec/DtsxSpecCoverageCommandLineRunnerTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/dtsxspec/DtsxManualReviewWorklist.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/dtsxspec/DtsxManualReviewWorklistGenerator.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/dtsxspec/DtsxManualReviewWorklistCommandLineRunner.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/dtsxspec/DtsxManualReviewWorklistGeneratorTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/dtsxspec/DtsxManualReviewWorklistCommandLineRunnerTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/dtsxspec/DtsxManualImplementationCoverage.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/dtsxspec/DtsxManualImplementationCoverageEvaluator.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/dtsxspec/DtsxManualImplementationCoverageCommandLineRunner.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/dtsxspec/DtsxManualImplementationCoverageEvaluatorTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/dtsxspec/DtsxManualImplementationCoverageCommandLineRunnerTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/validation/GoldenComparison.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/validation/GoldenArtifactComparator.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/validation/GoldenComparisonCommandLineRunner.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/validation/GoldenArtifactComparatorTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/validation/EquivalenceGate.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/validation/EquivalenceGateCommandLineRunner.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/validation/EquivalenceGateTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/validation/ContractFormatValidation.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/validation/ContractFormatValidator.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/validation/ContractFormatValidationCommandLineRunner.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/validation/ContractFormatValidatorTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/g1/G1EvidencePack.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/g1/G1EvidencePackValidator.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/g1/G1EvidenceValidationCommandLineRunner.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/g1/G1EvidenceTemplateGenerator.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/g1/G1EvidenceTemplateCommandLineRunner.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/g1/G1EvidenceImport.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/g1/G1EvidenceDirectoryImporter.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/g1/G1EvidenceImportCommandLineRunner.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/g1/G1EvidenceFragmentWriter.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/g1/G1EvidenceFragmentTemplateCommandLineRunner.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/g1/G1ApprovalDecisionCommandLineRunner.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/g1/G1OperatorExportPreflight.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/g1/G1OperatorExportPreflightCommandLineRunner.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/lock/IntegrationRunLock.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/lock/FileBackedIntegrationRunLockRepository.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/lock/InMemoryIntegrationRunLockRepository.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/batch/IntegrationRunLockJobExecutionListener.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/g1/G1EvidencePackValidatorTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/g1/G1EvidenceTemplateGeneratorTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/g1/G1EvidenceTemplateCommandLineRunnerTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/g1/G1EvidenceTestFixtures.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/g1/G1EvidenceDirectoryImporterTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/g1/G1EvidenceImportCommandLineRunnerTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/g1/G1EvidenceFragmentWriterTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/g1/G1EvidenceFragmentTemplateCommandLineRunnerTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/g1/G1ApprovalDecisionCommandLineRunnerTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/g1/G1OperatorExportPreflightCheckerTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/g1/G1OperatorExportPreflightCommandLineRunnerTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/lock/InMemoryIntegrationRunLockRepositoryTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/lock/FileBackedIntegrationRunLockRepositoryTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/batch/IntegrationRunLockJobExecutionListenerTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/delivery/LocalPublishReadback.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/delivery/LocalPublishReadbackVerifier.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/delivery/LocalPublishReadbackCommandLineRunner.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/smoke/LocalSmokeMatrix.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/smoke/LocalSmokeMatrixRunner.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/smoke/LocalSmokeMatrixCommandLineRunner.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/smoke/LocalSmokeMatrixRunnerTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/smoke/LocalSmokeMatrixCommandLineRunnerTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/delivery/LocalPublishReadbackVerifierTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/readiness/MigrationReadiness.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/readiness/MigrationReadinessEvaluator.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/main/kotlin/kr/co/aladin/partner/integration/batch/readiness/MigrationReadinessCommandLineRunner.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/readiness/MigrationReadinessEvaluatorTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/src/test/kotlin/kr/co/aladin/partner/integration/batch/readiness/MigrationReadinessCommandLineRunnerTest.kt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/build/dtsx-inventory/priority-13-17-inventory.json`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/dtsx-inventory/priority-13-17-inventory.json`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/dtsx-spec/priority-13-17-migration-spec.json`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/dtsx-spec-coverage/sample-report.json`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/dtsx-manual-worklist/sample-report.json`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/golden-comparison/sample-report.json`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/contract-format/sample-report.json`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/equivalence/sample-validation-report.json`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/equivalence/sample-equivalence-report.json`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/g1-evidence/sample-pack.json`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/g1-evidence/template-pack.json`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/g1-evidence/sample-report.json`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/publish-readback/sample-source/daily/feed.txt`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/publish-readback/sample-report.json`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/g1-evidence/import-fragments.md`
- `/Users/jm/Documents/workspace/b2b/partner-integration-batch/docs/readiness/sample-report.json`

## Next Command

```text
Decision Needed: 실제 operator READ_ONLY_EXPORT fragment source-root 또는 접근 경로가 필요하다. Source-root preflight, local approval decision 생성, approval-guarded import는 준비됐지만, SQL Agent package 확인, SP definition, golden-output 비교, SSIS 동등성 증명, schedule cutover, delivery modernization은 아직 실제 증거와 별도 승인이 필요하다.
```
