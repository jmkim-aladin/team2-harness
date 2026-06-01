---
name: ad-code-review
description: "Use when the user invokes $ad-code-review, ad code review, /ad:code-review, or asks for a DEV2 GitHub PR code review."
---

# `$ad-code-review`

`/ad:code-review`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/code-review.md`를 먼저 읽고 그 절차를 따른다.
3. command 파일이 참조하는 리뷰 정책과 PR 컨텍스트만 추가로 확인한다.
4. GitHub 조회는 `gh` CLI를 우선 사용한다.
5. 리뷰 코멘트 등록, 승인, 머지, 상태 변경은 사용자 승인 후 실행한다.
