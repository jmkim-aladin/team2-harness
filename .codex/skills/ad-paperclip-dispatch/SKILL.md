---
name: ad-paperclip-dispatch
description: "[상시·협업] Use when asked to put DEV2 tickets into the local Paperclip inbox or classify them into a Paperclip project for agent work. Also /ad:paperclip-dispatch."
---

# `$ad-paperclip-dispatch`

`/ad:paperclip-dispatch`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. `$TEAM2_HARNESS_PATH/.claude/commands/ad/paperclip-dispatch.md`를 먼저 읽고 그 절차를 따른다. 절차는 SoT 한 곳에만 둔다 — 여기 복제하면 한쪽이 낡는다.
3. 판정과 쓰기는 `tools/paperclip_import_ticket.py`가 한다. YouTrack은 읽기만 한다.
