---
phase: 3
phase_name: Validation Harness Specification
artifact: validation_harness
status: drafted
created: 2026-06-19
requirements:
  - VAL-01
  - VAL-02
  - VAL-03
---

# Phase 3 Validation Harness Specification

## Purpose

Validation is a reusable runtime harness behind `IntegrationValidator`, not only a set of JUnit assertions. The same contract should support local fixtures, shadow runs, and later cutover evidence.

## Package Shape

Root package: `kr.co.aladin.partner.integration.batch`

```text
validation
  IntegrationValidator
  ValidationHarness
  ValidationPlanResolver
  ValidationProfile
  ValidationReportAssembler

validation.compare
  ArtifactComparator
  ArtifactComparatorRegistry
  ArtifactProbe
  ByteFingerprint
  StreamingRecordCursor
  RecordHasher
  ComparisonResult
  DiffSummary
  DiffArtifactWriter

validation.compare.jsonl
  JsonlComparator
  JsonlJsEnvelopeHandler

validation.compare.txt
  TxtComparator

validation.compare.tsv
  TsvComparator
  MultiResourceTsvComparator

validation.compare.xml
  XmlComparator

validation.fixture
  FixtureManifest
  FixtureLoader
  GoldenArtifactRepository
  CandidateArtifactRepository

validation.runtime
  ManifestBackedGoldenArtifactRepository
  ArtifactStoreCandidateResolver
  ManifestValidationRecorder
```

`feed.*` packages own `ContractOutputSpec`: format, encoding, newline, delimiter, schema ref, sort keys, artifact keys, target aliases, and byte-equality policy. Validation consumes these specs and must not hardcode Naver/Google/Kakao rules.

## Comparison Strategy

Every comparator runs byte-first:

1. compute `ByteFingerprint`
2. compare byte count
3. compare SHA-256
4. detect encoding/newline/record count
5. run streaming semantic diagnostics only when byte equality fails or when a rule asks for details

Default pass condition is exact raw byte equality. Semantic comparison is diagnostic unless a feed-specific approved exception allows non-byte-equivalent output.

Large files must be streaming. Do not load full feeds into memory.

## Format Rules

| Format | Comparator | Required diagnostics |
|---|---|---|
| JSONL | `JsonlComparator` | line count, malformed line, key-level hash, order mismatch |
| JSONL.js | `JsonlComparator` + `JsonlJsEnvelopeHandler` | wrapper bytes, line payload diagnostics |
| TXT | `TxtComparator` | line sequence, delimiter or fixed-width shape, null token, trailing delimiter, newline |
| TSV | `TsvComparator` | tab delimiter, header policy, column count, per-file totals |
| split TSV | `MultiResourceTsvComparator` | split file naming/order, per-file and aggregate row counts |
| XML | `XmlComparator` | byte diff first, schema/XPath diagnostics, named artifact group checks |

## Aggregate Checks

When the contract exposes fields, record aggregate diagnostics:

- product count
- sale/list price sums
- availability/status/category distributions
- min/max/null counts
- reject count
- per-partition totals

Aggregate checks are exact by default. Tolerance requires a feed-specific approved exception.

## Manifest Recording

`validateArtifacts` records:

- `integration_validation_result` row per rule
- `integration_artifact.validationStatus`
- `integration_manifest_event` for validation start, pass, and fail
- `validationProfileId`
- `baselineArtifactId`
- `baselineSha256`
- `candidateSha256`
- `comparatorVersion`
- `diffArtifactUri`

Diff artifacts are written under:

```text
work/{integrationId}/{businessDate}/{runId}/validation-diff/
```

## Later Commands

After the new repo exists, expected command families:

```bash
./gradlew test --tests '*ComparatorTest'
./gradlew test --tests '*ValidationFixtureTest'
VALIDATION_FIXTURE_ROOT=/secure/ssis-golden ./gradlew integrationTest --tests '*ValidationHarnessIT'
```

Runtime shadow validation shape:

```bash
java -jar build/libs/partner-integration-batch.jar \
  --spring.batch.job.name=validationHarnessJob \
  integrationId=NAVER_BOOK mode=FULL businessDate=2026-06-18 \
  contractVersion=v1 runPurpose=SHADOW \
  goldenSetId=ssis-20260618 candidateRunId=<runId>
```
