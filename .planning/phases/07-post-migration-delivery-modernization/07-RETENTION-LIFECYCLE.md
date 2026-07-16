---
phase: 7
phase_name: Post-Migration Delivery Modernization
artifact: retention_lifecycle
status: drafted
created: 2026-06-19
requirements:
  - DELIV-02
---

# Phase 7 Retention Lifecycle

## Principle

Replace SSIS-style delete/cleanup tasks with a manifest-driven `LifecyclePolicy` after migration. Do not ship lifecycle replacement with v1 cutover.

## Policy Shape

Policies select by manifest fields, not raw path globs.

```yaml
lifecyclePolicy:
  policyId:
  integrationId:
  mode:
  contractVersion:
  targetAlias:
  artifactType:
  zone: candidate/work | candidate/validated | candidate/archive | production/validated | production/archive | partner-facing
  runPurposeAllowed: [SHADOW, PRODUCTION, RETRANSFER]
  partnerVisibleAllowed: false
  selector:
    manifestStatus:
    artifactKeyPattern:
    createdBefore:
  action: expire | transition | archive | redactPayload | revoke | supersedeRemote | deleteRemote
  dryRunRequired: true
  approvalGateId:
  retainMinimumCount:
  retainUntil:
  holdReasons:
```

`validated` means internal artifact state. It does not mean safe to expose or delete.

## Zone Safety Rules

| Zone | Rule |
|---|---|
| `candidate/work` | Short TTL cleanup allowed only under `candidate/...`; shadow cleanup must never touch non-candidate paths |
| `candidate/validated` | Immutable until validation reports, clean-run evidence, and cutover decisions no longer reference it |
| `candidate/archive` | Evidence store; transition or cold storage first; physical delete only after retention approval |
| `production/validated` | Source for publish and retransfer; retain previous known-good artifacts through rollback window |
| `production/archive` | Audit/evidence; delete only when no manifest event, incident, validation report, or partner request references it |
| `partner-facing` | No lifecycle change without separate Phase 7 approval and partner communication |

## Hard Gates

1. Phase gate: lifecycle replacement cannot ship with v1 cutover.
2. Inventory gate: enumerate all SSIS cleanup/delete behavior first.
3. Namespace gate: every lifecycle plan must include `zone`, `runPurpose`, `targetAlias`, `partnerVisible`, and manifest selector.
4. Shadow gate: when `runPurpose=SHADOW`, lifecycle can affect only candidate paths.
5. Dry-run gate: deletion plans must produce manifest-backed dry-run report before any mutation.
6. Hold gate: block deletion if artifact is referenced by validation report, cutover packet, rollback rehearsal, previous-known-good artifact, retransfer request, incident/change record, or golden baseline.
7. Partner gate: partner-facing path, URL, protocol, DNS, auth, or cache behavior changes require separate approval and communication.
8. Alert gate: alert if retention/delete candidate includes non-candidate or partner-facing path.

## Non-File Artifacts

Lifecycle applies to partner integration artifacts, not only files.

Include:

- API request/response payloads
- HTTP/static payloads
- remote object IDs
- delivery receipts
- readback probes
- idempotency keys
- signed URL metadata
- partner-visible resource versions

For non-file artifacts, retention actions may be:

- redact stored payload body while keeping hash, schema version, idempotency key, and readback receipt
- expire signed URL or token reference without deleting immutable evidence
- supersede or withdraw remote resource only when the partner contract/API supports idempotent reversal
- keep manifest events long enough to prove what was sent, when, and under which contract
