---
name: ad-ticket
description: "Use when the user invokes $ad-ticket, ad ticket, /ad:ticket, or asks to draft or create a DEV2 YouTrack ticket."
---

# `$ad-ticket`

`/ad:ticket`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/ticket.md`를 먼저 읽고 그 절차를 따른다. 절차는 SoT 한 곳에만 둔다 — 여기 복제하면 한쪽이 낡는다.
3. command 파일이 참조하는 정책과 카탈로그만 추가로 읽는다.
4. 티켓/Task 생성, 상태 변경, 필드 변경은 초안만 제시하고 사용자 승인 후 실행한다.
