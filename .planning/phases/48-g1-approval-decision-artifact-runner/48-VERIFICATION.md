# Phase 48 검증: G1 approval decision artifact runner

## 검증 명령

```bash
./gradlew test --tests 'kr.co.aladin.partner.integration.batch.g1.*'
```

결과: 통과

```bash
./gradlew bootRun --args='--partner.integration.g1-approval-decision.enabled=true --partner.integration.g1-approval-decision.packet=docs/g1-evidence/approval-packet.json --partner.integration.g1-approval-decision.output=build/g1-evidence/approval-decision-approved.json --partner.integration.g1-approval-decision.decision-status=APPROVED_READ_ONLY_EXPORT --partner.integration.g1-approval-decision.approved-by=jm --partner.integration.g1-approval-decision.approved-at=2026-06-20T00:00:00Z --partner.integration.g1-approval-decision.notes=사용자 승인에 따라 G1 read-only evidence export를 허용한다.'
```

결과: `build/g1-evidence/approval-decision-approved.json` 생성 확인

```bash
./gradlew bootRun --args='--partner.integration.g1-import.enabled=true --partner.integration.g1-import.require-approval=true --partner.integration.g1-import.approval-packet=docs/g1-evidence/approval-packet.json --partner.integration.g1-import.approval-decision=build/g1-evidence/approval-decision-approved.json --partner.integration.g1-import.source-root=build/g1-evidence/local-dtsx-candidates --partner.integration.g1-import.output-pack=build/g1-evidence/local-dtsx-candidates-approved-pack.json --partner.integration.g1-import.validation-report=build/g1-evidence/local-dtsx-candidates-approved-validation-report.json --partner.integration.g1-import.import-report=build/g1-evidence/local-dtsx-candidates-approved-import-report.json'
```

결과: approval guard 통과, validation conclusion은 `BLOCKED_LOCAL_CANDIDATE`

```bash
git diff --check
```

결과: 통과

```bash
./gradlew test --rerun-tasks
```

결과: `BUILD SUCCESSFUL in 6s`

## 커밋

- `0f28d89 [ssis-kotlin-batch-migration] Generate G1 approval decision`
- `437a57e [ssis-kotlin-batch-migration] Localize README headings`
