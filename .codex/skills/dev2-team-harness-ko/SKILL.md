---
name: dev2-team-harness-ko
description: "Use when a request needs DEV2/team2 harness context: policies, service catalog, KB, OKR, weekly reports, review rules, data requests, sprint/capacity/service activity, local wiki boundaries, or /ad:* parity."
---

# 개발 2팀 하네스

`$TEAM2_HARNESS_PATH`가 source of truth다. 기본값: `/Users/jm/Documents/workspace/team2`.

## 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`.
2. 요청과 직접 관련된 파일만 읽는다.
3. 정책이 있으면 그대로 적용하고, 없으면 가장 가까운 정책을 밝히고 확인한다.
4. `/ad:*` 요청은 `dev2-ad-commands-ko`도 적용한다.

## 참조

- 진입점: `CLAUDE.md`, `AGENTS.md`
- 정책: `policies/engineering-policy.md`, `branching-strategy.md`, `code-review-policy.md`, `release-policy.md`, `ai-usage-policy.md`, `security-policy.md`, `incident-policy.md`, `team-members.md`, `knowledge-base-policy.md`, `wiki-document-language-and-title-policy.md`, `business-stakeholder-communication-policy.md`, `data-request-policy.md`
- 서비스/스프린트/분석: `catalog/{service}.yaml`, `docs/sprint/*.md`, `docs/analysis-guides.md`

## 사업부 커뮤니케이션

- 사업부, 기획, 운영, CS 등 비개발 이해관계자에게 전달할 댓글/선택지/보고 초안은 `policies/business-stakeholder-communication-policy.md`를 먼저 적용한다.
- 특정 서비스에 국한하지 않고, 서비스별 내부 구현명을 그대로 설명하지 말고 업무 용어로 풀어쓴다. 예: `MaxProduct` → "이용권 상품 관리 구조", `AutoPayment` → "기존 정기결제 구조", `MaxPass` → "이용 권한/이용권 활성화".
- 내부명, 코드 경로, DB 근거는 사업부용 코멘트가 아니라 로컬 위키의 `내부 근거` 또는 개발 메모에 분리한다.

## 외부·승인

- YouTrack은 REST API/`curl`만 사용한다. 토큰은 env 또는 `~/.claude/settings.json`에서 읽되 출력하지 않는다.
- GitHub는 `gh`; DB MCP 금지; dev RDS `sqlcmd`는 read-only 조회만 허용한다.
- 승인 전 자동 실행 금지: YouTrack 티켓/Task/상태/필드, YouTrack KB, YouTrack/KB/git commit/push/merge/PR, DB/SP, 프로덕션 배포.
- team2 하네스 자체 변경은 DEV2 티켓 없이 가능하다. 서비스 제품 코드는 제외한다. 사용자 명시 지시가 있으면 `[TEAM2]` 커밋/푸시 가능.
- 로컬 Obsidian vault 티켓 노트 생성·갱신·종료 반영은 확인 없이 가능하다. 이는 YouTrack 상태 변경이 아니다.

## 저장 위치

- `$TEAM2_HARNESS_PATH`: 정책, 가이드, 서비스 카탈로그, 스킬, 템플릿, 스프린트 산출물.
- `$LOCAL_WIKI_PATH`: 도메인 분석, Querybook, daily/meetings/tickets 노트.
- 운영 데이터 추출 SQL: `AladinCommunication/data-requests-dev2`.
