---
phase_name: G1 Evidence Directory Import
status: complete
updated: 2026-06-19
---

# Phase 19 Context: G1 Evidence Directory Import

Phase 18 created a fill-in template pack. The next useful local step is accepting operator-provided read-only export fragments after G1 approval without requiring the operator to hand-edit one large JSON pack.

## Scope

- Add a local-only importer for a fixed fragment directory.
- Assemble the fragments into `G1EvidencePack`.
- Reuse the existing `G1EvidencePackValidator`.
- Record import and validation reports under `build/g1-evidence/`.

## Boundaries

- No SQL Server, FTP, SMB, HTTP, API, production, or partner-facing access.
- No YouTrack, KB, commit, push, or PR action.
- Placeholder/template fragments must not be treated as G1 pass evidence.

## Required Fragments

- `pack-metadata.json`
- `sql-agent-jobs.json`
- `deployed-dtsx-packages.json`
- `stored-procedures.json`
- `golden-outputs.json`
- `publish-targets.json`
- `runtime-evidence.json`
