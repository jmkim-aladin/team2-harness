---
name: ad-weekly-report
description: "Use when the user invokes $ad-weekly-report, ad weekly report, /ad:weekly-report, or asks for a DEV2 weekly work report."
---

# `$ad-weekly-report`

`/ad:weekly-report`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/weekly-report.md`를 먼저 읽고 그 절차를 따른다.
3. command 파일이 참조하는 스프린트, 주간업무, YouTrack, 로컬 위키 컨텍스트만 추가로 확인한다.
4. YouTrack은 REST API(`curl`)만 사용하고 MCP 도구는 사용하지 않는다.
5. 보고서 작성은 자동으로 할 수 있으나 YouTrack/KB/위키 변경은 사용자 승인 후 실행한다.

## 운영 기준

- 사용자가 "현재 KB가 최종"이라고 하면 YouTrack KB `DEV2-A-696` 본문을 기준본으로 읽고 비교만 한다. KB 업데이트는 별도 명시 승인 없이는 하지 않는다.
- 최종 주간보고 후보는 대상 월 스프린트와 맞는 티켓만 포함한다. 예: 2026년 6월 보고서는 `Sprints=2026.06` 또는 `2606-planned` 기준.
- `Backlog` 상태 티켓은 최종 주간보고 후보에서 제외한다.
- 개발자 담당 업무만 포함한다. 기획자/디자이너 Feature는 제외하되, 그 하위 Task가 개발자에게 할당되어 있으면 부모 Feature는 컨텍스트로만 쓰고 개발자 Task만 본문 라인으로 남긴다.
- 같은 월 안에서 주간 초안을 다시 만들 때는 기존 KB/직전 주차 본문 목록을 기준본으로 유지한다. 새 주차 변동분만 요약해 새 파일을 만들지 말고, 기존 항목을 상태 이동·본문 보강·신규 추가하는 방식으로 갱신한다. 월이 바뀔 때만 월별 목록을 새로 구성한다.
- 섹션 위치는 기존 본문 위치보다 현재 top-level 티켓 상태를 우선한다. Open/Reopened는 계획, In Progress는 진행중, Fixed/Closed/Verified는 완료, Backlog는 본문 제외로 재배치한다.
- 완료 항목은 대상 월 완료분을 유지한다. 같은 달에 완료된 Feature/Epic 또는 포함된 개발자 Task는 최근 7/14일 범위로 잘라내지 않는다.
- `DEV2-*` ID 중복은 같은 레벨에서만 제거한다. top-level끼리 또는 하위 본문 라인끼리 같은 ID가 반복되면 하나만 남기고, top-level과 하위 본문 라인의 반복은 계층 표현으로 허용한다.
