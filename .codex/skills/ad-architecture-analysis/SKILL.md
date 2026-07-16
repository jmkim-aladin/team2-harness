---
name: ad-architecture-analysis
description: "Use when the user invokes $ad-architecture-analysis, ad architecture analysis, /ad:architecture-analysis, or asks for a DEV2 repository-wide architecture, Clean Architecture, Hexagonal, DDD, naming, reliability, or documentation-drift analysis."
---

# `$ad-architecture-analysis`

`/ad:architecture-analysis`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/architecture-analysis.md`를 먼저 읽고 그대로 따른다.
3. command가 지정한 평가 가이드, 서비스 catalog, vault 정책만 추가로 읽는다.
4. 제품 저장소는 읽기 전용으로 다루고 결과는 DEV2 로컬 wiki에 Markdown과 HTML로 저장한다.
5. commit, push, PR, DB, 운영 API 호출은 수행하지 않는다.
