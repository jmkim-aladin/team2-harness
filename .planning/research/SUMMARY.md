# Research Summary

## Key Findings

**Stack:** standalone Kotlin + Spring Boot + Spring Batch app, with `LegacyDbAdapter`, streaming feed generators, feed manifest, and v1 compatibility delivery bridge.

**Table Stakes:** DTSX inventory, active SQL Agent confirmation, batch specification extraction, Spring Batch Job/Step model, legacy SP isolation, golden-file validation, shadow-run comparison, rollback-ready cutover.

**Watch Out For:** row 15 ambiguity, hidden staging side effects, full-feed memory usage, byte-level file contract drift, premature file delivery modernization, partial publish visibility.

## Direction

The project should start by reverse-engineering DTSX into a deterministic batch specification. Only after the spec is locked should implementation begin. The implementation should preserve the current file delivery contract during DB migration and defer protocol/path redesign until after migration.

## Recommended First Slice

Use `kakaoDaumFeedJob` as the first implementation slice after Phase 1-3 because row 17 has the clearest DTSX-to-output mapping: six XML outputs plus retention behavior. Keep row 15 blocked until SQL Agent active package confirmation.
