---
name: ad-code-review-self
description: "[개발·리뷰] Use when asked to self-review their own DEV2 GitHub PR with a separate reviewer agent until review completion. Also /ad:code-review-self."
---

# `$ad-code-review-self`

`/ad:code-review-self`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/code-review-self.md`를 먼저 읽고 그 절차를 따른다 — 절차는 SoT 한 곳에만 둔다. 여기 복제하면 한쪽이 낡는다.
3. 리뷰어 peer는 Codex 호스트에서도 Claude peer로 띄운다 — 판정 기준 SoT가 `/ad:code-review` command이고, peer 기동 규칙은 `$TEAM2_HARNESS_PATH/.claude/commands/ad/orchestration.md`를 따른다.
4. 리뷰 게시, 커밋·push, 답글은 command 파일의 모드(기본: 라운드마다 사용자 확인, `--auto`: 그 PR 하나만 위임) 범위 안에서만 실행한다. 머지·force push·티켓 상태 변경은 사용자 승인 후 실행한다.
