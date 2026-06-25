---
phase: 16
phase_name: G1 Evidence Pack Validation
status: passed_local_verification
verified: 2026-06-19
requirements:
  - INV-04
  - VAL-01
  - VAL-02
  - OPS-04
---

# Phase 16 Verification

## Commands Run

```bash
./gradlew test --rerun-tasks

./gradlew bootRun --args='--partner.integration.g1-evidence.enabled=true --partner.integration.g1-evidence.pack=docs/g1-evidence/sample-pack.json --partner.integration.g1-evidence.output=docs/g1-evidence/sample-report.json --logging.level.root=WARN'

jq '{conclusion,sourceType,requiredTargetCount,passedRuleCount,failedRuleCount,blockedRuleCount, blocked:(.rules|map(select(.status=="BLOCKED")|{ruleName,status,messages})[0:5])}' docs/g1-evidence/sample-report.json

rg -n "Password=[^<]|Pwd=[^<]" docs/g1-evidence/sample-pack.json docs/g1-evidence/sample-report.json
```

## Result

- Tests passed: 27 test methods.
- Sample report generation succeeded.
- Sample report conclusion: `BLOCKED_SAMPLE_ONLY`.
- Raw password grep returned no matches.

## Residual Risk

- The validator is an acceptance gate for evidence shape, not the evidence itself.
- Real G1 read-only export still needs user approval.
