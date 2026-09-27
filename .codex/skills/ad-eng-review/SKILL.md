---
name: ad-eng-review
description: "Use when the user invokes $ad-eng-review, /ad:eng-review, or asks for an engineering review of a plan or design before implementation."
---

# `$ad-eng-review`

`/ad:eng-review`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. `$TEAM2_HARNESS_PATH/.claude/commands/ad/eng-review.md`를 먼저 읽고 그 절차를 따른다. 절차는 SoT 한 곳에만 둔다 — 여기 복제하면 한쪽이 낡는다.
3. 섹션 점검표는 Step 0 합의 후 `$TEAM2_HARNESS_PATH/docs/eng-review/review-sections.md`를 읽는다.
4. 사용자 질문은 `AskUserQuestion` 대신 짧은 직접 질문으로 한다 (`$TEAM2_HARNESS_PATH/AGENTS.md` §도구 대응).
