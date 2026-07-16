# Phase 26 Context: Migration Readiness Bundle

## Problem

Phase 25 proves local skeleton execution and contract-format validation for the runnable 13, 14, 16, and 17 targets. It does not show the whole SSIS migration gate state in one operator-facing report.

The next useful local step is to bundle the existing evidence reports:

- local smoke matrix
- G1 read-only evidence validation
- equivalence gate
- local publish/readback smoke

## Constraints

- No DB, SQL Agent, FTP, SMB, HTTP, API, production, YouTrack, KB, push, or PR changes.
- Missing or synthetic evidence must not be treated as equivalent.
- The report must remain offline and deterministic enough for CI/local review.

## Target

Add a Kotlin/Spring Boot command-line runner that reads existing JSON reports and writes a single readiness report with `READY_FOR_SHADOW_RUN`, `BLOCKED`, or `NOT_EQUIVALENT`.
