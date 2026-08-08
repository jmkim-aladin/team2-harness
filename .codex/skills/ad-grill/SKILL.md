---
name: ad-grill
description: "Use when the user invokes $ad-grill, /ad:grill, or wants an alignment interview before building an idea, feature, or design."
---

# `$ad-grill`

`/ad:grill`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. `$TEAM2_HARNESS_PATH/.claude/commands/ad/grill.md`를 먼저 읽고 그 절차를 따른다.
3. 엔진은 `$TEAM2_HARNESS_PATH/vendor/mattpocock/grilling/SKILL.md`와 `vendor/mattpocock/domain-modeling/SKILL.md`를 읽어 그대로 적용한다.
4. 도메인 문서 배치는 `$TEAM2_HARNESS_PATH/docs/agents/domain.md`를 따른다.
