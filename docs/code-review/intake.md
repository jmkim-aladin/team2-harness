# PR 수집 — 리비전·diff·앞선 라운드·완화 신호·강도

[`/ad:code-review`](../../.claude/commands/ad/code-review.md) 1·2단계에서 Draft가 아니면 읽는다. 무엇을 언제 하는지는 본문이 SoT이고, 여기는 명령·검증 기준·사고 사례다. 대상 레포는 `--repo {owner}/{repo}`·`repos/{owner}/{repo}/...`로 명시한다(본문 §0).

## 준비

`gh --version`·`gh auth status` (없으면 `brew install gh`·`gh auth login`). YouTrack 티켓·KB 조회 인증은 [youtrack/api-guide.md](../../youtrack/api-guide.md). 읽기 명령은 `.claude/settings.local.json`의 `gh pr view` 계열 허용 목록으로 통과하고, 게시는 본문 7단계 게이트를 거친다.

## 조회 명령

```bash
gh pr diff {N} --repo {owner}/{repo} --name-only
rtk proxy gh pr diff {N} --repo {owner}/{repo} > {스크래치}/pr{N}.diff
# 앞선 리뷰 라운드: 인라인 코멘트 · 리뷰 본문 · 일반 코멘트
gh api repos/{owner}/{repo}/pulls/{N}/comments --jq '.[] | "--- \(.id) \(.user.login) \(.path):\(.line) reply_to=\(.in_reply_to_id)\n\(.body)\n"'
gh api repos/{owner}/{repo}/pulls/{N}/reviews --jq '.[] | "--- \(.user.login) \(.state)\n\(.body)\n"'
gh api repos/{owner}/{repo}/issues/{N}/comments --jq '.[] | "--- \(.user.login)\n\(.body)\n"'
```

## 리뷰 리비전 고정

조회한 `headRefOid`·`baseRefOid`를 이후 비교·원본 링크·교차 모델·게시 `commit_id`에 쓴다 — 브랜치 이름은 머지·푸시로 움직인다.

## diff 누락 검출

전체 diff는 `rtk proxy`로 파일에 받고 `Read`로 절 단위 소비한다. 받은 직후 `grep -c '^diff --git' {파일}`이 `--name-only` 파일 수와 같은지 센다. `gh api ... contents`로 원본을 받을 때도 `rtk proxy`를 붙인다.

근거: rtk 훅이 diff 본문을 버리고 `--name-only`는 온전히 통과해 빈 diff 위에서 조용히 리뷰가 진행된다 (2026-08-10 PR #27: 1688줄→518줄, `diff --git` 0건).

## 앞선 라운드 선독

diff보다 먼저 세 조회를 모두 읽는다 — 나 자신이 남긴 것도 세션이 다르면 컨텍스트에 없다.

- 작성자 답변이 달린 항목은 새 코멘트로 다시 올리지 않고 4단계 판정 입력으로 쓰며, 해소되지 않은 부분만 그 스레드의 답글로 남긴다
- 답변이 diff 밖 사실(레포 밖 파일·운영 DB·배포 계획)을 근거로 들면 본문 §검증 순서대로 확인해 근거 수준(정적 확인/실행 확인) 그대로 미리보기에 남긴다

근거: 2026-09-22 Tobe PR #205 — 1라운드에서 답변된 질문을 새 세션이 재게시해 삭제로 되돌렸다.

## 완화 신호 스캔

서비스 코드 PR이면 `python3 "$TEAM2_HARNESS_PATH/tools/gate_loosening_scan.py" --diff {스크래치}/pr{N}.diff` 출력을 미리보기 «완화 신호»에 붙인다 — 기준 강화는 조용히, 완화는 드러낸다. 잡는 범주·못 잡는 것은 [tools/README.md](../../tools/README.md) §gate_loosening_scan.py.

- 판정이 아니라 4단계 입력이다: 사유가 diff·PR 본문·티켓에 있으면 넘기고, 없으면 기준 축 발견 후보다
- exit 2(입력 오류 — 빈 diff·diff 형식 아님·git 실패)면 미리보기에 `완화 신호: 스캔 실패 — {stderr 요지}` 한 줄을 쓴다. 0건 줄과 섞지 않는다 — 안 본 것이 "완화 없음"으로 읽히면 diff 누락 사고가 다시 묻힌다
- DB 스크립트·SP PR(diff가 `.sql`뿐)은 생략하고 `완화 신호: 생략 — DB/SP PR` 한 줄 — 이 PR의 리뷰 범위가 비즈니스 로직 추적이다

근거: 2026-10-21 addyosmani/agent-skills 검토 — 임계값 하향·skip·suppress는 가장 싼 초록 경로라 hunk 단위 판정에서 묻힌다.

## 강도와 페르소나 투입

티켓 노트(`$LOCAL_WIKI_PATH/wiki/processes/tickets/dev2-{nnnn}.md`) `## 구현 계획`의 `강도:` 줄을 쓴다. 없으면 diff·티켓 단서(결제·인증·개인정보·DB 스키마·SP·운영 데이터·비가역)로 판정하고 근거를 미리보기에 한 줄 남긴다. 정의는 [harness-guide.md](../harness-guide.md) §강도, 명칭은 같은 문서 §단계별 도구 명칭.

- **위험**이면 [personas.md](./personas.md)를 읽고 페르소나 리뷰를 띄운다 — 강도가 정해진 직후 백그라운드로 띄워 4단계 판정과 겹친다
- 다른 강도는 본문 절차 그대로다 — 추가 관점은 위험 변경에만 투입해 평소 리뷰 비용을 늘리지 않는다

근거: 2026-10-21 [외부 스킬 팩 통합 판정](../skill-packs-adoption-review.md).
