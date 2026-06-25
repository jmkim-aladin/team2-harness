---
phase: 5
phase_name: Shadow Run And Operational Hardening
artifact: shadow_lifecycle
status: drafted
created: 2026-06-19
requirements:
  - VAL-04
---

# Phase 5 Shadow Lifecycle

## Principle

Shadow run proves candidate artifact equivalence without partner exposure. It may read approved source/golden evidence after G1, but it must not publish to final FTP, HTTP, SMB, API, or partner-visible aliases.

## Namespace

Every shadow run writes under:

```text
candidate/{integrationId}/{mode}/{businessDate}/{contractVersion}/{runId}
```

Required zones:

```text
candidate/work
candidate/validated
candidate/archive
```

Retention and cleanup jobs must be unable to touch non-candidate paths while `runPurpose=SHADOW`.

## Lifecycle

1. Acquire domain lock for `integrationId + mode + businessDate + contractVersion + targetAlias`.
2. Create `integration_run` with `runPurpose=SHADOW`, `candidateNamespace`, `goldenSetId`, and `baselineRunId`.
3. Generate candidate artifacts into `candidate/work`.
4. Record checksum, byte count, row or node count, encoding, newline, delimiter, schema reference, and artifact storage URI.
5. Compare candidate artifacts against approved SSIS golden artifacts.
6. Write diff artifacts and validation results for any mismatch.
7. Promote only passing artifacts to `candidate/validated`.
8. Optionally perform readback smoke against non-partner-facing candidate storage.
9. Archive completed run evidence under `candidate/archive`.
10. Append final manifest event and release lock.

## Hard Blocks

Shadow mode blocks:

- partner-facing final paths
- `ftp.aladin.co.kr` final delivery
- `www2.aladin.co.kr` final static delivery
- SMB/UNC final delivery
- partner API publish
- schedule disable/enable
- legacy SSIS schedule changes

## Clean Run Criteria

Before Phase 6 cutover eligibility, require:

- three consecutive clean daily/today runs per `integrationId + mode`
- one clean full-feed run where full mode exists
- zero validation diff count
- exact match for row count, byte count, checksum, schema, encoding, newline, delimiter, escaping, null handling, sort order, reject count, and aggregate totals
- publish status not partner-visible during shadow
- readback status recorded as `SKIPPED_SHADOW` or passed candidate readback smoke

Duration is fitness, not correctness:

- warn over 150% of SSIS baseline
- fail over 200% of SSIS baseline or scheduled-window breach

## Kakao/Daum First Slice

`kakaoDaumFeedJob` shadow validation treats these six XML files as one artifact group:

- `selling.xml`
- `ebook_selling.xml`
- `event.xml`
- `ebook_event.xml`
- `eventbook.xml`
- `ebook_eventbook.xml`

Group completion requires:

- exactly six files
- same `businessDate`
- expected order
- expected encoding per file
- well-formed XML
- same checksum or approved comparator result against golden output
- no partner-facing publish during shadow

One missing, malformed, encoding-mismatched, or order-mismatched file fails the whole group.

## Cutover Eligibility Output

Shadow run produces a validation report, but does not approve cutover by itself. Phase 6 requires human approval, rollback rehearsal evidence, and explicit feed-by-feed cutover gate.
