---
phase: 7
phase_name: Post-Migration Delivery Modernization
artifact: context
status: drafted
created: 2026-06-19
requirements:
  - DELIV-01
  - DELIV-02
  - DELIV-03
---

# Phase 7 Context: Post-Migration Delivery Modernization

## Purpose

Phase 7 defines post-migration options for modernizing partner delivery after the SSIS-to-Kotlin Spring Batch replacement is stable.

This phase is intentionally separated from v1. The v1 migration preserves existing partner-visible delivery contracts through `IntegrationPublisher` compatibility adapters.

## Scope

In scope:

- private delivery option comparison
- retention/lifecycle modernization
- partner communication and compatibility-period planning
- support for file and non-file partner integration artifacts

Out of scope:

- v1 cutover
- immediate DNS, protocol, path, auth, URL, or partner contract change
- production delivery migration
- DB, SQL Agent, FTP, HTTP, SMB, API, or partner endpoint changes

## Baseline

The internal model remains:

```text
partner integration artifact -> IntegrationPublisher -> targetAlias
```

The artifact may be a file, HTTP/static payload, FTP payload, SMB output, API payload, or other partner-facing contract. Delivery modernization changes the `IntegrationPublisher` target, not the core generation and validation model.
