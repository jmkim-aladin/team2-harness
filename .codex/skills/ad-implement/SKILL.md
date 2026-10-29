---
name: ad-implement
description: "[개발·구현] Use when asked to implement one slice of a DEV2 ticket note's implementation plan with TDD and then stop (commit only after confirmation), or work described by a spec or ticket. Also /ad:implement."
---

# `$ad-implement`

`/ad:implement`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. `$TEAM2_HARNESS_PATH/.claude/commands/ad/implement.md`를 먼저 읽고 그 절차를 따른다 (vendored implement 절차 + 팀 오버라이드). 절차는 SoT 한 곳에만 둔다 — 여기 복제하면 한쪽이 낡는다.
3. 커밋·푸시는 사용자 승인 후 실행한다 (슬라이스 단위로 제안).
