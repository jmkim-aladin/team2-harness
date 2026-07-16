---
phase: 7
phase_name: Post-Migration Delivery Modernization
artifact: research
status: drafted
created: 2026-06-19
requirements:
  - DELIV-01
  - DELIV-02
  - DELIV-03
---

# Phase 7 Research: Post-Migration Delivery Modernization

## Research Sources

This phase used existing planning artifacts plus three parallel read-only agent passes:

- private delivery option comparison
- manifest-driven lifecycle/retention model
- partner migration and communication strategy

No agents edited files. No production endpoint, partner target, DB, YouTrack, KB, git, or schedule was changed.

## Findings

### Delivery Modernization Is Separate From v1

v1 remains unchanged. Existing URL, FTP, API, WWW, SMB targets, artifact keys, file names, format, encoding, schedule semantics, auth path, and readback expectations stay as-is.

Phase 7 introduces new `targetAlias` values instead of mutating existing aliases.

### Recommended Option Stance

For file/static artifacts, the default evaluation path is private object storage with private web endpoint access where partners need polling.

SFTP is a compatibility lane for partners that cannot consume private HTTPS/object delivery.

API/payload delivery is for non-file or newly negotiated contracts, not a blanket replacement for every feed.

### Lifecycle Is Manifest-Driven

Retention should be a manifest-driven `LifecyclePolicy`, not another generation-time delete script.

Policies must select artifacts by manifest fields such as `integrationId`, `mode`, `contractVersion`, `targetAlias`, `zone`, `runPurpose`, and `partnerVisible`, not raw wildcard paths.

### Partner Migration Uses Dual Delivery

Recommended model:

1. Keep `contractVersion=v1` when payload bytes/schema stay unchanged.
2. Add a new delivery target alias such as `naverBook.www2.v2` or `google.sftp.v2`.
3. Run dual delivery during compatibility period.
4. Require partner readback/ingestion evidence before DNS, path, protocol, or auth switch.
5. Retire old target only after sign-off, clean monitoring, and rollback rehearsal.
