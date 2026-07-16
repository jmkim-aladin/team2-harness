# Phase 35 Plan: Exchange Catalog Readiness Gate

## Objective

Add the Phase 34 exchange catalog as a required migration readiness gate.

## Tasks

1. Add failing readiness evaluator coverage for the new gate.
2. Add failing command runner coverage for `--partner.integration.readiness.exchange-catalog-report`.
3. Add `EXCHANGE_CATALOG` to readiness gates.
4. Block readiness if the exchange catalog is missing, empty, or file-only.
5. Update the sample readiness report and documentation.
6. Run focused tests, runner smoke, and full tests.

## Success Criteria

- Readiness has 6 required gates.
- A valid exchange catalog passes with 19 contracts and 1 blocked integration.
- Missing or file-only exchange catalog keeps readiness `BLOCKED`.
- Sample readiness report includes `EXCHANGE_CATALOG`.
- Full tests pass.
