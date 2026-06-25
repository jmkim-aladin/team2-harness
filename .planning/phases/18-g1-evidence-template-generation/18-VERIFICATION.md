---
phase_name: G1 Evidence Template Generation
status: passed
updated: 2026-06-19
---

# Phase 18 Verification: G1 Evidence Template Generation

## Commands

```bash
./gradlew test --rerun-tasks
```

Result: passed, 39 tests.

```bash
./gradlew bootRun --args='--partner.integration.g1-template.enabled=true --partner.integration.g1-template.business-date=2026-06-19 --partner.integration.g1-template.captured-by=TODO_CAPTURED_BY --partner.integration.g1-template.evidence-pack-id=g1-template-20260619 --partner.integration.g1-template.captured-at=2026-06-19T00:00:00Z --partner.integration.g1-template.output=docs/g1-evidence/template-pack.json --logging.level.root=WARN'
```

Result: passed; `docs/g1-evidence/template-pack.json` generated.

```bash
./gradlew bootRun --args='--partner.integration.g1-evidence.enabled=true --partner.integration.g1-evidence.pack=docs/g1-evidence/template-pack.json --partner.integration.g1-evidence.output=build/g1-evidence/template-validation-report.json --logging.level.root=WARN'
```

Result: passed as command execution; validation conclusion intentionally failed.

```bash
jq '{conclusion,sourceType,requiredTargetCount,passedRuleCount,failedRuleCount,blockedRuleCount}' build/g1-evidence/template-validation-report.json
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
rg -n "Password=[^<]|Pwd=[^<]|Secret|Token|AKIA|BEGIN PRIVATE KEY" docs/g1-evidence/template-pack.json build/g1-evidence/template-validation-report.json || true
```

Result: no matches.

## Requirement Check

| Requirement | Status | Evidence |
|---|---|---|
| INV-04 | Prepared, blocked on approval | Required target template exists; actual SQL Agent export still needs approval |
| VAL-01 | Prepared, blocked on evidence | Golden output placeholder files are generated from contract names |
| VAL-02 | Prepared, blocked on evidence | Template contains byte/SHA fields; real shadow comparison still needs G1 |
| OPS-04 | Prepared, blocked on approval | Runtime/private-network evidence placeholder exists |

## Residual Risk

- Template placeholders are not operational proof.
- SQL Agent active package, deployed DTSX drift, SP definitions, real golden outputs, publish target readback, and runtime/private-network proof remain unverified until G1 approval.
