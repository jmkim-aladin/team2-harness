---
phase_name: Local Publish Readback Harness
status: complete
updated: 2026-06-19
---

# Phase 17 Context: Local Publish Readback Harness

Phase 16 added an offline G1 evidence-pack validator, but the codebase still needed a concrete local publish/readback smoke path. The user clarified that the integration model must not be file-only because some integrations may receive data or use non-file payloads later. For v1, however, existing SSIS partner delivery contracts must be preserved until DB migration is stable.

This phase adds a local compatibility-bridge harness. It copies candidate artifacts from a source root to a local target root, reads them back, and records byte count plus SHA-256 evidence. It does not connect to FTP, SMB, HTTP, API, SQL Server, or production endpoints.

## Constraints

- Do not perform DB/SP/SQL Agent/prod access.
- Do not publish to partner-facing targets.
- Do not modernize delivery protocol/path in v1.
- Do not claim SSIS equivalence from local sample data.
- Keep Kotlin + Spring Boot 4.1.x + Spring Batch 6.0.x baseline.

## Evidence Added

- Local model/report: `LocalPublishReadbackReport`
- Local verifier: `LocalPublishReadbackVerifier`
- CLI runner: `LocalPublishReadbackCommandLineRunner`
- Sample source: `docs/publish-readback/sample-source/daily/feed.txt`
- Sanitized sample report: `docs/publish-readback/sample-report.json`
- Runtime sample report path: `build/local-publish-readback/report.json`
