---
name: ad-harness-optimize
description: "Use when the user invokes $ad-harness-optimize, ad harness optimize, /ad:harness-optimize, or asks to optimize DEV2 harness and vault boundaries."
---

# `$ad-harness-optimize`

`/ad:harness-optimize`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/harness-optimize.md`를 먼저 읽고 그 절차를 따른다.
3. command 파일이 참조하는 repo/vault 경계 정책과 문서 규칙만 추가로 확인한다.
4. 로컬 위키와 하네스 파일의 위치 기준을 유지한다.
5. 파일 생성, 이동, 삭제, KB 변경은 사용자 승인 후 실행한다.
