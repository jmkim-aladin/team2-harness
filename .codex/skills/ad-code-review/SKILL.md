---
name: ad-code-review
description: "Use when the user invokes $ad-code-review, ad code review, /ad:code-review, or asks for a DEV2 GitHub PR code review."
---

# `$ad-code-review`

`/ad:code-review`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/code-review.md`를 먼저 읽고 그 절차를 따른다.
3. **리뷰 범위는 diff hunk에 포함된 줄과 그 줄이 깨뜨리는 기존 동작으로 한정한다** (command 파일의 최우선 규칙). diff 밖 코드는 영향 판단 문맥으로만 읽고 지적하지 않는다 — 눈에 띈 것은 `PR 밖 관찰`로만 남기고 게시하지 않는다. diff에 없는 의도·후속 계획을 추정해 지적하지 않는다.
4. command 파일이 참조하는 리뷰 정책과 PR 컨텍스트만 추가로 확인한다.
5. GitHub 조회는 `gh` CLI를 우선 사용한다.
6. 판정(4단계) 전에 **이해 패스(3단계)**를 반드시 거친다. 섹션 규격은 `$TEAM2_HARNESS_PATH/.claude/commands/ad/explain.md`를 따르고, 퀴즈·정답표·HTML 렌더·md 파일 저장은 제외한다. 근거를 못 댄 변경 묶음이 남으면 판정으로 넘어가지 않는다.
7. 각 코드 코멘트에는 이 변경 맥락에서 깨지는 경로를 `왜:` 한 줄로 쓴다 (미리보기 판정용). 일반론만 남으면 지적이 아니라 질의 코멘트로 내린다.
8. 교차 모델 검증(5단계)은 **기본 실행**이다. Codex 호스트에서는 교차 모델이 Claude Code다 — 자기 자신을 검증하지 않는다:

```bash
(cd "{로컬 클론}" && claude -p "$(cat "$PROMPT_FILE")" \
  --model opus --allowedTools Read Grep Glob) < /dev/null
```

`--no-cross`로 껐어도 위험 신호(DB/SP·외부 연동·인증·결제·레거시 경계·테스트 없는 로직 변경·순삭제 100줄+)가 걸리면 실행한다. 실행 여부는 항상 결과에 한 줄 노출한다.
9. **게시 코멘트는 4블록 골격**을 따른다 — `**[중요|제안|질문] 결론**` / 재현 / 기전 / `수정 제안:`. 본문 8줄 이내, 실패 경로가 다르면 코멘트를 쪼갠다. 주어는 코드·경로로 쓰고(작성자를 주어로 쓰지 않는다), 확인된 사실은 단정하되 확인 못 한 것은 `[질문]`으로 돌린다. 축·신뢰도·심각도·교차 모델 표기는 미리보기 전용이며 게시 본문에 넣지 않는다.
10. `APPROVE`는 승인 조건 3개를 모두 만족할 때만 낸다 — 미확인 축 0개 / 강등된 질의 항목 0개 / 교차 모델 검증 완료. 하나라도 못 채우면 `COMMENT`다.
11. 리뷰 코멘트 등록, 승인, 머지, 상태 변경은 사용자 승인 후 실행한다.
