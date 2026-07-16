# Phase 43 Context - Legacy SQL Call Adapter Plan

## Situation

The project decision says existing SP/SQL calls must stay behind `LegacyDbAdapter`, but the current implementation only has a small Kakao/Daum no-op adapter method. The DTSX migration spec already contains SQL/SP candidates from priority 13-17 packages, but there is no machine-readable plan that proves those candidates are contained at the legacy boundary.

## Boundary

This phase does not connect to SQL Server, SQL Agent, FTP, SMB, HTTP, APIs, production paths, or partner endpoints. It reads only the local DTSX migration spec JSON and writes a local report.

## Inputs

- `docs/dtsx-spec/priority-13-17-migration-spec.json`
- `LegacyDbAdapter` boundary decision from the project state

## Output

- Legacy SQL call adapter plan model/generator/runner
- Sample report showing procedure call candidates and unresolved SQL candidates
