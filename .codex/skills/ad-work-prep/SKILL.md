---
name: ad-work-prep
description: "Use when the user invokes $ad-work-prep, ad work prep, /ad:work-prep, asks to prepare DEV2 ticket work context, or asks to close/mark done/finish a DEV2 ticket wiki note after work is complete."
---

# `$ad-work-prep`

`/ad:work-prep` Codex alias. 실제 절차는 team2 하네스 command 파일이 source of truth다.

## 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/work-prep.md`를 먼저 읽고 그 절차를 따른다.
3. 참조 정책, 티켓, 로컬 위키 경로만 추가 확인한다.
4. YouTrack은 REST API/`curl`만 사용한다. MCP 금지.
5. 위키 노트 생성·갱신·종료 반영은 사용자 확인 없이 진행한다. YouTrack, git, DB/prod 변경은 승인 후 실행한다.
6. cmux/herdr 라벨 규칙은 유지한다: tab/agent는 티켓번호, pane은 티켓번호+제목.
7. 검증된 SQL은 위키 노트에 먼저 남기고, `data-requests-dev2` 등록은 별도 단계로 처리한다.
8. 티켓 종료/완료/마감/닫힘 요청 또는 완료 보고 시 로컬 위키에 `ticket_status: done`, 필요 시 `decision_status: resolved`, 종료 기록을 자동 반영한다.
