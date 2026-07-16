# Phase 31 Context: Derived File Generation Building Block

## Problem

Phase 28 identified three NaverShop Script Task work items that generate derived output files:

- `DTS_NaverShopDBFile_Make` / `Make Procuct`
- `DTS_NaverShopDBFile_Make` / `Make Yesterday Sales`
- `DTS_NaverShopDBFile_Make_Today` / `Make Today Procuct`

The upstream SQL/SP and golden output evidence still require G1 approval. A local generation building block can still be implemented now by treating the upstream query result as structured rows and writing the target delimited artifact with explicit contract rules.

## Target

Add a local Kotlin service that can back future Spring Batch tasklets for derived file generation:

- explicit source name
- explicit field count
- delimiter/newline/encoding rules
- null token handling
- overwrite/symlink safety
- byte/SHA-256 readback stats

## Non-Goal

This does not execute SQL/SP and does not claim NaverShop SSIS equivalence.
