---
name: ad-weekly-planned
description: "Use when the user invokes $ad-weekly-planned, ad weekly planned, /ad:weekly-planned, or asks for a DEV2 weekly plan snapshot."
---

# `$ad-weekly-planned`

`/ad:weekly-planned`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/weekly-planned.md`를 먼저 읽고 그 절차를 따른다.
3. command 파일이 참조하는 스프린트, 주간 계획, 팀 정책만 추가로 확인한다.
4. YouTrack은 REST API(`curl`)만 사용하고 MCP 도구는 사용하지 않는다.
5. 계획 스냅샷 작성 외의 YouTrack/KB/위키 변경은 사용자 승인 후 실행한다.
