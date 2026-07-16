---
phase: 13
phase_name: Golden Comparison Harness
status: passed_local_verification
verified: 2026-06-19
requirements:
  - VAL-01
  - VAL-02
  - VAL-03
---

# Phase 13 Verification

## Commands Run

```bash
./gradlew test --rerun-tasks

./gradlew bootRun --args='--partner.integration.golden-compare.enabled=true --partner.integration.golden-compare.candidate-root=build/golden-comparison-sample/candidate --partner.integration.golden-compare.golden-root=build/golden-comparison-sample/golden --partner.integration.golden-compare.output=docs/golden-comparison/sample-report.json --logging.level.root=WARN'

jq '{conclusion,totalFiles,matchedFiles,failedFiles, statuses:(.comparisons|map({relativePath,status}))}' docs/golden-comparison/sample-report.json

rg -n "secret|Password=[^<]|Pwd=[^<]" docs/golden-comparison/sample-report.json
```

## Result

- Tests passed: 14 test methods.
- Sample report generation succeeded.
- Sample report conclusion: `BLOCKED_MISSING_FILES`.
- Secret/password grep returned no matches.

## Residual Risk

- Real golden output still needs G1 evidence collection.
- A passing comparator report is only meaningful when candidate and golden files are produced from the same `businessDate` and contract version.
