---
phase: 7
phase_name: Post-Migration Delivery Modernization
artifact: delivery_options
status: drafted
created: 2026-06-19
requirements:
  - DELIV-01
---

# Phase 7 Delivery Options

## Requirement

All post-migration delivery options must support private communication. Public URL plus token is not enough for this project constraint.

## Option Comparison

| Option | Best fit | Strengths | Risks / cost | Private-only requirement |
|---|---|---|---|---|
| Private web endpoint | Partners already poll HTTP/static artifacts and need URL-style access | Simple consumer model; good readback/probe semantics; can expose latest artifact, manifest, checksum, and versioned paths; works for JSONL/JS, TXT, TSV, XML | Requires endpoint/auth/DNS/path approval; service availability becomes delivery dependency; cache and partial publish behavior must be designed | Private HTTPS via VPN, private link, allowlist, mTLS, or equivalent |
| SFTP/FTPS | Partners are file-drop oriented or depend on FTP-like workflows | Lowest migration friction from FTP; familiar operations; good for large batch files and retransfer; maps well to `FtpPublisher` | Account/key management; directory cleanup risk; FTPS firewall/passive-mode issues; weaker for non-file/API contracts | Private network paths and approved runtime allowlists; prefer SFTP if new |
| Object storage / private CDN-style delivery | Static artifacts, many reads, versioned artifact keys, lifecycle retention, immutable archive | Best lifecycle story; strong checksum/readback; good for split Google files and Kakao/Daum six-file group | Partner capability varies; CDN-style can accidentally become public; listing/manifest design needed | Private object access only: VPC endpoint, private link, VPN, allowlist, or private distribution |
| API / payload delivery | Non-file integrations, request/response contracts, idempotent partner transactions | Explicit idempotency, retry, schema versioning, status semantics; best for non-file artifacts | Highest partner change cost; requires compatibility period, contract versioning, rate/error semantics, rollback story | Private API only: private endpoint, mTLS or equivalent auth, allowlisted network |

## Recommendation

Default evaluation path:

1. private object storage for artifact storage and lifecycle
2. private web endpoint for HTTP-style partner polling
3. SFTP as partner compatibility lane
4. API/payload delivery only for non-file or newly negotiated contracts

Do not implement this in v1. Each option requires separate post-migration approval and partner communication.

## Artifact Coverage

The delivery model must support:

- file artifact
- HTTP/static payload
- FTP payload
- SMB/UNC output
- API request/response payload
- delivery receipt
- readback probe
- remote object ID

Core batch generation should remain behind:

```text
partner integration artifact -> IntegrationPublisher -> targetAlias
```
