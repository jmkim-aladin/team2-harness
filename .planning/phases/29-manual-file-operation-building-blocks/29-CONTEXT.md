# Phase 29 Context: Manual File Operation Building Blocks

## Problem

Phase 28 split 17 DTSX manual-review steps into concrete work items. Thirteen of those are file-oriented and can be implemented locally without G1 evidence:

- artifact copy tasklet: 7
- encoding transcode tasklet: 4
- retention cleanup tasklet: 2

## Constraint

No DB, SQL Agent, FTP, SMB, HTTP, API, production, YouTrack, KB, push, or PR action.

## Target

Add side-effect-bounded local Kotlin services that can back future Spring Batch tasklets for these file-oriented Script Task replacements.
