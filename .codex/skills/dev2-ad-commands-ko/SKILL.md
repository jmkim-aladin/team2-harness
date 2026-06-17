---
name: dev2-ad-commands-ko
description: "Use when the user invokes or refers to DEV2 /ad:* commands in Codex, including ticket, work-prep, work-board, code-review, weekly, sprint, OKR, KB, harness, data, service activity, capacity, Granola, or new-note work."
---

# 개발 2팀 `/ad:*` 명령 호환

Codex는 team2 하네스 command 파일을 source of truth로 읽고 같은 절차를 수행한다.

## 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`.
2. `/ad:{name}`, `$ad-{name}`, 자연어 요청을 아래 매핑으로 고른다.
3. `$TEAM2_HARNESS_PATH/.claude/commands/ad/{name}.md` command 파일을 source of truth로 먼저 읽는다.
4. 도구명 대응: `Bash`→`exec_command`, `Read/Grep/Glob`→`sed`/`rg`/`find`, `Write/Edit`→`apply_patch`, `AskUserQuestion`→짧은 직접 질문.
5. YouTrack은 REST API/`curl`만 사용한다. MCP 금지.

## 매핑

- `ticket`: 티켓 생성/5W1H
- `work-prep`: 작업 준비, 위키 노트
- `work-board`: Hermes board projection
- `code-review`: GitHub PR 리뷰
- `weekly-report`, `weekly-planned`, `sprint-close-check`
- `okr`
- `team2-kb-read`, `team2-kb-list`, `team2-kb-sync`
- `harness-optimize`: repo-vault 경계/정리
- `data-request`, `service-activity`, `capacity-plan`
- `granola-sync`, `new-note`

`$ad-{name}` alias는 같은 `{name}.md`로 매핑한다.

## 자격증명·게이트

토큰은 출력하지 않는다. 필요 시 env를 우선하고 `~/.claude/settings.json`에서 보조로 읽는다.

```bash
BASE="${YOUTRACK_BASE_URL:-https://aladincommunication.youtrack.cloud}"
if [ -z "${YOUTRACK_TOKEN:-}" ] && [ -r "$HOME/.claude/settings.json" ]; then
  YOUTRACK_TOKEN="$(jq -r '.env.YOUTRACK_TOKEN // empty' "$HOME/.claude/settings.json")"
fi
AUTH="Authorization: Bearer $YOUTRACK_TOKEN"
```

- `mcp__youtrack__*` 또는 DB MCP 도구를 호출하지 않는다.
- 생성/변경/커밋/푸시/PR은 초안까지만 자동 수행하고 사용자 승인 후 실행한다.
- YouTrack 티켓/Task/상태, KB 생성/수정/삭제/이동, git commit/push/merge/PR은 승인 필수.
- 운영 데이터 추출 SQL은 `AladinCommunication/data-requests-dev2`에 둔다.
