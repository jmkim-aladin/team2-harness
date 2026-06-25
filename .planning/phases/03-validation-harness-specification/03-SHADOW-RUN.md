---
phase: 3
phase_name: Validation Harness Specification
artifact: shadow_run
status: drafted
created: 2026-06-19
requirements:
  - VAL-02
  - VAL-03
---

# Phase 3 Shadow Run Specification

## Purpose

Shadow runs compare new Spring Batch candidate artifacts against SSIS golden artifacts without touching partner-facing FTP/WWW/final paths.

## Entry Gates

Shadow execution is not allowed until:

- Phase 3 comparison rules are approved
- G1 evidence is locked
- candidate target is configured
- manifest storage is decided
- lock behavior is verified
- no partner-facing destination is reachable from the shadow target

Row 15 is excluded until G1 confirms active SQL Agent scope.

## Required Parameters

Shadow jobs use:

```text
runPurpose=SHADOW
```

`shadowRun` may exist as a convenience flag, but it must not be the only semantic differentiator if it affects Spring Batch JobInstance identity.

## Candidate Namespace

Candidate artifacts must use:

```text
candidate/{integrationId}/{mode}/{businessDate}/{contractVersion}/{runId}
```

Candidate lifecycle:

- `candidate/work`
- `candidate/validated`
- `candidate/archive`

Retention and cleanup during shadow validation must only touch candidate paths.

Partner-facing `targetAlias` is blocked for shadow runs.

## Shadow Validation Steps

1. generate candidate artifact under `candidate/work`
2. compare candidate with approved golden set
3. write diff artifacts if any rule fails
4. promote to `candidate/validated` only when validation passes
5. record validation results in manifest
6. optionally run candidate readback smoke against non-partner-facing target

Final partner publish is not part of Phase 3.

## Strict Failure Thresholds

Any of these fails correctness:

- row count mismatch
- byte count mismatch
- checksum mismatch
- schema mismatch
- encoding mismatch
- newline mismatch
- delimiter mismatch
- escaping mismatch
- null-handling mismatch
- sort-order mismatch
- unexpected reject count
- aggregate total mismatch without approved tolerance

Shadow diff count greater than zero blocks cutover.

## Duration Thresholds

Duration is operational fitness, not correctness. Once SSIS baseline duration exists:

- warn at `>150%` of SSIS baseline
- fail at `>200%` of SSIS baseline or scheduled-window breach

## Clean Run Recommendation

Before cutover, require at least:

- three consecutive clean daily/today runs per integration/mode
- one clean full-feed run where full mode exists

This is a later cutover gate, not a Phase 3 completion claim.
