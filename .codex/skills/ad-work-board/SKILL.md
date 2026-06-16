---
name: ad-work-board
description: "Use when the user invokes $ad-work-board, ad work board, /ad:work-board, or asks to refresh the DEV2 Hermes work board / Discord dispatch request."
---

# `$ad-work-board`

`/ad:work-board`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/work-board.md`를 먼저 읽고 그 절차를 따른다.
3. Claude Code와 Codex 모두 `$TEAM2_HARNESS_PATH/tools/run_work_board.py`를 사용한다.
4. 기본은 dry-run이다. 사용자가 명시적으로 apply/갱신을 요청한 경우에만 `--apply`로 vault projection 파일을 갱신한다.
5. Hermes runtime의 board 갱신/pending payload 계산/outbox export는 `$TEAM2_HARNESS_PATH/tools/run_hermes_dispatch_cycle.py` 계약을 따른다.
6. Hermes runtime의 단독 pending payload 계산/ack 갱신은 `$TEAM2_HARNESS_PATH/tools/hermes_dispatch_consumer.py` 계약을 따른다.
7. Hermes bot adapter용 파일 handoff는 `$TEAM2_HARNESS_PATH/tools/export_hermes_discord_outbox.py` 계약을 따른다.
8. Hermes bot adapter command 실행은 `$TEAM2_HARNESS_PATH/tools/run_hermes_discord_adapter.py` 계약을 따른다.
9. Hermes bot adapter 전송 결과는 `$TEAM2_HARNESS_PATH/tools/import_hermes_discord_receipt.py`로 ack에 반영한다.
10. Discord API, webhook, bot token은 직접 사용하지 않는다. Hermes가 기존 Discord bot 통합을 담당한다.
11. YouTrack, KB, git, DB, 배포 변경은 수행하지 않는다.
