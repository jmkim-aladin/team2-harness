# Phase 1: DTSX Evidence Lock - Context

**Gathered:** 2026-06-19
**Status:** Ready for planning
**Source:** User decisions, project initialization, local Excel/DTSX inspection

<domain>

## Phase Boundary

Phase 1 locks the evidence model for Excel 업무 번호 13-17. It does not implement Kotlin batch code. It produces the canonical ledger shape and the read-only evidence request needed to prove which DTSX packages are active in production.

</domain>

<decisions>

## Implementation Decisions

### Stack

- Kotlin is mandatory.
- Spring baseline is Spring Boot 4.1.x stable line and Spring Batch 6.0.x.
- Kotlin 2.2+ is the minimum Kotlin line for Boot 4.
- The repo name/path is `/Users/jm/Documents/workspace/b2b/partner-integration-batch`.

### Migration Approach

- Do not auto-convert DTSX into production Kotlin code.
- Reverse-engineer DTSX as current batch specification.
- Existing SP/SQL calls are wrapped first through `LegacyDbAdapter`.
- File/protocol/path modernization is after migration, not v1.

### Phase 1 Scope

- Build the ledger.
- Extract DTSX inventory from local repo and Excel.
- Mark SQL Agent/DB/SP/golden output as approval-required evidence.
- Keep row 15 blocked until active SQL Agent job confirms scope.

</decisions>

<canonical_refs>

## Canonical References

### Project Planning

- `.planning/PROJECT.md` - project context and decisions
- `.planning/ROADMAP.md` - phase structure
- `.planning/REQUIREMENTS.md` - mapped requirements
- `.planning/LEDGER.md` - evidence ledger

### Local Inputs

- `/Users/jm/Documents/workspace/ssis/B2B 배치.xlsx` - Excel source rows 13-17
- `/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_NaverDBFile` - Naver/NaverShop candidate DTSX
- `/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_GoogleShop_DBFile` - Google candidate DTSX
- `/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_DaumDBFile_Make` - Kakao/Daum candidate DTSX
- `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/projects/db-idc-migration/2026-06-b2b-ssis-13-17-kotlin-batch-transition.md` - prior analysis note

### Official Spring Sources

- `https://spring.io/projects/spring-boot`
- `https://docs.spring.io/spring-boot/system-requirements.html`
- `https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide`
- `https://spring.io/projects/spring-batch`
- `https://docs.spring.io/spring-batch/reference/whatsnew.html`

</canonical_refs>

<specifics>

## Specific Ideas

- Use `Excel row -> partner/integration -> DTSX package -> control-flow task -> DB object/SP/table -> artifact -> publish endpoint -> cleanup/retention` as the graph model.
- Use `kakaoDaumFeedJob` as the likely first implementation slice after evidence lock because row 17 has the clearest output mapping.
- Use the ledger as the source of truth for implementation readiness.

</specifics>

<deferred>

## Deferred Ideas

- Actual repo scaffolding and Kotlin code belong after Phase 1 evidence lock or Phase 2 architecture baseline.
- Delivery modernization belongs after DB migration v1.
- Production cutover requires later approval.

</deferred>

---

*Phase: 01-dtsx-evidence-lock*
*Context gathered: 2026-06-19*
