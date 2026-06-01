---
name: dev2-team-harness-ko
description: "Use when a request needs development team 2 context from the team2 harness: policies, service catalog, KB, OKR, weekly reports, code review rules, data requests, sprint process, capacity planning, service activity, local wiki boundaries, or Claude Code ad command parity."
---

# 개발 2팀 하네스

항상 `$TEAM2_HARNESS_PATH`를 source of truth로 사용한다. 기본값은 `/Users/jm/Documents/workspace/team2`다.

## 시작 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 요청 주제와 직접 관련된 하네스 파일만 읽는다.
3. 정책에 정답이 있으면 그 기준으로 답하고, 정책이 없으면 가장 가까운 정책을 명시한 뒤 확인을 구한다.
4. `/ad:*` 요청이면 `dev2-ad-commands-ko` 절차를 함께 적용한다.

## 우선 참조 파일

| 영역 | 파일 |
|------|------|
| 진입점 | `CLAUDE.md`, `AGENTS.md` |
| 엔지니어링 | `policies/engineering-policy.md`, `policies/branching-strategy.md`, `policies/code-review-policy.md`, `policies/release-policy.md` |
| AI/보안/장애 | `policies/ai-usage-policy.md`, `policies/security-policy.md`, `policies/incident-policy.md` |
| 팀/KB | `policies/team-members.md`, `policies/knowledge-base-policy.md`, `policies/wiki-document-language-and-title-policy.md` |
| 데이터 추출 | `policies/data-request-policy.md` |
| 서비스 | `catalog/{service}.yaml` |
| 스프린트 | `docs/sprint/*.md` |
| 분석 | `docs/analysis-guides.md` |

## 외부 시스템 규칙

- YouTrack은 REST API와 `curl`만 사용한다. MCP 도구는 사용하지 않는다.
- `YOUTRACK_TOKEN`이 shell 환경에 없으면 `~/.claude/settings.json`의 `env.YOUTRACK_TOKEN`을 `jq`로 읽되 값을 출력하지 않는다.
- GitHub는 `gh` CLI를 사용한다.
- DB 관련 MCP 도구는 사용하지 않는다. dev RDS `sqlcmd`는 read-only 조회만 허용한다.

## 사용자 확인 게이트

아래 작업은 초안 또는 계획까지만 자동 수행하고, 실행 전 명시 승인을 받는다.

- YouTrack 티켓/Task 생성, 상태 전환, 담당자/필드 변경
- YouTrack KB 생성/수정/삭제/이동
- git 커밋, 푸시, 머지, PR 생성/머지
- DB/SP 변경 및 프로덕션 배포

## 저장 위치

| 산출물 | 위치 |
|--------|------|
| 정책/가이드/서비스 카탈로그/스킬 | `$TEAM2_HARNESS_PATH` |
| 도메인 분석, Querybook, daily/meetings/tickets 노트 | `$LOCAL_WIKI_PATH` 기본 `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2` |
| 운영 데이터 추출 SQL | `AladinCommunication/data-requests-dev2` |
| OKR | `docs/okr/` 또는 YouTrack KB 기준 |
| 스프린트/주간 운영 산출물 | `docs/sprint/` |
