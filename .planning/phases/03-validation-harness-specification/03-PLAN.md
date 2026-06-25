---
phase: 3
phase_name: Validation Harness Specification
plan: 03
type: execute
wave: 1
depends_on:
  - 01-dtsx-evidence-lock
  - 02-spring-batch-architecture-baseline
files_modified:
  - .planning/phases/03-validation-harness-specification/03-CONTEXT.md
  - .planning/phases/03-validation-harness-specification/03-RESEARCH.md
  - .planning/phases/03-validation-harness-specification/03-PLAN.md
  - .planning/phases/03-validation-harness-specification/03-GOLDEN-SET.md
  - .planning/phases/03-validation-harness-specification/03-VALIDATION-HARNESS.md
  - .planning/phases/03-validation-harness-specification/03-SHADOW-RUN.md
autonomous: true
requirements:
  - VAL-01
  - VAL-02
  - VAL-03
---

# Phase 3 Plan: Validation Harness Specification

<objective>
Define the validation harness that will prove SSIS-to-Spring Batch equivalence later. Produce golden-set, comparator, fixture, shadow-run, threshold, and manifest-recording specifications without accessing DB/prod or collecting real golden files.
</objective>

<must_haves>
- Default equivalence is exact raw byte equality.
- Feed-specific comparator exceptions require explicit approval and manifest recording.
- Real SSIS golden files are external to git and blocked by G1.
- Sanitized fixtures may be committed after repo creation.
- Validation harness is a runtime `IntegrationValidator` design, not only JUnit assertions.
- Shadow output uses `candidate/...` paths only and cannot reach partner-facing targets.
- Row 15 remains excluded until active SQL Agent scope is confirmed.
</must_haves>

<tasks>

<task id="T1" type="execute">
<title>Create golden-set specification</title>
<read_first>
- `.planning/LEDGER.md`
- `.planning/REQUIREMENTS.md`
- `.planning/phases/03-validation-harness-specification/03-CONTEXT.md`
- `.planning/phases/03-validation-harness-specification/03-RESEARCH.md`
</read_first>
<action>
Create `.planning/phases/03-validation-harness-specification/03-GOLDEN-SET.md`. It must define golden identity `integrationId + mode + businessDate + contractVersion + artifact sequence`, required metadata, sample classes, external storage rule for real SSIS golden files, sanitized fixture layout, and row 15 exclusion until G1.
</action>
<acceptance_criteria>
- `03-GOLDEN-SET.md` contains `integrationId + mode + businessDate + contractVersion + artifact sequence`.
- `03-GOLDEN-SET.md` contains `SHA-256`, `byte count`, and `row count`.
- `03-GOLDEN-SET.md` contains `normal full`, `today/incremental`, `high-volume`, `no-data`, and `encoding edge`.
- `03-GOLDEN-SET.md` states real SSIS golden files stay outside git.
- `03-GOLDEN-SET.md` states row 15 is excluded until G1.
</acceptance_criteria>
</task>

<task id="T2" type="execute">
<title>Create validation harness and comparator specification</title>
<read_first>
- `.planning/phases/02-spring-batch-architecture-baseline/02-ARCHITECTURE.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-BATCH-MAPPING.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-OPERATIONS.md`
- `.planning/phases/03-validation-harness-specification/03-RESEARCH.md`
</read_first>
<action>
Create `.planning/phases/03-validation-harness-specification/03-VALIDATION-HARNESS.md`. It must define `IntegrationValidator`, `ValidationHarness`, `ValidationPlanResolver`, `ValidationProfile`, `ArtifactComparator`, `ArtifactComparatorRegistry`, `ByteFingerprint`, `DiffArtifactWriter`, `JsonlComparator`, `TxtComparator`, `TsvComparator`, `XmlComparator`, fixture repositories, and manifest recording fields. It must specify byte-first comparison and streaming semantic diagnostics for JSONL/JSONL.js, TXT, TSV, and XML.
</action>
<acceptance_criteria>
- `03-VALIDATION-HARNESS.md` contains all class/interface names listed in the action.
- `03-VALIDATION-HARNESS.md` contains `exact raw byte equality`.
- `03-VALIDATION-HARNESS.md` contains `JSONL.js`, `TXT`, `TSV`, and `XML`.
- `03-VALIDATION-HARNESS.md` states validation must not hardcode Naver/Google/Kakao rules.
- `03-VALIDATION-HARNESS.md` states large files must be streaming.
- `03-VALIDATION-HARNESS.md` contains `integration_validation_result`.
</acceptance_criteria>
</task>

<task id="T3" type="execute">
<title>Create shadow-run safety and threshold specification</title>
<read_first>
- `.planning/LEDGER.md`
- `.planning/research/PITFALLS.md`
- `.planning/phases/02-spring-batch-architecture-baseline/02-OPERATIONS.md`
- `.planning/phases/03-validation-harness-specification/03-RESEARCH.md`
</read_first>
<action>
Create `.planning/phases/03-validation-harness-specification/03-SHADOW-RUN.md`. It must define `runPurpose=SHADOW`, candidate namespace `candidate/{integrationId}/{mode}/{businessDate}/{contractVersion}/{runId}`, `candidate/work`, `candidate/validated`, `candidate/archive`, partner-facing target blocking, strict failure thresholds, duration warning/failure thresholds, and shadow entry gates.
</action>
<acceptance_criteria>
- `03-SHADOW-RUN.md` contains `runPurpose=SHADOW`.
- `03-SHADOW-RUN.md` contains `candidate/{integrationId}/{mode}/{businessDate}/{contractVersion}/{runId}`.
- `03-SHADOW-RUN.md` contains `candidate/work`, `candidate/validated`, and `candidate/archive`.
- `03-SHADOW-RUN.md` states partner-facing `targetAlias` is blocked.
- `03-SHADOW-RUN.md` contains `>150%`, `>200%`, and `shadow diff count`.
- `03-SHADOW-RUN.md` states row 15 is excluded until G1.
</acceptance_criteria>
</task>

<task id="T4" type="execute">
<title>Update project state and requirement traceability</title>
<read_first>
- `.planning/STATE.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/phases/03-validation-harness-specification/03-GOLDEN-SET.md`
- `.planning/phases/03-validation-harness-specification/03-VALIDATION-HARNESS.md`
- `.planning/phases/03-validation-harness-specification/03-SHADOW-RUN.md`
</read_first>
<action>
Update `.planning/STATE.md` so the current focus is Phase 3 validation harness specification. Update `.planning/REQUIREMENTS.md` traceability for `VAL-01`, `VAL-02`, and `VAL-03` to reflect specified design, with `VAL-01` actual golden file acquisition blocked by G1. Update `.planning/ROADMAP.md` next phase guidance to Phase 4 feed job design after Phase 3 verification.
</action>
<acceptance_criteria>
- `.planning/STATE.md` contains `Phase 3 - Validation Harness Specification`.
- `.planning/REQUIREMENTS.md` contains `VAL-01` with `Blocked by G1` or equivalent wording.
- `.planning/REQUIREMENTS.md` contains `VAL-02` and `VAL-03` with `Specified`.
- `.planning/ROADMAP.md` contains `Phase 4 feed job design`.
</acceptance_criteria>
</task>

</tasks>

<verification>

Run these checks:

```bash
test -f .planning/phases/03-validation-harness-specification/03-GOLDEN-SET.md
test -f .planning/phases/03-validation-harness-specification/03-VALIDATION-HARNESS.md
test -f .planning/phases/03-validation-harness-specification/03-SHADOW-RUN.md
rg -n "exact raw byte equality|SHA-256|row count|byte count|outside git|row 15.*G1" .planning/phases/03-validation-harness-specification/03-GOLDEN-SET.md
rg -n "IntegrationValidator|ArtifactComparator|ByteFingerprint|JsonlComparator|TxtComparator|TsvComparator|XmlComparator|integration_validation_result|streaming" .planning/phases/03-validation-harness-specification/03-VALIDATION-HARNESS.md
rg -n "runPurpose=SHADOW|candidate/\\{integrationId\\}/\\{mode\\}/\\{businessDate\\}/\\{contractVersion\\}/\\{runId\\}|partner-facing|>150%|>200%|shadow diff count" .planning/phases/03-validation-harness-specification/03-SHADOW-RUN.md
rg -n "VAL-01.*G1|VAL-02.*Specified|VAL-03.*Specified" .planning/REQUIREMENTS.md
```

</verification>

<success_criteria>
1. Phase 3 defines golden-set acquisition and comparison rules without pretending real golden files were collected.
2. Phase 3 defines reusable Kotlin validation harness architecture for later implementation.
3. Phase 3 defines strict shadow-run safety rules and failure thresholds.
4. All Phase 3 requirements are traceable.
5. No DB/prod/repo/git/YouTrack/KB side effect occurs.
</success_criteria>
