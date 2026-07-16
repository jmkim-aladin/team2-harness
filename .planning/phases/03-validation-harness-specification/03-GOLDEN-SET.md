---
phase: 3
phase_name: Validation Harness Specification
artifact: golden_set
status: drafted
created: 2026-06-19
requirements:
  - VAL-01
---

# Phase 3 Golden Set Specification

## Purpose

The golden set is the immutable SSIS output baseline used later to prove Spring Batch equivalence. Phase 3 defines the collection contract; actual golden file acquisition is blocked by G1 approval.

## Golden Identity

Each golden artifact is identified by:

```text
integrationId + mode + businessDate + contractVersion + artifact sequence
```

For multi-artifact integrations, compare both individual artifacts and the ordered artifact set.

## Required Metadata

Each golden artifact record must include:

- `goldenSetId`
- `integrationId`
- `mode`
- `businessDate`
- `contractVersion`
- `artifactSequence`
- `artifactKey`
- `fileName`
- `targetAlias`
- `sourceKind`: `ssis-generated`, `published-readback`, or `both`
- `sqlAgentJob`
- `sqlAgentStep`
- `dtsxPackage`
- `dtsxDeploymentRef`
- `ssisRunStartedAt`
- `ssisRunEndedAt`
- `byte count`
- `row count`
- `SHA-256`
- `encoding`
- `newline`
- `delimiter`
- `schemaRef`
- `collectedBy`
- `collectedAt`

## Required Sample Classes

Each integration/mode should eventually include:

- normal full
- today/incremental
- high-volume
- no-data
- low-data
- encoding edge

If a class cannot be captured, the missing class must be recorded with owner, reason, and follow-up.

## Storage Rule

Real SSIS golden files stay outside git. They may contain production-derived partner data and should be stored in approved secure storage only.

Sanitized fixtures may be committed later under the new repo after sensitive data is removed:

```text
src/test/resources/validation-fixtures/{integrationId}/{contractVersion}/{mode}/{businessDate}/
  fixture.yaml
  golden/artifacts/{artifactName}
  candidate/artifacts/{artifactName}
  expected/validation-report.json
```

`fixture.yaml` must describe artifact keys, filenames, format, encoding, newline, delimiter, expected row count, SHA-256, schema ref, sort keys, and allowed tolerances. Default tolerance is zero.

## Golden Collection Gate

Actual collection requires G1 approval for:

- SQL Agent `msdb` enabled job/step/package/schedule
- operational DTSX deployment
- SP definitions and output schema
- existing SSIS output golden files
- publish/readback path access
- runtime account/private network/secret inventory

Row 15 is excluded until G1 confirms active SQL Agent scope and the exact Naver ranking package/job behavior.

## Equivalence Default

The default pass condition is exact raw byte equality between golden and candidate artifacts.

Approved exceptions must be feed-specific and recorded with:

- exception id
- approver
- affected integration/mode/artifact
- allowed difference
- reason
- comparator version
- diff artifact URI
