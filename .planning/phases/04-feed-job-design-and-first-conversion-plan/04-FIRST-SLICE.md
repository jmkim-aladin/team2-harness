---
phase: 4
phase_name: Feed Job Design And First Conversion Plan
artifact: first_slice
status: drafted
created: 2026-06-19
requirements:
  - FEED-01
  - FEED-02
  - FEED-03
  - FEED-04
  - FEED-05
---

# Phase 4 First Vertical Slice Decision

## Decision

Select `kakaoDaumFeedJob` as the first vertical slice after G1 evidence and repo creation approval.

## Rationale

`kakaoDaumFeedJob` has the clearest local mapping:

- one primary DTSX generator: `KakaoDaum.dtsx`
- one separate retention DTSX: `DTS_DaumDBFile_OldDataDelete.dtsx`
- six explicit XML outputs
- known SP families: `KakaoDaum_Book_Selling`, `KakaoDaum_Book_Event`, `KakaoDaum_Book_EventBook`
- less ambiguity than row 15/Naver ranking
- strong fit for Phase 3 named artifact group validation

## Scope Of First Slice

The first implementation slice should include:

- repo scaffold for Kotlin + Spring Boot 4.1.x + Spring Batch 6.0.x
- package boundaries from Phase 2
- `kakaoDaumFeedJob`
- `feedRetentionJob` dry-run path only
- manifest writes
- artifact store work/validated/archive lifecycle
- `XmlComparator` validation for six outputs
- candidate/shadow output only before cutover

## Not In First Slice

- Naver ranking / row 15
- production publish
- delivery modernization
- Google partition tuning
- full Naver book/shopping implementation
- real equivalence claim without golden files

## Required Before Implementation

Implementation waits for:

- G1 read-only evidence approval
- repo creation approval for `/Users/jm/Documents/workspace/b2b/partner-integration-batch`
- JobRepository/manifest/artifact storage decision
- runtime account/private network/secret source decision

No production equivalence claim is allowed until SSIS golden outputs and shadow comparison pass.
