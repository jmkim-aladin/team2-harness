---
phase: 5
phase_name: Shadow Run And Operational Hardening
artifact: context
status: drafted
created: 2026-06-19
requirements:
  - VAL-04
  - OPS-03
---

# Phase 5 Context: Shadow Run And Operational Hardening

## Purpose

Phase 5 defines how the Kotlin Spring Batch replacement proves operational equivalence with the current SSIS schedules before any partner-facing cutover.

This phase is an operational proof design, not a production cutover. The batch app remains based on Spring Boot 4.1.x, Spring Batch 6.0.x, Kotlin 2.2+, and the Phase 2 `IntegrationManifest` domain model.

## Scope

In scope:

- isolated shadow run lifecycle
- manifest fields and audit events needed for publish/readback proof
- restart, manual rebuild, retransfer, rollback runbook
- validation report shape for operator and cutover review
- observability metrics and alert criteria
- Kakao/Daum first-slice operational proof rules

Out of scope:

- repo creation or Kotlin implementation
- SQL Agent, DB, SP, FTP, HTTP, SMB, API, or production access
- partner-facing publish
- schedule disable/enable
- delivery modernization after DB migration

## Inputs

Phase 5 builds on:

- Phase 2 operations baseline: Spring Batch metadata is execution metadata; `IntegrationManifest` is partner-domain truth.
- Phase 3 validation harness: byte-first comparison, candidate namespace, clean-run recommendation.
- Phase 4 first slice: `kakaoDaumFeedJob` is the first vertical slice after G1 and repo approval.

## External Gates

Executable shadow runs remain blocked until:

- G1 read-only evidence collection is approved and completed.
- The new repo `/Users/jm/Documents/workspace/b2b/partner-integration-batch` is approved.
- JobRepository, manifest store, artifact store, and candidate storage are decided.
- Runtime account, secret source, private network allowlist, and alert route are approved.
- Golden SSIS outputs are secured for the same `businessDate` and contract version.

## Terminology

`Restart` resumes the same Spring Batch `JobInstance` after a failure.

`Manual rebuild` creates a new `runId` and new artifacts by querying source data and generating output again.

`Retransfer` republishes an existing validated artifact without DB/SP/generation.

`Rollback` is a business operation that restores a known-good artifact or schedule state; it is not a Spring Batch restart.
