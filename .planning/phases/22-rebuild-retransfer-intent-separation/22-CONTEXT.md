---
phase_name: Rebuild Retransfer Intent Separation
status: complete
updated: 2026-06-19
---

# Phase 22 Context: Rebuild Retransfer Intent Separation

SSIS replacement needs different operator paths for rebuilding a feed artifact and retransferring an already validated artifact. Treating both as one generation run can overwrite evidence and hide whether a partner issue is content generation or delivery.

## Scope

- Add `forceRebuild` and `retransferArtifactId` job parameter support.
- Reject invalid rebuild/retransfer combinations.
- Persist rebuild/retransfer intent in manifest run records.
- Block retransfer before artifact generation until publish-from-manifest exists.

## Boundaries

- No real retransfer publishing yet.
- No DB/SP/SQL Agent/prod access.
- No commit, push, PR, YouTrack, or KB update.
