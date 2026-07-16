---
phase_name: G1 Fragment Template Directory Generation
status: complete
updated: 2026-06-19
---

# Phase 20 Context: G1 Fragment Template Directory Generation

Phase 19 added an importer for operator-supplied G1 read-only export fragments. To reduce hand-editing risk, the app should also produce the exact fragment directory skeleton operators will fill after G1 approval.

## Scope

- Add a local-only writer that splits a `G1EvidencePack` into the seven required fragment files.
- Add a runner that generates a placeholder template fragment directory.
- Protect non-empty output roots unless overwrite is explicit.
- Verify template fragment directory can be imported by the Phase 19 importer.

## Boundaries

- No SQL Server, FTP, SMB, HTTP, API, production, or partner-facing access.
- No YouTrack, KB, commit, push, or PR action.
- Generated placeholders are not G1 evidence and must not pass validation.
