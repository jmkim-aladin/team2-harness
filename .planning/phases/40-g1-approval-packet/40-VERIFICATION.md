# Phase 40 Verification - G1 Approval Packet

## Commands

```bash
./gradlew test --tests 'kr.co.aladin.partner.integration.batch.g1.G1ApprovalPacket*'
```

```bash
./gradlew bootRun --args='--partner.integration.g1-approval.enabled=true --partner.integration.g1-approval.readiness-report=docs/readiness/sample-report.json --partner.integration.g1-approval.request-bundle=docs/g1-evidence/request-bundle.json --partner.integration.g1-approval.packet-id=g1-approval-sample --partner.integration.g1-approval.created-at=2026-06-19T00:00:00Z --partner.integration.g1-approval.output=docs/g1-evidence/approval-packet.json'
```

## Expected

- focused approval packet tests pass
- runner writes `docs/g1-evidence/approval-packet.json`
- packet status is `APPROVAL_REQUIRED`
- packet has four blocking gates
- packet has 7 required fragments, 7 target requests, 4 read-only query ids, and 6 forbidden actions
- no external endpoint, DB, SQL Agent, DTSX execution, or partner-facing publish is touched

## Actual

- focused approval packet tests: passed
- G1 focused suite: 17 tests passed
- runner wrote `docs/g1-evidence/approval-packet.json`
- packet values:
  - `status=APPROVAL_REQUIRED`
  - blocking gates: 4
  - required fragments: 7
  - target requests: 7
  - read-only query ids: 4
  - forbidden actions: 6
- full Gradle test: 118 tests, 0 failures/errors
