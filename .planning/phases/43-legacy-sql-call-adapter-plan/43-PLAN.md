# Phase 43 Plan - Legacy SQL Call Adapter Plan

## Goal

Generate a local adapter-boundary plan from DTSX SQL/SP candidates so legacy DB behavior stays outside the Spring Batch core.

## Steps

1. Add RED tests for stored procedure extraction from DTSX SQL previews.
2. Add RED tests that `select`/unknown SQL remains manual adapter review.
3. Add a command runner that reads DTSX migration spec JSON and writes a report.
4. Add committed sample report under `docs/legacy-sql/`.
5. Update README, migration ledger, and GSD planning ledger.
6. Run focused tests, actual runner, and full tests.

## Acceptance

- SQL candidates from DTSX specs are counted.
- Procedure calls have normalized procedure names and argument text.
- Unresolved SQL cannot be treated as ready.
- Report records `LegacyDbAdapter` as the adapter boundary.
- No external systems are touched.
