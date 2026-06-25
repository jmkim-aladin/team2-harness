---
phase: 7
phase_name: Post-Migration Delivery Modernization
artifact: partner_migration
status: drafted
created: 2026-06-19
requirements:
  - DELIV-03
---

# Phase 7 Partner Migration

## Strategy

v1 remains unchanged. Phase 7 is a separate post-migration delivery project.

Recommended migration model:

1. Keep `contractVersion=v1` for payloads if bytes/schema stay unchanged.
2. Introduce a new delivery `targetAlias` instead of mutating the existing alias.
3. Use dual delivery during compatibility period.
4. Require partner readback or ingestion evidence before any DNS, path, protocol, or auth switch.
5. Retire old targets only after partner sign-off, clean monitoring, and rollback rehearsal.

Example aliases:

```text
naverBook.www2.v2
google.sftp.v2
kakaoDaum.privateWeb.v2
```

## Change Gates

| Change | Gate |
|---|---|
| DNS | create new host/CNAME first; keep existing `www2.aladin.co.kr` and `ftp.aladin.co.kr`; repoint existing DNS only as final approved step |
| Protocol | choose per partner; no blanket migration |
| Path | freeze existing path; use `/v2/` or partner prefix for new path |
| Auth | keep existing auth through compatibility period; issue separate credential/key/cert/token for new target |
| Contract | preserve payload unless separate partner contract change is approved |

Secret values must not appear in documents, logs, tickets, manifests, or commits.

## Compatibility Period

Default:

- 90 days dual delivery per partner
- optional 30-day extension for major partners

Shortening requires:

- at least two successful full artifact deliveries
- at least 14 days of clean daily/today deliveries
- partner ingestion confirmation
- readback/checksum match
- incident response and rollback rehearsal complete

## Partner Communication Draft

```text
DB 이관 이후 별도 단계로 연동 파일/데이터 제공 방식을 개선하려고 합니다.

현재 운영 중인 제공 방식은 바로 변경하지 않습니다. 기존 URL, FTP 경로, 파일명, 데이터 포맷, 제공 시각, 인증 방식은 유지됩니다.

신규 제공 방식은 파트너별로 사전 테스트 후 전환합니다. 테스트 기간에는 기존 방식과 신규 방식을 병행 제공하며, 신규 방식의 수신/검증이 안정적으로 확인된 뒤에만 전환 일정을 확정하겠습니다.

변경 대상이 되는 항목은 파트너별로 별도 안내드립니다.
- 접속 주소 또는 DNS
- 프로토콜: HTTPS, SFTP/FTPS 등
- 파일 또는 데이터 경로
- 인증 방식: 계정, 키, 인증서, 토큰 등
- 장애 시 기존 방식으로 되돌리는 기준

전환 전에는 테스트 계정/경로, 샘플 산출물, 체크섬 또는 건수 검증 기준, 롤백 기준을 함께 공유하겠습니다.
```

## Evidence Packet

For each `integrationId + mode + contractVersion + targetAlias`:

- existing v1 artifact hash
- row or node count
- byte count
- new target publish attempt
- readback result
- partner ingestion acknowledgment
- remote checksum/size
- auth success log
- manifest event IDs
- rollback rehearsal ID
- owner, backup owner, rollback owner sign-off

## Rollback

During dual delivery:

- keep existing target primary
- stop v2 publish
- partner continues v1 target

After DNS/path/protocol/auth switch:

- restore previous CNAME/route within TTL
- retransfer previous known-good artifact from archive to existing target
- revoke or pause v2 credentials if needed
- keep manifest event IDs and partner confirmation

Rollback triggers:

- auth failure
- checksum mismatch
- partner ingestion failure
- schedule miss
- readback failure
- partner incident report
