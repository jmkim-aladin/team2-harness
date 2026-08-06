---
name: ad-work-close
description: "Use when the user invokes $ad-work-close, ad work close, /ad:work-close, or asks to close/finish a DEV2 YouTrack ticket itself — state to Fixed with completion comment and spent-time work items. Wiki note closure stays with ad-work-prep."
---

# `$ad-work-close`

`/ad:work-close` Codex alias. 실제 절차는 team2 하네스 command 파일이 source of truth다.

## 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/work-close.md`를 먼저 읽고 그 절차를 따른다.
3. YouTrack은 REST API/`curl`만 사용한다. MCP 금지.
4. 상태 전환·코멘트·work item 등록은 실행 계획 제시 후 사용자 승인 1회를 받고 실행한다.
5. 로컬 위키 노트 종료 반영은 `$ad-work-prep` 종료 플로우로 처리한다.
