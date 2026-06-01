---
name: ad-team2-kb-list
description: "Use when the user invokes $ad-team2-kb-list, ad team2 kb list, /ad:team2-kb-list, or asks to list DEV2 YouTrack KB content."
---

# `$ad-team2-kb-list`

`/ad:team2-kb-list`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/team2-kb-list.md`를 먼저 읽고 그 절차를 따른다.
3. command 파일이 참조하는 KB 정책과 조회 범위만 추가로 확인한다.
4. YouTrack은 REST API(`curl`)만 사용하고 MCP 도구는 사용하지 않는다.
5. 조회 결과만 출력하고 KB 변경은 사용자 승인 후 실행한다.
