---
phase: 4
phase_name: Feed Job Design And First Conversion Plan
plan: 04
type: execute
wave: 1
depends_on:
  - 01-dtsx-evidence-lock
  - 02-spring-batch-architecture-baseline
  - 03-validation-harness-specification
files_modified:
  - .planning/phases/04-feed-job-design-and-first-conversion-plan/04-CONTEXT.md
  - .planning/phases/04-feed-job-design-and-first-conversion-plan/04-RESEARCH.md
  - .planning/phases/04-feed-job-design-and-first-conversion-plan/04-PLAN.md
  - .planning/phases/04-feed-job-design-and-first-conversion-plan/04-NAVER.md
  - .planning/phases/04-feed-job-design-and-first-conversion-plan/04-GOOGLE.md
  - .planning/phases/04-feed-job-design-and-first-conversion-plan/04-KAKAO-DAUM.md
  - .planning/phases/04-feed-job-design-and-first-conversion-plan/04-FIRST-SLICE.md
autonomous: true
requirements:
  - FEED-01
  - FEED-02
  - FEED-03
  - FEED-04
  - FEED-05
---

# Phase 4 Plan: Feed Job Design And First Conversion Plan

<objective>
Define feed-specific Job/Step/output contracts for Naver book, Naver shopping, Naver ranking, Google, and Kakao/Daum. Select the first vertical slice for later implementation without creating a repo or touching DB/prod.
</objective>

<must_haves>
- `kakaoDaumFeedJob` is selected as first vertical slice or a concrete alternative is documented.
- Naver book, Naver shopping, Google, and Kakao/Daum have Job/Step/output contract designs.
- `naverRankingFeedJob` remains blocked until G1/row 15 evidence.
- Google split `groupId` is modeled as partition/step context, not top-level JobParameter.
- full/today uses `mode`; same-day multiple runs use `scheduleSlot` or `windowKey`.
- All feed designs list G1 blockers and validation needs.
</must_haves>

<tasks>

<task id="T1" type="execute">
<title>Create Naver feed design</title>
<read_first>
- `.planning/LEDGER.md`
- `.planning/phases/04-feed-job-design-and-first-conversion-plan/04-RESEARCH.md`
- `/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_NaverDBFile`
</read_first>
<action>
Create `.planning/phases/04-feed-job-design-and-first-conversion-plan/04-NAVER.md`. It must define `naverBookFeedJob`, `naverShoppingFeedJob`, and blocked `naverRankingFeedJob`. Include DTSX candidates, modes, likely steps, outputs, validation needs, unknowns, and G1 blockers.
</action>
<acceptance_criteria>
- `04-NAVER.md` contains `naverBookFeedJob`, `naverShoppingFeedJob`, and `naverRankingFeedJob`.
- `04-NAVER.md` contains `DTS_NaverDBFile_Make_V2.dtsx`, `DTS_NaverDBFile_Make_V2_Today.dtsx`, `DTS_NaverShopDBFile_Make.dtsx`, and `DTS_NaverShopDBFile_Make_Today.dtsx`.
- `04-NAVER.md` states `naverRankingFeedJob` is blocked until G1.
- `04-NAVER.md` contains `JsonlComparator`, `JsonlJsEnvelopeHandler`, and `TxtComparator`.
</acceptance_criteria>
</task>

<task id="T2" type="execute">
<title>Create Google feed design</title>
<read_first>
- `.planning/LEDGER.md`
- `.planning/phases/04-feed-job-design-and-first-conversion-plan/04-RESEARCH.md`
- `/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_GoogleShop_DBFile`
</read_first>
<action>
Create `.planning/phases/04-feed-job-design-and-first-conversion-plan/04-GOOGLE.md`. It must define `googleShoppingFeedJob`, full/today modes, TSV V2 DTSX candidates, full five-file split, `groupId` partition handling, `scheduleSlot` or `windowKey`, validation needs, unknowns, and G1 blockers.
</action>
<acceptance_criteria>
- `04-GOOGLE.md` contains `googleShoppingFeedJob`.
- `04-GOOGLE.md` contains `DTS_GoogleShop_DBFile_Make_TSV_V2.dtsx` and `DTS_GoogleShop_DBFile_Make_Today_TSV_V2.dtsx`.
- `04-GOOGLE.md` contains `product_aladin_1.txt` and `product_aladin_today.txt`.
- `04-GOOGLE.md` states `groupId` is a `StepExecutionContext` partition key.
- `04-GOOGLE.md` contains `scheduleSlot` or `windowKey`.
- `04-GOOGLE.md` contains `MultiResourceTsvComparator`.
</acceptance_criteria>
</task>

<task id="T3" type="execute">
<title>Create Kakao/Daum feed and retention design</title>
<read_first>
- `.planning/LEDGER.md`
- `.planning/phases/04-feed-job-design-and-first-conversion-plan/04-RESEARCH.md`
- `/Users/jm/Documents/workspace/ssis/dev1-ssis-cool/src/DTS_DaumDBFile_Make`
</read_first>
<action>
Create `.planning/phases/04-feed-job-design-and-first-conversion-plan/04-KAKAO-DAUM.md`. It must define `kakaoDaumFeedJob`, `feedRetentionJob`, six XML outputs, SP calls, encoding evidence, output order, direct-write chain decision, validation needs, and G1 blockers.
</action>
<acceptance_criteria>
- `04-KAKAO-DAUM.md` contains `kakaoDaumFeedJob` and `feedRetentionJob`.
- `04-KAKAO-DAUM.md` contains all six XML output names: `selling.xml`, `ebook_selling.xml`, `event.xml`, `ebook_event.xml`, `eventbook.xml`, `ebook_eventbook.xml`.
- `04-KAKAO-DAUM.md` contains `KakaoDaum_Book_Selling`, `KakaoDaum_Book_Event`, and `KakaoDaum_Book_EventBook`.
- `04-KAKAO-DAUM.md` states disabled temp-file copy script path is not recreated.
- `04-KAKAO-DAUM.md` contains `XmlComparator`.
</acceptance_criteria>
</task>

<task id="T4" type="execute">
<title>Create first vertical slice decision and update traceability</title>
<read_first>
- `.planning/STATE.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/phases/04-feed-job-design-and-first-conversion-plan/04-NAVER.md`
- `.planning/phases/04-feed-job-design-and-first-conversion-plan/04-GOOGLE.md`
- `.planning/phases/04-feed-job-design-and-first-conversion-plan/04-KAKAO-DAUM.md`
</read_first>
<action>
Create `.planning/phases/04-feed-job-design-and-first-conversion-plan/04-FIRST-SLICE.md` selecting `kakaoDaumFeedJob` as the first vertical slice after G1/repo approval. Update `.planning/STATE.md` current focus to Phase 4. Update `.planning/REQUIREMENTS.md` traceability for `FEED-01` through `FEED-05` to Specified, with `FEED-03` blocked by G1. Update `.planning/ROADMAP.md` next phase guidance to Phase 5 shadow run/operational hardening after G1 and repo approval.
</action>
<acceptance_criteria>
- `04-FIRST-SLICE.md` contains `kakaoDaumFeedJob`.
- `04-FIRST-SLICE.md` contains `first vertical slice`.
- `04-FIRST-SLICE.md` states implementation waits for G1 and repo creation approval.
- `.planning/REQUIREMENTS.md` contains `FEED-03` with `Blocked by G1`.
- `.planning/STATE.md` contains `Phase 4 - Feed Job Design And First Conversion Plan`.
</acceptance_criteria>
</task>

</tasks>

<verification>

Run these checks:

```bash
test -f .planning/phases/04-feed-job-design-and-first-conversion-plan/04-NAVER.md
test -f .planning/phases/04-feed-job-design-and-first-conversion-plan/04-GOOGLE.md
test -f .planning/phases/04-feed-job-design-and-first-conversion-plan/04-KAKAO-DAUM.md
test -f .planning/phases/04-feed-job-design-and-first-conversion-plan/04-FIRST-SLICE.md
rg -n "naverBookFeedJob|naverShoppingFeedJob|naverRankingFeedJob|blocked until G1|JsonlComparator|TxtComparator" .planning/phases/04-feed-job-design-and-first-conversion-plan/04-NAVER.md
rg -n "googleShoppingFeedJob|groupId|StepExecutionContext|scheduleSlot|windowKey|MultiResourceTsvComparator" .planning/phases/04-feed-job-design-and-first-conversion-plan/04-GOOGLE.md
rg -n "kakaoDaumFeedJob|feedRetentionJob|selling\\.xml|ebook_selling\\.xml|event\\.xml|ebook_event\\.xml|eventbook\\.xml|ebook_eventbook\\.xml|XmlComparator" .planning/phases/04-feed-job-design-and-first-conversion-plan/04-KAKAO-DAUM.md
rg -n "kakaoDaumFeedJob|first vertical slice|G1|repo creation approval" .planning/phases/04-feed-job-design-and-first-conversion-plan/04-FIRST-SLICE.md
rg -n "FEED-01.*Specified|FEED-02.*Specified|FEED-03.*G1|FEED-04.*Specified|FEED-05.*Specified" .planning/REQUIREMENTS.md
```

</verification>

<success_criteria>
1. All feed design requirements FEED-01 through FEED-05 are covered.
2. `kakaoDaumFeedJob` is selected as first vertical slice.
3. Row 15 remains blocked instead of over-designed.
4. The phase remains local-only and does not imply implementation or equivalence.
</success_criteria>
