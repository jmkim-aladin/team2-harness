---
phase: 3
phase_name: Validation Harness Specification
status: research_complete
created: 2026-06-19
source: multi_agent_v1 explorers
---

# Phase 3 Research: Validation Harness Specification

## RESEARCH COMPLETE

## Golden Output

Collect immutable SSIS outputs per:

```text
integrationId + mode + businessDate + contractVersion + artifact sequence
```

Each golden must record:

- SQL Agent job/step/package evidence
- DTSX deployment source
- run timestamp
- business date
- file name/path or endpoint alias
- target alias
- byte count
- row count
- SHA-256
- encoding/newline/delimiter notes

Required sample classes:

- normal full
- today/incremental
- high-volume
- no-data or low-data
- encoding edge date

Row 15/Naver ranking cannot enter the golden set until active scope is confirmed by G1.

## Comparator Strategy

Default pass condition is exact raw byte equality. Do not normalize line endings, trim whitespace, reserialize JSON/XML, reorder rows, or canonicalize unless an approved feed-specific exception exists.

Every comparison should run in two stages:

1. byte fingerprint: byte count, SHA-256, encoding, newline, row/record count
2. streaming semantic comparator: diagnostics only unless the contract explicitly allows non-byte-equivalent output

Format diagnostics:

- JSONL/JSONL.js: stream line by line; unwrap `.js` envelope only for diagnostics; preserve line order
- TXT: line-based byte/sequence comparison; validate delimiter/fixed-width/null token/trailing delimiter
- TSV: validate tab delimiters, header policy, column count, split file naming/order, per-file and aggregate row counts
- XML: byte check first, then StAX/XML diagnostics; Kakao/Daum six-output group is a named artifact set

Large files must be streaming. Do not load full feeds into memory.

## Harness Architecture

Recommended validation package shape:

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

`feed.*` owns `ContractOutputSpec`; validation consumes specs and must not hardcode Naver/Google/Kakao logic.

## Shadow Safety

- No shadow runs before Phase 3 comparison rules are approved.
- Use `runPurpose=SHADOW`.
- Block partner-facing `targetAlias`.
- Candidate namespace:

```text
candidate/{integrationId}/{mode}/{businessDate}/{contractVersion}/{runId}
```

- Candidate lifecycle: `candidate/work`, `candidate/validated`, `candidate/archive`.
- Retention/cleanup must only touch candidate paths during shadow validation.

## Failure Thresholds

Default strict failures:

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

Duration is not correctness, but once SSIS baseline exists:

- warn at `>150%`
- fail at `>200%` or scheduled-window breach

Cutover remains blocked if shadow diff count is greater than zero.

## Blocked By G1

- active SQL Agent job/step/package/schedule
- operational DTSX deployment readback
- SP definitions and output schema
- existing SSIS golden output collection
- publish/readback path access
- runtime account, private network allowlist, secret source
