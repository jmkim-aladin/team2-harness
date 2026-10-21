---
name: dev2-ad-commands-ko
description: "Use when the user invokes or refers to DEV2 /ad:* commands in Codex, including plan, plan-run, ticket, work, review, architecture, weekly, sprint, OKR, KB, harness, data, capacity, Granola, or new-note work."
---

# 개발 2팀 `/ad:*` 명령 호환

Codex는 team2 하네스 command 파일을 source of truth로 읽고 같은 절차를 수행한다.

## 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`.
2. `/ad:{name}`·`$ad-{name}`은 같은 `{name}.md`로, 자연어 요청은 아래 §작업 플로우와 alias description으로 고른다.
3. `$TEAM2_HARNESS_PATH/.claude/commands/ad/{name}.md` command 파일을 source of truth로 먼저 읽는다.
4. 도구명 대응: `Bash`→`exec_command`, `Read/Grep/Glob`→`sed`/`rg`/`find`, `Write/Edit`→`apply_patch`, `AskUserQuestion`→짧은 직접 질문.
5. YouTrack은 REST API/`curl`만 사용한다. MCP 금지 — 토큰과 쓰기 권한을 `curl` 한 경로로 통제하기 위해.

## 작업 플로우

개별 `$ad-*` 라우팅은 alias description이 맡는다. 아래는 `memory/claude-base.md`에서 생성한 블록이다(`tools/lint_harness_rules.py --sync-generated`).

<!-- generated:workflow-summary source=memory/claude-base.md -->
4그룹 — 떠올릴 단서는 "지금 티켓 기준 어디냐". 그룹 허브를 먼저 부르면 나머지를 안내한다. 지도 SoT(상황별 동사·강도·단계별 도구 명칭): `docs/harness-guide.md` §작업 플로우.

| 그룹 | 기억 단서 | 허브 → 흐름 |
|---|---|---|
| 구상 (티켓 전) | 아직 티켓이 없다 | `/ad:plan` · `/ad:grill` — 과제 크기 판정: 세션 하나 `/ad:grill` / 다세션 `/ad:plan`→`/ad:plan-run` / 세션을 넘는 안개 `/wayfinder` |
| 개발 (티켓 하나) | 티켓 하나를 끝낸다 | `/ad:work-prep`(강도 판정 + 구현 계획, "다음 단계" 지목) — `/ad:ticket → /ad:work-prep → (/ad:eng-review) → /ad:implement → /ad:code-review(-self) → /ad:work-close`. 구현 중 `tdd`·`diagnosing-bugs` |
| 주기 (팀 운영) | 달력 | 주간 `/ad:ticket-schedule`·`/ad:weekly-report` / 월말 `/ad:sprint-close-check`·`/ad:capacity-plan` |
| 상시 (언제든) | 상황 | 지식 `/ad:new-note` / 이해 `/wait-what` / 협업 `/ad:orchestration`·`/handoff` / 운영 DB `/ad:data-request` / 하네스 `/ad:harness-optimize` |

강도: 가벼움(1시간·설정) 바로 수정 / 보통(반나절·버그) 구현 계획 → `tdd` / 무거움(Task 여럿·모호·경계 변경) 전체 플로우 + 설계 검증 / 위험(운영 데이터·결제·인증·개인정보·공유 DB 스키마·비가역 — 크기 무관) 무거움 + 반증 검토·페르소나 리뷰·롤백 트리거. `/ad:implement`는 슬라이스 하나를 red→green 후 노트 체크하고 멈춘다.
<!-- /generated:workflow-summary -->

## 자격증명·게이트

토큰은 출력하지 않는다. 필요 시 env를 우선하고 `~/.claude/settings.json`에서 보조로 읽는다.

```bash
BASE="${YOUTRACK_BASE_URL:-https://aladincommunication.youtrack.cloud}"
if [ -z "${YOUTRACK_TOKEN:-}" ] && [ -r "$HOME/.claude/settings.json" ]; then
  YOUTRACK_TOKEN="$(jq -r '.env.YOUTRACK_TOKEN // empty' "$HOME/.claude/settings.json")"
fi
AUTH="Authorization: Bearer $YOUTRACK_TOKEN"
```

- `mcp__youtrack__*` 또는 DB MCP 도구를 호출하지 않는다 — 위 권한 통제 이유.
- 생성/변경/커밋/푸시/PR은 초안까지만 자동 수행하고 사용자 승인 후 실행한다.
- YouTrack 티켓/Task/상태, KB 생성/수정/삭제/이동, git commit/push/merge/PR은 승인 필수.
- 운영 데이터 추출 SQL은 `AladinCommunication/data-requests-dev2`에 둔다.
