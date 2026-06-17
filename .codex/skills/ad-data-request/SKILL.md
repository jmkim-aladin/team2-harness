---
name: ad-data-request
description: "Use when the user invokes $ad-data-request, ad data request, /ad:data-request, asks to prepare a DEV2 operational data extraction request, or asks to register operational SQL such as a max subscription payment actual-usage check."
---

# `$ad-data-request`

`/ad:data-request`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/data-request.md`를 먼저 읽고 그 절차를 따른다.
3. command 파일이 참조하는 데이터 추출 정책과 `AladinCommunication/data-requests-dev2` 기준만 추가로 확인한다.
4. DB 관련 MCP 도구는 사용하지 않는다. dev RDS `sqlcmd`는 read-only 조회만 허용한다.
5. SQL 등록, DB/SP 변경, PR/커밋/푸시는 사용자 승인 후 실행한다.
6. data-requests-dev2 커밋명은 `[DEV2-####] {요청 제목 또는 핵심 산출물 요약}` 형식을 쓴다. 예: `[DEV2-6654] 합산 구매내역 통계 요청`. 기본값으로 `[DEV2-####] 요청 완료`처럼 범용 문구를 쓰지 않는다.
7. 만권당 구독 결제 실제 사용 여부 확인 SQL은 vault `wiki/services/max/analysis/subscription-usage-check-sql.md` 템플릿을 우선 참조한다.
