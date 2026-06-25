---
phase: 6
phase_name: Incremental Cutover Plan
artifact: context
status: drafted
created: 2026-06-19
requirements:
  - OPS-03
  - OPS-04
---

# Phase 6 Context: Incremental Cutover Plan

## Purpose

Phase 6 defines how each SSIS-backed partner integration moves to the Kotlin Spring Batch replacement only after evidence and human approval are in place.

This is still a planning phase. It does not disable SQL Agent schedules, enable Spring Batch production schedules, publish partner-facing artifacts, update YouTrack, or touch DB/prod.

## Cutover Unit

Default cutover unit:

```text
integrationId + mode + contractVersion + targetAlias
```

Feed groups such as `kakaoDaumFeedJob` may cut over as one artifact group when outputs are contractually coupled.

## Inputs Required From Earlier Phases

- G1 evidence: SQL Agent active jobs, deployed DTSX, SP definitions, golden SSIS outputs
- G2 evidence: repo, JobRepository, manifest store, artifact store, candidate storage
- Phase 3 validation rules
- Phase 4 feed-level job contracts
- Phase 5 clean-run evidence and rollback/retransfer runbook

## Hard Rules

- No feed cutover without validation report.
- No feed cutover without rollback rehearsal.
- No feed cutover without owner, backup owner, and rollback owner.
- No partner-visible contract change in v1.
- No delivery modernization in v1.
- No production action without explicit human approval.
