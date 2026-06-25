# Phase 44 Context - Legacy SQL Adapter Plan Readiness Gate

## Why

Phase 43 produced a local `LegacySqlCallPlanReport`, but migration readiness did not require it. That left a gap: unresolved direct SQL candidates could exist outside `LegacyDbAdapter` planning while the readiness bundle only checked DTSX spec coverage, manual work, G1, equivalence, and publish/readback evidence.

## Current Inputs

- b2b repo: `/Users/jm/Documents/workspace/b2b/partner-integration-batch`
- DTSX migration spec: `docs/dtsx-spec/priority-13-17-migration-spec.json`
- legacy SQL plan sample: `docs/legacy-sql/sample-report.json`
- readiness sample: `docs/readiness/sample-report.json`

## Constraint

No DB, SQL Agent, DTSX execution, FTP, SMB, HTTP, API, production endpoint, YouTrack, KB, push, or PR action is allowed for this phase.
