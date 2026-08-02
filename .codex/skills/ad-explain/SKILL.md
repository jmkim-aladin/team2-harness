---
name: ad-explain
description: "Use when the user invokes $ad-explain, ad explain, /ad:explain, or asks for an explainer document of a code change, PR, branch, or of an analysis just completed."
---

# `$ad-explain`

`/ad:explain` Codex alias. 실제 절차는 team2 하네스 command 파일이 source of truth다.

## 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/explain.md`를 먼저 읽고 그 절차와 섹션 규격을 따른다.
3. 모드를 먼저 정한다 — git 참조·PR URL이면 `diff`, 아니면 `analysis`. 인자가 없으면 직전 세션 대상을 `analysis`로 잡고 한 줄로 확인받는다.
4. 독자를 한 명 지정한 뒤 배경을 2층으로 쓴다. 소스 순서가 아니라 이해 순서로 묶는다.
5. 퀴즈 5문항은 편향 체크 4항(보기 길이 차 20자 이내 / 정답 분산 / 3연속 금지 / "모두 맞다" 금지)을 통과해야 한다.
6. 섹션 제목은 규격 그대로 쓴다. HTML은 `python3 "$TEAM2_HARNESS_PATH/tools/render_explain_report.py" "$NOTE" "$HTML"`로 만든다 (오프라인은 `--no-mermaid`).
7. 리뷰 판정·finding은 넣지 않는다. YouTrack, KB, vault, git 커밋, 배포는 수행하지 않는다.
