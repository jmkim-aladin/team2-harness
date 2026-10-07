---
description: WBS·간트 추출 — YouTrack 루트 이슈 하위 트리를 엑셀·HTML 간트로. "간트 뽑아줘", "WBS 만들어줘", "프로젝트 진척 현황 엑셀로"
---

# WBS·간트 추출

루트 이슈 하나의 하위 트리 전체(프로젝트 경계 무관)를 `tools/export_wbs.py`로 WBS·간트 엑셀(.xlsx)과 HTML 간트로 뽑고, 진척·지연·구조 문제를 숫자로 보고한다. 계산·판정 규칙(계획=Sprints 근사, 실제=In Progress 이력·resolved, 취소 제외 진척률, rollup, 점검 항목)은 도구가 SoT다 — `python3 tools/export_wbs.py --help`와 [tools/README.md](../../../tools/README.md) §export_wbs.py.

## 사용법

```
/ad:wbs DEV2-5237            # 기본 위치에 xlsx + html
/ad:wbs DEV2-5237 주         # 엑셀 간트를 주 단위로 (기본은 일 단위)
/ad:wbs 스토어프론트          # 루트 ID부터 찾는다
```

## 절차

기본 순서다. 인자가 이미 정해 준 단계는 건너뛴다.

1. **루트 이슈 확정** — 인자에 이슈 ID가 있으면 그대로 쓴다. 서비스·프로젝트 이름만 있으면 YouTrack에서 Epic 후보를 조회해([youtrack/api-guide.md](../../../youtrack/api-guide.md) 공통 호출 패턴) 추천안과 함께 한 번 묻는다. 완료: 루트 ID 하나.
2. **출력 위치 확정** — 기본: vault `wiki/projects/{프로젝트}/wbs/`의 `wbs-{루트}.xlsx`·`gantt-{루트}.html`, 같은 이름으로 덮어쓴다(이전 판은 vault git 이력). 프로젝트 폴더는 vault(`$LOCAL_WIKI_PATH`)에서 루트 ID·서비스 슬러그로 찾고, 못 찾으면 추천 폴더와 함께 한 번 묻는다. 사용자가 경로를 주면 그 경로를 쓴다. 완료: repo 밖 절대 경로 두 개.
3. **실행** — 완료: 종료 코드 0, 두 파일 존재.
   ```bash
   python3 "${TEAM2_HARNESS_PATH:-$HOME/Documents/workspace/team2}/tools/export_wbs.py" {루트} \
     --out {xlsx} --html {html} --html-title "{2~4단어 이름}" [--gantt-unit week]
   ```
   실패하면 stderr 한 줄을 그대로 보고한다. 토큰이 없다는 오류면 `python3 tools/cred.py set youtrack-token`을 안내한다.
4. **보고** — 도구 stdout의 숫자를 그대로 옮긴다: 이슈 수·깊이 분포, 진척률(취소 제외), rollup 행 수, 0이 아닌 점검 항목, Depend·Relates 링크 수. 해석은 한두 줄(예: Depend 0건 = 선후관계가 YouTrack에 기록돼 있지 않음)과 두 파일 경로. 완료: 모든 숫자가 stdout에 있는 값.

## 경계

- YouTrack은 조회만 한다 — 도구가 GET만 호출한다. 점검에서 드러난 티켓 정리(Sprints 입력, 접두어 통일, 선행 링크 추가)는 별도 요청으로 받고, 티켓 변경은 사용자 확인 후 수행한다. 근거: 티켓 변경은 되돌릴 수 없는 외부 행동(CLAUDE.md 핵심 규칙).
- 산출물은 repo 밖에 둔다 — 업무 데이터라서다. 도구가 repo 안 경로를 거부한다.
- HTML을 claude.ai Artifact로 게시하는 것은 사용자가 요청할 때만 한다. 근거: 업무 데이터(담당자 이름·티켓 제목)의 게시 범위는 사람이 정한다.
