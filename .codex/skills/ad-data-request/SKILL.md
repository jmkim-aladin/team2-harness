---
name: ad-data-request
description: "Use when the user invokes $ad-data-request, ad data request, /ad:data-request, or asks to prepare a DEV2 operational data extraction request."
---

# `$ad-data-request`

`/ad:data-request`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/data-request.md`를 먼저 읽고 그 절차를 따른다.
3. command 파일이 참조하는 데이터 추출 정책과 `AladinCommunication/data-requests-dev2` 기준만 추가로 확인한다.
4. DB 관련 MCP 도구는 사용하지 않는다. dev RDS `sqlcmd`는 read-only 조회만 허용한다.
5. SQL 등록, DB/SP 변경, PR/커밋/푸시는 사용자 승인 후 실행한다.
