---
type: weekly-report
title: {{year}}-{{month}}-{{week_in_month}}W {{user}} 주간업무
canonical_id: weekly-report:{{year}}-{{month}}-{{week_in_month}}W-{{user}}
status: draft
updated_at: {{date}}
assignee: {{user}}
year: {{year}}
month: {{month}}
week_in_month: {{week_in_month}}
sprint: {{sprint}}
related_tickets: []
related_services: []
related_okrs: []
relation_status: inferred
relation_sources:
  - manual
---

<!-- llm-hint -->
주간업무 보고서 초안. 라인 포맷 SoT = 가이드 docs/sprint/weekly-report-guide.md §4-B (2026-07 개편).
요약 섹션 + 서비스 그룹핑 + 라인 단순화(제목 1회, DEV2-xxxx ID만) + 하위 Task 날짜는 (완료)만 표시.
KB 자동 반영 X — 사용자가 수동 sync.
<!-- /llm-hint -->

# {{year}}-{{month}}-{{week_in_month}}W {{user}} 주간업무

## 이번 주 요약

* 계획 N건 · 진행중 N건 · 완료 N건 ({{date}} 상태 동기화 기준)

| 담당자 | 계획 | 진행중 | 완료 |
|---|---|---|---|
| {{user}} | 0 | 0 | 0 |

* [서비스] 핵심 변동 하이라이트

## **백로그 항목**

## **계획 항목**

**{서비스}**

* **\[서비스\] {제목}** ({시작예정일}~, {담당자}, DEV2-xxxx)
  : (예정) {간략 설명} ({담당자}, DEV2-yyyy)

<!-- 최상위 Task(하위 Feature 없음)는 제목과 동일한 하위 라인 1개 생성 -->
* **\[서비스\] {Task 제목}** ({시작예정일}~, {담당자}, DEV2-xxxx)
  : (예정) {Task 제목} ({담당자}, DEV2-xxxx)

## **진행중 항목**

**{서비스}**

* **\[서비스\] {제목}** (~{완료목표일}, {담당자}, DEV2-xxxx)
  : (진행 중) {간략 설명} ({담당자}, DEV2-yyyy)
  : (완료) {간략 설명} ({완료일}, {담당자}, DEV2-yyyy)

## **완료된 항목**

**{서비스}**

* **\[서비스\] {제목}** ({완료일}, {담당자}, DEV2-xxxx)
  : (완료) {간략 설명} ({완료일}, {담당자}, DEV2-yyyy)

## **이슈사항**

- 

## **기타**

- 
