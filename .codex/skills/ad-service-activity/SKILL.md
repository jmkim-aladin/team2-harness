---
name: ad-service-activity
description: "Use when the user invokes $ad-service-activity, ad service activity, /ad:service-activity, or asks to inspect DEV2 service work activity."
---

# `$ad-service-activity`

`/ad:service-activity`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/service-activity.md`를 먼저 읽고 그 절차를 따른다.
3. command 파일이 참조하는 서비스 카탈로그, 스프린트, YouTrack 컨텍스트만 추가로 확인한다.
4. YouTrack은 REST API(`curl`)만 사용하고 MCP 도구는 사용하지 않는다.
5. 조회 결과를 중심으로 답하고 상태/필드 변경은 사용자 승인 후 실행한다.
