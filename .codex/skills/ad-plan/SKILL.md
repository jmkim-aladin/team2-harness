---
name: ad-plan
description: "Use when the user invokes $ad-plan, /ad:plan, or wants to synthesize an idea or grill session into a vault plan note."
---

# `$ad-plan`

`/ad:plan`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. `$TEAM2_HARNESS_PATH/.claude/commands/ad/plan.md`를 먼저 읽고 그 절차를 따른다.
3. YouTrack·KB·git은 변경하지 않는다 — vault 계획 노트 산출만.
