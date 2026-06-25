# Phase 39 Plan - G1 Read-only Evidence Request Bundle

## Goal

Add a local G1 request bundle generator and command runner so the evidence collection request is explicit, deterministic, and auditable before any G1 read-only collection is approved.

## Tasks

1. Add failing tests for request bundle generation and command runner output.
2. Add `G1EvidenceRequestBundle` model, generator, and command-line runner.
3. Generate a deterministic sample request bundle under `docs/g1-evidence/request-bundle.json`.
4. Update README, G1 import guide, migration ledger, and GSD state.
5. Verify focused tests, actual runner, and full Gradle test suite.
