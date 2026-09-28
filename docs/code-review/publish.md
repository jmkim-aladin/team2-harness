# 리뷰 게시

[`/ad:code-review`](../../.claude/commands/ad/code-review.md) 7단계에서 사용자가 "이대로 게시"라고 답한 뒤에만 읽는다. 게시 본문은 미리보기에서 승인된 내용이고, 로컬 전용 항목·하네스 경로는 넣지 않는다(본문 §6).

본문은 셸 인자로 넣지 않고 파일로 넘긴다 — 백틱·`$`·따옴표가 셸에서 깨진다. heredoc은 `<<'EOF'`로 확장을 막고, 게시 후 임시 파일을 지운다.

## 인라인 코멘트 없을 때

```bash
cat > {스크래치}/review-{N}-body.md <<'EOF'
{전체 메시지}
EOF
gh pr review {N} --repo {owner}/{repo} {--approve|--request-changes|--comment} --body-file {스크래치}/review-{N}-body.md
```

## 인라인 코멘트 포함할 때

JSON 페이로드 파일로 한 번에 POST한다. `gh api -f 'comments[][...]'` 반복 브래킷 폼 인코딩은 쓰지 않는다 — 근거: 2026-05-27 `side` 미인식·배열 인덱스 오매핑으로 422 실패. 실패 사례 기반 하드 게이트이며 완화 대상이 아니다.

```bash
cat > {스크래치}/review-{N}.json <<'EOF'
{
  "commit_id": "{리뷰한 headRefOid}",
  "event": "COMMENT",
  "body": "{전체 메시지}",
  "comments": [
    {"path": "src/foo.ts", "line": 42, "side": "RIGHT", "body": "{코멘트 1}"}
  ]
}
EOF
gh api repos/{owner}/{repo}/pulls/{N}/reviews -X POST --input {스크래치}/review-{N}.json --jq '{id, state}'
rm {스크래치}/review-{N}.json
```

- `event`는 `APPROVE`/`REQUEST_CHANGES`/`COMMENT` — 함께 보내면 즉시 submit되어 별도 단계가 없다
- comment마다 `path`·`line`·`body`. `side`는 `RIGHT`(추가·수정 줄, 기본) / `LEFT`(삭제 줄). 멀티라인은 `start_line` 추가(`line`은 끝줄)
- `body`가 빈 코멘트는 빼낸다 — 서버가 422를 낸다
- 문자열 값은 JSON 이스케이프(`\"`·줄바꿈 `\n`)한다

## 앞선 라운드 스레드 답글

미해소 항목은 새 코멘트가 아니라 기존 스레드에 답한다(본문 1단계). 리뷰와 별도로 게시하며, 같은 승인 범위 안에서만 보낸다.

```bash
cat > {스크래치}/reply-{comment_id}.json <<'EOF'
{"body": "{답글}"}
EOF
gh api repos/{owner}/{repo}/pulls/{N}/comments/{comment_id}/replies -X POST --input {스크래치}/reply-{comment_id}.json --jq '{id}'
```

## 게시 직후 확인

```bash
gh api repos/{owner}/{repo}/pulls/{N}/reviews --jq '.[-1] | {id, state, user: .user.login}'
```

`state`가 `APPROVED`/`CHANGES_REQUESTED`/`COMMENTED`면 성공.
