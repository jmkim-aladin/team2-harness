# Phase 28 Plan: DTSX Manual Review Worklist

## Objective

Make the 17 DTSX manual-review blockers actionable by generating a Kotlin/Spring Batch worklist.

## Tasks

1. Add worklist report model.
2. Add generator with resolution heuristics:
   - copy -> artifact copy tasklet
   - Unicode -> encoding transcode tasklet
   - old/delete -> retention cleanup tasklet
   - loop -> partitioned multi-file writer
   - make -> derived file generation tasklet
3. Add CLI runner.
4. Add tests and docs.
5. Verify with actual priority 13-17 spec.
