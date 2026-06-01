---
name: ad-weekly-report
description: "Use when the user invokes $ad-weekly-report, ad weekly report, /ad:weekly-report, or asks for a DEV2 weekly work report."
---

# `$ad-weekly-report`

`/ad:weekly-report`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/weekly-report.md`를 먼저 읽고 그 절차를 따른다.
3. command 파일이 참조하는 스프린트, 주간업무, YouTrack, 로컬 위키 컨텍스트만 추가로 확인한다.
4. YouTrack은 REST API(`curl`)만 사용하고 MCP 도구는 사용하지 않는다.
5. 보고서 작성은 자동으로 할 수 있으나 YouTrack/KB/위키 변경은 사용자 승인 후 실행한다.
