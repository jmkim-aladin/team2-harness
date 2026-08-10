---
name: ad-plan-run
description: "Use when the user invokes $ad-plan-run, /ad:plan-run, or asks to execute one internal milestone from a DEV2 vault plan without requiring a YouTrack ticket."
---

# `$ad-plan-run`

`/ad:plan-run`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. `$TEAM2_HARNESS_PATH/.claude/commands/ad/plan-run.md`를 먼저 읽고 그 절차를 따른다.
3. 한 번에 vault 계획의 internal milestone 하나만 구현·검증하고 plan status와 evidence를 갱신한다.
4. YouTrack·KB·commit·push·PR·merge·배포와 외부 시스템 변경은 command의 사용자 승인 게이트를 따른다.
