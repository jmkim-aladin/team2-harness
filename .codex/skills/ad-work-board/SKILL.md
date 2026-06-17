---
name: ad-work-board
description: "Use when the user invokes $ad-work-board, ad work board, /ad:work-board, or asks to refresh the DEV2 Hermes work board / Discord dispatch request."
---

# `$ad-work-board`

`/ad:work-board` Codex alias. 실제 절차는 team2 하네스 command 파일이 source of truth다.

## 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/work-board.md`를 먼저 읽고 그 절차를 따른다.
3. Claude Code와 Codex 모두 `$TEAM2_HARNESS_PATH/tools/run_work_board.py`를 사용한다.
4. 기본은 dry-run이다. 사용자가 apply/갱신을 명시한 경우에만 `--apply`로 vault projection을 갱신한다.
5. Hermes runtime 계약: `run_hermes_dispatch_cycle.py`, `hermes_dispatch_consumer.py`, `export_hermes_discord_outbox.py`, `run_hermes_discord_adapter.py`, `import_hermes_discord_receipt.py`.
6. Discord API, webhook, bot token은 직접 사용하지 않는다. Hermes가 기존 Discord bot 통합을 담당한다.
7. YouTrack, KB, git, DB, 배포 변경은 수행하지 않는다.
