---
phase: 5
phase_name: Shadow Run And Operational Hardening
artifact: research
status: drafted
created: 2026-06-19
requirements:
  - VAL-04
  - OPS-03
---

# Phase 5 Research: Shadow Run And Operational Hardening

## Research Sources

This phase used existing planning artifacts plus three parallel read-only agent passes:

- shadow lifecycle and clean-run gate
- restart/rebuild/retransfer/rollback runbook
- manifest fields, events, metrics, alerts, and validation report shape

No files were changed by agents. No external system was accessed.

## Findings

### Shadow Is Not Cutover

Phase 5 must not touch partner-facing final paths. It should generate candidate artifacts, compare them against approved SSIS golden outputs, record manifest evidence, and promote only passing artifacts within candidate storage.

The lifecycle stays:

```text
candidate/work -> candidate/validated -> candidate/archive
```

The namespace remains:

```text
candidate/{integrationId}/{mode}/{businessDate}/{contractVersion}/{runId}
```

### Clean Run Criteria

Before cutover eligibility, each integration/mode needs:

- three consecutive clean daily/today runs
- one clean full-feed run where full mode exists
- zero validation diff
- matching row count, byte count, checksum, schema, encoding, newline, delimiter, escaping, null handling, sort order, reject count, and aggregate totals
- manifest evidence for run, artifact, validation, publish/readback, and audit events

Duration is operational fitness:

- warn at more than 150% of SSIS baseline
- fail at more than 200% of SSIS baseline or scheduled-window breach

### Manifest Is The Operational Truth

Spring Batch metadata answers whether a Job/Step ran. It does not prove partner artifact correctness. Phase 5 should harden the Phase 2 manifest model instead of adding another operations store.

Minimum hardening:

- run trigger, reason, requested-by, lock, candidate namespace, golden set, baseline run, clean-run sequence
- artifact group, contract output key, zone, partner visibility, expected/detected encoding and newline
- publish attempt temp/final destination masking, readback probe type, retryability, failure class
- validation baseline/candidate checksum, comparator version, exception approval reference
- append-only events with correlation, actor type, reason code, previous status, next status, masked details

### Restart, Rebuild, Retransfer, Rollback Are Different Actions

Phase 5 must keep four operator actions separate:

- `Restart`: same `JobInstance`, same identifying parameters, continue from recoverable failure point.
- `Manual rebuild`: new `runId` and new artifact identity; source query/generation/validation can run again.
- `Retransfer`: existing validated artifact only; no DB/SP/generation.
- `Rollback`: restore a known-good artifact or legacy schedule state with explicit approval.

The current `forceRebuild` idea is not enough by itself because a rebuild requires new artifact identity. Implementation should add identifying `rerunKey` or include attempt identity in `runPurpose`.

### Kakao/Daum Specific Rule

`kakaoDaumFeedJob` has six XML outputs and must be validated as one artifact group:

- `selling.xml`
- `ebook_selling.xml`
- `event.xml`
- `ebook_event.xml`
- `eventbook.xml`
- `ebook_eventbook.xml`

One missing, malformed, encoding-mismatched, or order-mismatched file blocks group completion.
