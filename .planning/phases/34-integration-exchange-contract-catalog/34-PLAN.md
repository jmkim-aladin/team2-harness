# Phase 34 Plan: Integration Exchange Contract Catalog

## Objective

Make the local implementation model file-compatible but not file-only by introducing an integration exchange contract catalog.

## Tasks

1. Add TDD coverage for current priority outputs as outbound file exchanges.
2. Add TDD coverage for inbound non-file exchange contracts without file names.
3. Implement exchange contract models and catalog generation.
4. Add a command-line runner that writes a JSON exchange catalog report.
5. Generate a sample report and update README/ledger.
6. Run focused tests, full tests, and a runner smoke.

## Success Criteria

- Current runnable priority targets produce 19 outbound file exchange contracts.
- `NAVER_RANKING` remains blocked until G1.
- A non-file inbound contract can be represented without `fileNamePattern`.
- The runner writes `docs/exchange-catalog/sample-report.json`.
- No external endpoints or production systems are touched.
