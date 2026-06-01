---
name: dev2-ad-commands-ko
description: "Use when the user invokes or refers to any development team 2 Claude Code ad command in Codex, including /ad:ticket, /ad:work-prep, /ad:code-review, /ad:weekly-report, /ad:weekly-planned, /ad:sprint-close-check, /ad:okr, /ad:team2-kb-read, /ad:team2-kb-list, /ad:team2-kb-sync, /ad:harness-optimize, /ad:data-request, /ad:service-activity, /ad:capacity-plan, or /ad:new-note."
---

# 개발 2팀 `/ad:*` 명령 호환

Codex에서는 Claude Code slash command를 직접 로드하지 않는다. 대신 이 스킬이 team2 하네스의 command 파일을 읽고 같은 절차를 수행한다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 사용자 요청에서 `/ad:{name}` 또는 `$ad-{name}`을 찾는다. 자연어 요청이면 아래 매핑으로 가장 가까운 command를 고른다.
3. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/{name}.md`를 먼저 읽고, 그 파일을 source of truth로 따른다.
4. command 파일이 Claude Code 도구명을 쓰면 Codex 도구로 대응한다: `Bash`는 `exec_command`, `Read/Grep/Glob`은 `sed`/`rg`/`find`, `Write/Edit`은 `apply_patch`, `AskUserQuestion`은 필요한 경우 짧은 직접 질문.
5. YouTrack은 REST API(`curl`)만 사용하고 MCP 도구는 사용하지 않는다.
6. 생성/변경/커밋/푸시/PR 같은 확인 게이트 작업은 초안만 제시하고 사용자 승인 후 실행한다.

## 명령 매핑

| 요청 | command 파일 |
|------|--------------|
| 티켓 생성, YouTrack 티켓, 5W1H | `ticket.md` |
| 작업 준비, 티켓번호/할일로 위키 노트 생성 | `work-prep.md` |
| GitHub PR 코드 리뷰 | `code-review.md` |
| 주간업무 보고 | `weekly-report.md` |
| 주간 계획 스냅샷 | `weekly-planned.md` |
| 스프린트 마감 자가점검 | `sprint-close-check.md` |
| OKR 조회/작성 | `okr.md` |
| YouTrack KB 조회/목록/동기화 | `team2-kb-read.md`, `team2-kb-list.md`, `team2-kb-sync.md` |
| 하네스 최적화, repo-vault 경계 점검 | `harness-optimize.md` |
| 운영 데이터 추출 요청 SQL 등록 | `data-request.md` |
| 서비스별 작업 활동 조회 | `service-activity.md` |
| 가용 용량 분석, capacity plan | `capacity-plan.md` |
| 신규 운영 위키 노트 작성 | `new-note.md` |

## Codex `$` alias

| alias | command 파일 |
|-------|--------------|
| `$ad-ticket` | `ticket.md` |
| `$ad-work-prep` | `work-prep.md` |
| `$ad-code-review` | `code-review.md` |
| `$ad-weekly-report` | `weekly-report.md` |
| `$ad-weekly-planned` | `weekly-planned.md` |
| `$ad-sprint-close-check` | `sprint-close-check.md` |
| `$ad-okr` | `okr.md` |
| `$ad-team2-kb-read` | `team2-kb-read.md` |
| `$ad-team2-kb-list` | `team2-kb-list.md` |
| `$ad-team2-kb-sync` | `team2-kb-sync.md` |
| `$ad-harness-optimize` | `harness-optimize.md` |
| `$ad-data-request` | `data-request.md` |
| `$ad-service-activity` | `service-activity.md` |
| `$ad-capacity-plan` | `capacity-plan.md` |
| `$ad-new-note` | `new-note.md` |

## 자격증명 패턴

토큰은 출력하지 않는다.

```bash
BASE="${YOUTRACK_BASE_URL:-https://aladincommunication.youtrack.cloud}"
if [ -z "${YOUTRACK_TOKEN:-}" ] && [ -r "$HOME/.claude/settings.json" ]; then
  YOUTRACK_TOKEN="$(jq -r '.env.YOUTRACK_TOKEN // empty' "$HOME/.claude/settings.json")"
fi
if [ -z "${YOUTRACK_TOKEN:-}" ]; then
  echo "YOUTRACK_TOKEN is missing" >&2
  exit 1
fi
AUTH="Authorization: Bearer $YOUTRACK_TOKEN"
```

## 금지 및 승인 게이트

- `mcp__youtrack__*` 또는 DB 관련 MCP 도구를 호출하지 않는다.
- YouTrack 티켓/Task 생성, 상태 변경, KB 생성/수정/삭제/이동은 사용자 승인 후에만 실행한다.
- git 커밋, 푸시, 머지, PR 생성/머지는 사용자 승인 후에만 실행한다.
- 운영 데이터 추출 SQL은 하네스 `docs/`가 아니라 `AladinCommunication/data-requests-dev2`에 둔다.
