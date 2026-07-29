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
- `Backlog` 상태 티켓은 최종 주간보고 후보에서 제외한다. 단 코멘트에 이월·범위 제외 결정만 있고 상태가 아직 `Open`이면 제외하지 않는다. 계획 항목에 유지하고 제목 끝에 ` - {대상} 이월 검토`(예: `- 8월 이월 검토`, `- 4분기 이월 검토`) 마커를 붙이고 일정정보를 `{N}월~`/`{N}분기~`로 바꾼다. 지나간 원래 시작예정일은 그대로 두지 않는다. 대상 목록·근거 코멘트 날짜·승인 대기 여부는 이슈사항에 모으고, 실제 `Backlog` 전환 후부터 본문에서 뺀다. 상세는 가이드 §4-B.5.
- 개발자 담당 업무만 포함한다. 기획자/디자이너 Feature는 제외하되, 그 하위 Task가 개발자에게 할당되어 있으면 부모 Feature는 컨텍스트로만 쓰고 개발자 Task만 본문 라인으로 남긴다.
- 같은 월 안에서 주간 초안을 다시 만들 때는 기존 KB/직전 주차 본문 목록을 기준본으로 유지한다. 새 주차 변동분만 요약해 새 파일을 만들지 말고, 기존 항목을 상태 이동·본문 보강·신규 추가하는 방식으로 갱신한다. 월이 바뀔 때만 월별 목록을 새로 구성한다.
- 섹션 위치는 기존 본문 위치보다 현재 top-level 티켓 상태를 우선한다. Open/Reopened는 계획, In Progress는 진행중, Fixed/Closed/Verified는 완료, Backlog는 본문 제외로 재배치한다.
- 대상 월 스프린트의 Open/Reopened/In Progress Feature·Task 일정은 각 티켓의 자유 형식 코멘트에서 상태별 예정일을 의미 기반으로 추출한다. 미착수는 시작 예정일, 진행중은 완료 예정일을 사용하고 완료 티켓의 완료일은 덮어쓰지 않는다.
- 자체 코멘트 날짜를 우선한다. Feature 명시일만 날짜 없는 Task에 상속하고, Feature 명시일이 없으면 날짜가 있는 대상 Task 중 가장 빠른 명시일을 Feature에 표시한다. Task에서 롤업한 Feature 파생 날짜는 다른 Task로 재전파하지 않는다.
- 일정정보 방향은 상태로 고정한다. 진행중 항목은 항상 `~M/D`(완료 경계), 계획(미착수) 항목은 항상 `M/D~`(시작 경계)다. 진행중 항목에 `M/D~`를 쓰는 것은 오류다. 근거가 부족해도 방향을 바꾸지 않는다.
- 미착수(`Open`/`Reopened`) 우선순위: ① 코멘트 시작예정일 → ② 착수일 fallback(`State`가 `In Progress`로 전환된 시각, 없으면 `created`) → ③ `<font color="red">미기록</font>`. `created`가 대상 월 밖이면 시작예정일 근거로 부적절하므로 미기록으로 둔다.
- 진행중(`In Progress`) 우선순위: ① 코멘트 완료·종료·마감 목표일 → ② 대상 월 스프린트 종료일(예: 2026-07 → `~7/31`)을 완료 목표로 쓰고 이슈사항에 "완료 목표 코멘트 미기재"로 남긴다. 착수일을 완료 목표로 대체하지 않는다.
- 예외: 제목이 `{서비스} N월 운영` 형태인 월 단위 운영 umbrella Feature는 그 달 전체가 작업 기간이므로 운영 시작일 `M/D~`를 유지한다.
- 착수일 조회는 `GET /api/issues/{id}/activities?categories=CustomFieldCategory&fields=timestamp,field(name),added(name)`에서 State→In Progress 최초 항목의 timestamp를 사용한다. 상세 해석·우선순위는 `docs/sprint/weekly-report-guide.md` §4.4~§4.5를 따른다.
- 저장 전 `진행중 항목` 섹션에 `M/D~` 패턴이 남았는지 점검한다. 운영 umbrella 외에 남아 있으면 방향 오류다.
- 보고 포맷은 가이드 §4-B(2026-07 개편)를 따른다: `## 이번 주 요약`(건수·담당자 표·하이라이트) + 상태 섹션 내 서비스 그룹핑(그룹명 한글, 원문 제목 대괄호는 보존) + 라인 단순화(제목 1회 + `DEV2-xxxx` ID만) + 하위 Task 날짜는 (완료)만 표시.
- `## 이번 주 요약` 바로 다음에 `## 이번 주 핵심목표`를 둔다. 출처는 KB `DEV2-A-1351`(주간업무 핵심 목표, parent는 `DEV2-A-1` Team이며 `DEV2-A-692` 하위가 아니다) 하위의 대상 주차 문서다. `childArticles`에서 주차 문서를 찾아 담당자·항목 순서·문구·티켓 ID를 **원문 그대로** 옮긴다. 상태·일정정보·`티켓 미발행`·출처 인용·제외 사유 각주 같은 **보강은 넣지 않는다**. 핵심목표 섹션과 상태 섹션의 ID 중복은 허용한다. 상세는 가이드 §4-B.1.1. 핵심목표 운영 원칙(2026-08-03 주차부터 담당자별 2개, 산출물 증명 필수, 미달성 시 원인·재발 방지 기록)은 `docs/sprint/weekly-goal-policy.md`를 따른다.
- 핵심목표 KB 주차 표기는 해당 월 1일 기준(7/27~31 = `2026.07.5W`)이고 vault 파일명 주차는 월 첫 월요일 기준(`2026-07-4W`)이라 서로 다를 수 있다. 파일명 규칙은 바꾸지 않고 인용 시 KB 원문 주차를 그대로 적는다.
- 신규 항목 탐색은 본문 ID 재조회로 끝내지 않고 `Sprints:{대상월}` · `tag:{YYMM}-planned` · `State:{In Progress}` · `resolved date:{대상월}` 질의 합집합에서 본문에 없는 dev Feature/Epic을 찾아 편입한다.
- YouTrack API 실측 주의: `Assignee.value`는 `name`(표시명)과 `login`이 함께 오므로 담당자 필터는 `login`으로 비교한다(`name` 비교 시 dev 필터가 전부 탈락). `activities`의 `field.name`은 로컬라이즈되어 `상태`로 오므로 착수일 판정은 `State`와 `상태` 둘 다 허용한다.
- 최상위 Task(하위 Feature 없이 top-level로 오는 Type=Task)는 제목과 동일한 하위 라인 1개를 생성한다. 말머리는 상태별(Open→예정/In Progress→진행 중/완료→완료), 완료만 날짜를 남긴다. Feature(하위 없음)는 제목 라인 하나로 끝낸다.
- 완료 항목은 대상 월 완료분을 유지한다. 같은 달에 완료된 Feature/Epic 또는 포함된 개발자 Task는 최근 7/14일 범위로 잘라내지 않는다.
- `DEV2-*` ID 중복은 같은 레벨에서만 제거한다. top-level끼리 또는 하위 본문 라인끼리 같은 ID가 반복되면 하나만 남기고, top-level과 하위 본문 라인의 반복은 계층 표현으로 허용한다.
