---
phase_name: G1 Evidence Directory Import
status: passed
updated: 2026-06-19
---

# Phase 19 Verification: G1 Evidence Directory Import

## Commands

```bash
./gradlew test --tests 'kr.co.aladin.partner.integration.batch.g1.*'
```

Result: passed, 10 G1 tests.

```bash
./gradlew bootRun --args='--partner.integration.g1-import.enabled=true --partner.integration.g1-import.source-root=build/g1-evidence/template-import-fragments --partner.integration.g1-import.output-pack=build/g1-evidence/imported-template-pack.json --partner.integration.g1-import.validation-report=build/g1-evidence/imported-template-validation-report.json --partner.integration.g1-import.import-report=build/g1-evidence/import-report.json --logging.level.root=WARN'
```

Result: passed as command execution.

```bash
jq '{importConclusion, validationConclusion, fragmentCount, missingFragments, messages}' build/g1-evidence/import-report.json
```

Observed:

```json
{
  "importConclusion": "PACK_WRITTEN_VALIDATION_FAILED",
  "validationConclusion": "FAILED",
  "fragmentCount": 7,
  "missingFragments": [],
  "messages": [
    "Imported 7 G1 evidence fragments"
  ]
}
```

```bash
jq '{conclusion, sourceType, requiredTargetCount, passedRuleCount, failedRuleCount, blockedRuleCount}' build/g1-evidence/imported-template-validation-report.json
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

Result: passed, 43 tests.

```bash
rg -n --hidden -S "(?i)(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|BEGIN RSA|BEGIN OPENSSH|jdbc:sqlserver|ftp://|sftp://|https?://[^ )']+)" README.md docs src/main src/test .gitignore build.gradle.kts gradle.properties settings.gradle.kts || true
```

Result: expected placeholders, masked test strings, public XML feature URLs, and code identifiers only; no real credential or endpoint material found.

## Requirement Check

| Requirement | Status | Evidence |
|---|---|---|
| INV-04 | Prepared, blocked on approval | Importer accepts SQL Agent fragment but real export still needs approval |
| VAL-01 | Prepared, blocked on evidence | Golden-output fragment is accepted and validated by existing rules |
| VAL-02 | Prepared, blocked on evidence | Import+validation report path exists; real shadow comparison still needs G1 |
| OPS-04 | Prepared, blocked on approval | Runtime evidence fragment is accepted and validated by existing rules |

## Residual Risk

- Imported template fragments are not operational proof.
- SQL Agent active package, deployed DTSX drift, SP definitions, real golden outputs, publish target readback, and runtime/private-network proof remain unverified until G1 approval.
