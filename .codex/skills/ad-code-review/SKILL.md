---
name: ad-code-review
description: "Use when the user invokes $ad-code-review, ad code review, /ad:code-review, or asks for a DEV2 GitHub PR code review."
---

# `$ad-code-review`

`/ad:code-review`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/code-review.md`를 먼저 읽고 그 절차·섹션 규격·판정 기준을 따른다. 절차는 SoT 한 곳에만 둔다 — 여기 복제하면 한쪽이 낡는다.
3. command 파일이 참조하는 리뷰 정책과 PR 컨텍스트만 추가로 확인한다. GitHub 조회는 `gh` CLI를 우선 사용한다.
4. 교차 모델 검증(command 파일 5단계)에서 Codex 호스트의 상대 모델은 Claude Code다 — 자기 자신을 검증하지 않는다:

```bash
(cd "{로컬 클론}" && claude -p "$(cat "$PROMPT_FILE")" \
  --model opus --allowedTools Read Grep Glob) < /dev/null
```

5. 리뷰 코멘트 등록, 승인, 머지, 상태 변경은 사용자 승인 후 실행한다.

## 최우선 규칙

SoT를 읽기 전에도 이 범위 규칙은 깨지 않는다. 아래는 command 파일에서 생성된 블록이다 — 직접 고치지 말고 SoT를 고친 뒤 `python3 tools/lint_harness_rules.py --sync-generated`.

<!-- generated:code-review-scope source=.claude/commands/ad/code-review.md -->
아래 규칙은 이 문서의 다른 모든 절차보다 우선한다. 범위를 넘긴 리뷰는 작성자 시간을 쓰게 만들고, PR과 무관한 논쟁으로 머지를 지연시킨다.

- 판정 대상은 **diff hunk에 실제로 포함된 줄**, 그리고 그 줄이 깨뜨리는 기존 동작이다
- diff 밖 파일·기존 코드의 결함은 **지적 대상이 아니다** — 문맥으로 읽었어도 마찬가지. 눈에 띄면 미리보기에 `PR 밖 관찰` 한 줄로만 남기고 게시 본문에는 넣지 않는다
- **확대해석 금지**: diff에 없는 의도·설계 계획·후속 작업을 추정해 지적하지 않는다. 스펙 축 근거는 티켓·설계 문서에 **명시된 것**뿐이다
- 추정이 남으면 지적이 아니라 3단계 `확인 못 한 것` 또는 질의 코멘트다
- "이렇게 했으면 더 좋았다"류 대안 제시는 diff가 실제로 깨는 것을 지목할 때만 코멘트가 된다
<!-- /generated:code-review-scope -->
