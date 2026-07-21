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
- 대상 월 스프린트의 Open/Reopened/In Progress Feature·Task 일정은 각 티켓의 자유 형식 코멘트에서 상태별 예정일을 의미 기반으로 추출한다. 미착수는 시작 예정일, 진행중은 완료 예정일을 사용하고 완료 티켓의 완료일은 덮어쓰지 않는다.
- 자체 코멘트 날짜를 우선한다. Feature 명시일만 날짜 없는 Task에 상속하고, Feature 명시일이 없으면 날짜가 있는 대상 Task 중 가장 빠른 명시일을 Feature에 표시한다. Task에서 롤업한 Feature 파생 날짜는 다른 Task로 재전파하지 않는다.
- 일정정보 우선순위: ① 코멘트 명시일 → ② 착수일 fallback → ③ 미기록. 코멘트에 유효한 날짜가 없으면 착수일(`State`가 `In Progress`로 전환된 시각, 없으면 `created`)을 시작 경계 `M/D~`로 표시한다. 착수일 조회는 `GET /api/issues/{id}/activities?categories=CustomFieldCategory&fields=timestamp,field(name),added(name)`에서 State→In Progress 최초 항목의 timestamp를 사용한다. 착수일은 완료 목표(`~M/D`)로 쓰지 않는다.
- 코멘트·착수일 어디서도 날짜를 찾지 못하면 일정정보를 `<font color="red">미기록</font>`으로 표시하며 임의 추정하지 않는다. 상세 해석·우선순위는 `docs/sprint/weekly-report-guide.md` §4.5를 따른다.
- 보고 포맷은 가이드 §4-B(2026-07 개편)를 따른다: `## 이번 주 요약`(건수·담당자 표·하이라이트) + 상태 섹션 내 서비스 그룹핑(그룹명 한글, 원문 제목 대괄호는 보존) + 라인 단순화(제목 1회 + `DEV2-xxxx` ID만) + 하위 Task 날짜는 (완료)만 표시.
- 최상위 Task(하위 Feature 없이 top-level로 오는 Type=Task)는 제목과 동일한 하위 라인 1개를 생성한다. 말머리는 상태별(Open→예정/In Progress→진행 중/완료→완료), 완료만 날짜를 남긴다. Feature(하위 없음)는 제목 라인 하나로 끝낸다.
- 완료 항목은 대상 월 완료분을 유지한다. 같은 달에 완료된 Feature/Epic 또는 포함된 개발자 Task는 최근 7/14일 범위로 잘라내지 않는다.
- `DEV2-*` ID 중복은 같은 레벨에서만 제거한다. top-level끼리 또는 하위 본문 라인끼리 같은 ID가 반복되면 하나만 남기고, top-level과 하위 본문 라인의 반복은 계층 표현으로 허용한다.
