---
phase_name: Domain Run Lock
status: passed
updated: 2026-06-19
---

# Phase 21 Verification: Domain Run Lock

## Commands

```bash
./gradlew test --tests 'kr.co.aladin.partner.integration.batch.lock.*' --tests 'kr.co.aladin.partner.integration.batch.batch.IntegrationRunLockJobExecutionListenerTest'
```

Result: passed, 5 targeted lock tests.

```bash
./gradlew bootRun --args='--partner.integration.launch-job=kakaoDaumFeedJob --integrationId=KAKAO_DAUM --mode=FULL --businessDate=2026-06-19 --contractVersion=v1 --runPurpose=SHADOW --targetAlias=local.candidate --partner.integration.golden-comparison-required=false --partner.integration.manifest-root=build/partner-integration/lock-smoke/manifest --partner.integration.artifact-root=build/partner-integration/lock-smoke/artifacts --logging.level.root=WARN'
```

Result: passed as local skeleton smoke.

```bash
find build/partner-integration/lock-smoke/manifest/locks -type f -maxdepth 1 2>/dev/null | wc -l | tr -d ' '
```

Observed: `0`.

```bash
find build/partner-integration/lock-smoke/manifest/events -type f -maxdepth 1 -print -exec sh -c 'tail -n +1 "$1" | rg "LOCK_ACQUIRED|RUN_COMPLETED|RUN_PLANNED"' sh {} \;
```

Observed: manifest event stream contains `RUN_PLANNED`, `LOCK_ACQUIRED`, and `RUN_COMPLETED`.

```bash
./gradlew test --rerun-tasks
```

Result: passed, 50 tests.

```bash
rg -n --hidden -S "(?i)(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|BEGIN RSA|BEGIN OPENSSH|jdbc:sqlserver|ftp://|sftp://|https?://[^ )']+)" README.md docs src/main src/test .gitignore build.gradle.kts gradle.properties settings.gradle.kts || true
```

Result: expected placeholders, masked test strings, public XML feature URLs, and code identifiers only; no real credential or endpoint material found.

## Requirement Check

| Requirement | Status | Evidence |
|---|---|---|
| OPS-01 | Partial local implementation | Manifest event records `LOCK_ACQUIRED` and run completes with no leftover lock |
| OPS-02 | Local implementation complete | Same `integrationId + businessDate` lock is enforced by tests and file-backed atomic create |

## Residual Risk

- File-backed lock is local compatibility baseline only.
- Production lock store, stale-lock takeover, and operator unlock procedure must be finalized with the G2 storage decision.
