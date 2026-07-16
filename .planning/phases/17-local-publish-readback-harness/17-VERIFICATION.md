---
phase_name: Local Publish Readback Harness
status: passed
updated: 2026-06-19
---

# Phase 17 Verification: Local Publish Readback Harness

## Commands

```bash
./gradlew test --rerun-tasks
```

Result: passed, 36 tests.

```bash
./gradlew bootRun --args='--partner.integration.local-publish-readback.enabled=true --partner.integration.local-publish-readback.source-root=docs/publish-readback/sample-source --partner.integration.local-publish-readback.target-root=build/local-publish-readback-sample/target --partner.integration.local-publish-readback.target-alias=local.sample --partner.integration.local-publish-readback.allow-overwrite=true --partner.integration.local-publish-readback.output=build/local-publish-readback/report.json --logging.level.root=WARN'
```

Result: passed; `build/local-publish-readback/report.json` generated.

```bash
jq '{conclusion,totalFiles,publishedFiles,failedFiles,targetAlias,results:(.results|map({relativePath,status,source,target,messages}))}' build/local-publish-readback/report.json
```

Observed:

```json
{
  "conclusion": "PASSED",
  "totalFiles": 1,
  "publishedFiles": 1,
  "failedFiles": 0,
  "targetAlias": "local.sample",
  "overwriteExisting": true
}
```

```bash
rg -n "Password=[^<]|Pwd=[^<]|Secret|Token|AKIA|BEGIN PRIVATE KEY" build/local-publish-readback/report.json docs/publish-readback/sample-report.json docs/publish-readback/sample-source || true
```

Result: no matches.

## Requirement Check

| Requirement | Status | Evidence |
|---|---|---|
| ARCH-04 | Partial | Local compatibility-bridge harness exists; real endpoint bridge still requires G1/runtime approval |
| VAL-04 | Passed locally | Sample report records publish/readback byte/SHA match |
| OPS-01 | Partial | JSON evidence report added; production manifest persistence still requires target storage decision |

## Residual Risk

- Local filesystem readback is not proof of FTP/SMB/HTTP/API behavior.
- Sample source is synthetic and cannot prove SSIS equivalence.
- Real partner-visible readback remains blocked until G1 evidence and runtime/private network approval.
