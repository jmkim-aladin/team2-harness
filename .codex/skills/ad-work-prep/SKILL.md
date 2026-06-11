---
name: ad-work-prep
description: "Use when the user invokes $ad-work-prep, ad work prep, /ad:work-prep, or asks to prepare DEV2 ticket work context."
---

# `$ad-work-prep`

`/ad:work-prep`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/work-prep.md`를 먼저 읽고 그 절차를 따른다.
3. command 파일이 참조하는 정책, 티켓, 로컬 위키 경로만 추가로 확인한다.
4. YouTrack은 REST API(`curl`)만 사용하고 MCP 도구는 사용하지 않는다.
5. 위키 노트 생성, YouTrack 변경, git 작업은 사용자 승인 후 실행한다.
6. command 파일 §9의 cmux/herdr 작업 라벨 변경 규칙은 Codex에서도 생략하지 않는다. herdr 안에서는 `HERDR_ENV`/`HERDR_PANE_ID` 감지 후 tab/agent는 티켓번호만, pane은 티켓번호와 제목으로 바꾼다.
7. 검증된 SQL은 command 파일 §11 기준으로 위키 노트에 먼저 남긴다. data-requests-dev2 등록은 위키에 정리된 완료 정보를 기반으로 별도 단계에서 진행한다.
