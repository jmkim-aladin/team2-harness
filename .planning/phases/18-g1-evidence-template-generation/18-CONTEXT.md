---
phase_name: G1 Evidence Template Generation
status: complete
updated: 2026-06-19
---

# Phase 18 Context: G1 Evidence Template Generation

Phase 16 can validate a completed G1 evidence pack, but an operator still needs a complete fill-in skeleton before approved read-only evidence collection begins. Phase 18 adds a deterministic template generator so no required integration/mode target is omitted during G1 collection.

This phase does not query SQL Agent, SQL Server, SSIS deployment storage, partner publish targets, or production systems. It only generates a local JSON template in the existing `G1EvidencePack` shape.

## Scope

- Share the required target list between validator and template generator.
- Generate placeholder SQL Agent, deployed DTSX, stored procedure, golden output, publish target, and runtime/private-network evidence for every required target.
- Keep the generated template from passing validation while placeholders remain.
- Provide a command-line runner and deterministic sample template.

## Evidence Added

- `G1RequiredTargets`
- `G1EvidenceTemplateGenerator`
- `G1EvidenceTemplateCommandLineRunner`
- `docs/g1-evidence/template-pack.json`
