# Research: Features

## Table Stakes

- DTSX inventory from Excel row to package, task, DB object, artifact, publish endpoint.
- Spring Batch job model per external partner integration contract.
- Legacy DB/SP boundary through `LegacyDbAdapter`.
- Streaming artifact generation for JSONL, TXT/TSV, XML, and non-file outputs where needed.
- Manifest with run, artifact, validation, publish, readback status.
- Idempotent restart and separate rebuild/retransfer.
- Shadow-run validation against existing SSIS output.
- Compatibility delivery bridge that preserves v1 file/HTTP/FTP/API contract.
- Manual rerun/retransfer and rollback procedure.

## Differentiators

- Package-level dependency graph generated from DTSX XML.
- Byte-level golden-file comparison with row count/checksum/aggregate checks.
- Integration contract versioning per partner/feed/API/mode.
- Active SQL Agent job confirmation matrix before implementation.
- Post-migration delivery modernization roadmap separated from DB migration.

## Anti-Features

- Auto-converting DTSX into production Kotlin code.
- Loading full partner feeds into JVM memory.
- Letting SP names and side effects spread through job definitions.
- Writing directly to final FTP/WWW/SMB paths before validation passes.
- Bundling delivery modernization into the migration cutover.
