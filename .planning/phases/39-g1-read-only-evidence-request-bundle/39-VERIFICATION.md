# Phase 39 Verification - G1 Read-only Evidence Request Bundle

## Verification Commands

```bash
./gradlew test --tests 'kr.co.aladin.partner.integration.batch.g1.G1EvidenceRequest*'
```

Status: PASSED

```bash
./gradlew bootRun --args='--partner.integration.g1-request.enabled=true --partner.integration.g1-request.business-date=2026-06-19 --partner.integration.g1-request.requested-by=migration-lead --partner.integration.g1-request.request-id=g1-request-sample --partner.integration.g1-request.generated-at=2026-06-19T00:00:00Z --partner.integration.g1-request.output=docs/g1-evidence/request-bundle.json'
```

Status: PASSED

Observed bundle:

```text
approvalRequired=true
collectionMode=READ_ONLY_OPERATOR_EXPORT
requiredFragments=7
targetRequests=7
readOnlyEvidenceQueries=4
forbiddenActions=6
```

```bash
./gradlew test --tests 'kr.co.aladin.partner.integration.batch.g1.*'
```

Status: PASSED

```bash
./gradlew test --rerun-tasks
```

Status: PASSED

```text
tests=116 failures=0 errors=0 skipped=0
```

## Safety Check

The generated request bundle contains placeholders, masked-path requirements, and read-only query templates only. It does not contain DB credentials, tokens, passwords, production endpoints, or executable DB mutation commands.

## Commit

```text
417f542 [ssis-kotlin-batch-migration] Add G1 evidence request bundle
```
