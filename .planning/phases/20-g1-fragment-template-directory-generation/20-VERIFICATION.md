---
phase_name: G1 Fragment Template Directory Generation
status: passed
updated: 2026-06-19
---

# Phase 20 Verification: G1 Fragment Template Directory Generation

## Commands

```bash
./gradlew test --tests 'kr.co.aladin.partner.integration.batch.g1.*'
```

Result: passed, 13 G1 tests.

```bash
./gradlew bootRun --args='--partner.integration.g1-fragment-template.enabled=true --partner.integration.g1-fragment-template.business-date=2026-06-19 --partner.integration.g1-fragment-template.captured-by=TODO_CAPTURED_BY --partner.integration.g1-fragment-template.evidence-pack-id=g1-fragment-template-20260619 --partner.integration.g1-fragment-template.captured-at=2026-06-19T00:00:00Z --partner.integration.g1-fragment-template.output-root=build/g1-evidence/fragment-template-cli --partner.integration.g1-fragment-template.report=build/g1-evidence/fragment-template-report.json --logging.level.root=WARN'
```

Result: passed as command execution.

```bash
./gradlew bootRun --args='--partner.integration.g1-import.enabled=true --partner.integration.g1-import.source-root=build/g1-evidence/fragment-template-cli --partner.integration.g1-import.output-pack=build/g1-evidence/fragment-template-imported-pack.json --partner.integration.g1-import.validation-report=build/g1-evidence/fragment-template-imported-validation-report.json --partner.integration.g1-import.import-report=build/g1-evidence/fragment-template-import-report.json --logging.level.root=WARN'
```

Result: passed as command execution.

```bash
jq '{evidencePackId, fragmentCount, fragmentNames}' build/g1-evidence/fragment-template-report.json
```

Observed:

```json
{
  "evidencePackId": "g1-fragment-template-20260619",
  "fragmentCount": 7,
  "fragmentNames": [
    "pack-metadata.json",
    "sql-agent-jobs.json",
    "deployed-dtsx-packages.json",
    "stored-procedures.json",
    "golden-outputs.json",
    "publish-targets.json",
    "runtime-evidence.json"
  ]
}
```

```bash
jq '{importConclusion, validationConclusion, fragmentCount, missingFragments}' build/g1-evidence/fragment-template-import-report.json
```

Observed:

```json
{
  "importConclusion": "PACK_WRITTEN_VALIDATION_FAILED",
  "validationConclusion": "FAILED",
  "fragmentCount": 7,
  "missingFragments": []
}
```

```bash
jq '{conclusion, sourceType, requiredTargetCount, passedRuleCount, failedRuleCount, blockedRuleCount}' build/g1-evidence/fragment-template-imported-validation-report.json
```

Observed:

```json
{
  "conclusion": "FAILED",
  "sourceType": "READ_ONLY_EXPORT",
  "requiredTargetCount": 7,
  "passedRuleCount": 1,
  "failedRuleCount": 36,
  "blockedRuleCount": 0
}
```

```bash
./gradlew test --rerun-tasks
```

Result: passed, 45 tests.

```bash
rg -n --hidden -S "(?i)(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|BEGIN RSA|BEGIN OPENSSH|jdbc:sqlserver|ftp://|sftp://|https?://[^ )']+)" README.md docs src/main src/test .gitignore build.gradle.kts gradle.properties settings.gradle.kts || true
```

Result: expected placeholders, masked test strings, public XML feature URLs, and code identifiers only; no real credential or endpoint material found.

## Requirement Check

| Requirement | Status | Evidence |
|---|---|---|
| INV-04 | Prepared, blocked on approval | Fragment template includes SQL Agent fragment shape but real export still needs approval |
| VAL-01 | Prepared, blocked on evidence | Golden-output fragment template is generated from expected contracts |
| VAL-02 | Prepared, blocked on evidence | Generated fragments round-trip through import+validation path |
| OPS-04 | Prepared, blocked on approval | Runtime evidence fragment template is generated |

## Residual Risk

- Generated template fragments are not operational proof.
- SQL Agent active package, deployed DTSX drift, SP definitions, real golden outputs, publish target readback, and runtime/private-network proof remain unverified until G1 approval.
