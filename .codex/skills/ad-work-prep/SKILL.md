---
name: ad-work-prep
description: "Use when the user invokes $ad-work-prep, ad work prep, /ad:work-prep, asks to prepare DEV2 ticket work context, or asks to close/mark done/finish a DEV2 ticket wiki note after work is complete."
---

# `$ad-work-prep`

`/ad:work-prep`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/work-prep.md`를 먼저 읽고 그 절차를 따른다.
3. command 파일이 참조하는 정책, 티켓, 로컬 위키 경로만 추가로 확인한다.
4. YouTrack은 REST API(`curl`)만 사용하고 MCP 도구는 사용하지 않는다.
5. 위키 노트 생성·갱신·종료 반영은 command 파일 기준으로 사용자 확인 없이 진행한다. YouTrack 변경, git 작업, DB/prod 변경은 사용자 승인 후에만 실행한다.
6. command 파일 §9의 cmux/herdr 작업 라벨 변경 규칙은 Codex에서도 생략하지 않는다. herdr 안에서는 `HERDR_ENV`/`HERDR_PANE_ID` 감지 후 tab/agent는 티켓번호만, pane은 티켓번호와 제목으로 바꾼다.
7. 검증된 SQL은 command 파일 §11 기준으로 위키 노트에 먼저 남긴다. data-requests-dev2 등록은 위키에 정리된 완료 정보를 기반으로 별도 단계에서 진행한다.
8. 사용자가 티켓 종료/완료/마감/닫힘을 요청하거나 완료 사실을 보고하면 command 파일 §12 기준으로 로컬 위키에 `ticket_status: done`, `decision_status: resolved`, 종료 기록을 자동 반영한다.
