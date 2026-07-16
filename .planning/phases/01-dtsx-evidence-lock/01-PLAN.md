---
phase: 1
phase_name: DTSX Evidence Lock
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/LEDGER.md
  - .planning/phases/01-dtsx-evidence-lock/01-CONTEXT.md
  - .planning/phases/01-dtsx-evidence-lock/01-RESEARCH.md
  - .planning/phases/01-dtsx-evidence-lock/01-PLAN.md
autonomous: true
requirements:
  - INV-01
  - INV-02
  - INV-03
  - INV-04
---

# Phase 1 Plan: DTSX Evidence Lock

<objective>
Create and verify the evidence ledger that maps Excel rows 13-17 to DTSX candidates, operation classes, Spring Batch job candidates, and approval-required production evidence. Do not implement Kotlin production code in this phase.
</objective>

<must_haves>
- Ledger exists at `.planning/LEDGER.md`.
- Ledger maps Excel physical rows 15-19 to 업무 번호 13-17.
- Ledger marks row 15 as blocked until active SQL Agent evidence confirms exact scope.
- Ledger separates local candidate evidence from production canonical evidence.
- Phase 1 output defines approval-required read-only evidence before implementation.
</must_haves>

<tasks>

<task id="T1" type="execute">
<title>Verify local Excel and DTSX candidate inventory</title>
<read_first>
- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/LEDGER.md`
- `/Users/jm/Documents/workspace/ssis/B2B 배치.xlsx`
- `/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_NaverDBFile`
- `/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_GoogleShop_DBFile`
- `/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_DaumDBFile_Make`
</read_first>
<action>
Confirm that `.planning/LEDGER.md` contains rows for Excel physical rows `15`, `16`, `17`, `18`, `19` and 업무 번호 `13`, `14`, `15`, `16`, `17`. Confirm DTSX candidates include `DTS_NaverDBFile_Make_V2.dtsx`, `DTS_NaverDBFile_Make_V2_Today.dtsx`, `DTS_NaverShopDBFile_Make.dtsx`, `DTS_NaverShopDBFile_Make_Today.dtsx`, `DTS_NaverDBFile_BestSellerMake.dtsx`, `naver.dtsx`, `DTS_GoogleShop_DBFile_Make_TSV_V2.dtsx`, `DTS_GoogleShop_DBFile_Make_Today_TSV_V2.dtsx`, `KakaoDaum.dtsx`, and `DTS_DaumDBFile_OldDataDelete.dtsx`.
</action>
<acceptance_criteria>
- `.planning/LEDGER.md` contains `| 15 | 13 |`, `| 16 | 14 |`, `| 17 | 15 |`, `| 18 | 16 |`, `| 19 | 17 |`.
- `.planning/LEDGER.md` contains all DTSX candidate names listed in the action.
- Row 15 ledger status contains `Blocked` or `scope 모호`.
</acceptance_criteria>
</task>

<task id="T2" type="execute">
<title>Classify DTSX operations into migration categories</title>
<read_first>
- `.planning/LEDGER.md`
- `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/projects/db-idc-migration/2026-06-b2b-ssis-13-17-kotlin-batch-transition.md`
</read_first>
<action>
Ensure `.planning/LEDGER.md` has an operation classification table with rows for 업무 번호 `13`, `14`, `15`, `16`, and `17`. Categories must include extract, staging mutate, file generate, encoding/format transform, publish, cleanup/retention, and validation where applicable.
</action>
<acceptance_criteria>
- `.planning/LEDGER.md` contains heading `## DTSX Operation Classification`.
- `.planning/LEDGER.md` contains `legacyPrepareSnapshot`, `JSONL streaming writer`, `TXT writer`, `partition/range reader`, and `six XML step outputs`.
- `.planning/LEDGER.md` states that row 15 is pending active package confirmation.
</acceptance_criteria>
</task>

<task id="T3" type="execute">
<title>Define approval-required production evidence</title>
<read_first>
- `.planning/LEDGER.md`
- `.planning/STATE.md`
- `/Users/jm/Documents/workspace/team2/.codex/skills/dev2-team-harness-ko/SKILL.md`
</read_first>
<action>
Ensure `.planning/LEDGER.md` has a Required Evidence table for SQL Agent `msdb`, operational DTSX deployment, SP definitions, golden output files, publish/readback path access, and runtime account/secret/network allowlist. Mark each item as `Missing` and `Required` approval.
</action>
<acceptance_criteria>
- `.planning/LEDGER.md` contains `SQL Agent`, `운영 DTSX`, `SP definition`, `golden files`, `publish/readback`, and `runtime account`.
- Each evidence row has status `Missing`.
- Each evidence row has approval `Required`.
</acceptance_criteria>
</task>

<task id="T4" type="execute">
<title>Lock Kotlin/Spring version baseline for downstream phases</title>
<read_first>
- `.planning/PROJECT.md`
- `.planning/research/STACK.md`
- `.planning/STATE.md`
- `.planning/phases/01-dtsx-evidence-lock/01-RESEARCH.md`
</read_first>
<action>
Confirm all project planning artifacts describe the implementation baseline as Kotlin with Spring Boot `4.1.x` and Spring Batch `6.0.x`, with Kotlin `2.2+`. Confirm source URLs for Spring Boot, Spring Boot system requirements, Spring Boot 4 migration guide, Spring Batch project page, and Spring Batch 6 reference are present in `.planning/research/STACK.md` or phase research.
</action>
<acceptance_criteria>
- `.planning/PROJECT.md` contains `Kotlin + Spring Boot 4.1.x + Spring Batch 6.0.x`.
- `.planning/STATE.md` contains `Kotlin is mandatory`.
- `.planning/research/STACK.md` contains all five official Spring source URLs.
- `.planning/phases/01-dtsx-evidence-lock/01-RESEARCH.md` contains `Kotlin 2.2+`.
</acceptance_criteria>
</task>

</tasks>

<verification>

Run these checks:

```bash
test -f .planning/LEDGER.md
test -f .planning/phases/01-dtsx-evidence-lock/01-CONTEXT.md
test -f .planning/phases/01-dtsx-evidence-lock/01-RESEARCH.md
test -f .planning/phases/01-dtsx-evidence-lock/01-PLAN.md
rg -n "Kotlin \\+ Spring Boot 4\\.1\\.x \\+ Spring Batch 6\\.0\\.x|Kotlin 2\\.2\\+" .planning
rg -n "DTS_NaverDBFile_Make_V2\\.dtsx|DTS_NaverShopDBFile_Make\\.dtsx|DTS_GoogleShop_DBFile_Make_TSV_V2\\.dtsx|KakaoDaum\\.dtsx" .planning/LEDGER.md
rg -n "SQL Agent|SP definition|golden files|Missing|Required" .planning/LEDGER.md
```

</verification>

<success_criteria>
1. Phase 1 evidence ledger exists and is internally consistent.
2. All INV-01 through INV-04 requirements are represented by explicit tasks.
3. Production evidence gaps are documented as approval-required, not silently assumed.
4. The downstream implementation baseline is Kotlin + Spring Boot 4.1.x + Spring Batch 6.0.x.
</success_criteria>
