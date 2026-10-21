---
name: dev2-team-harness-ko
description: "Use when a request needs DEV2/team2 harness context: policies, service catalog, KB, OKR, weekly reports, review rules, data requests, sprint/capacity, local wiki boundaries, or /ad:* parity."
---

# 개발 2팀 하네스

`$TEAM2_HARNESS_PATH`가 source of truth다. 기본값: `/Users/jm/Documents/workspace/team2`.

## 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`.
2. 요청과 직접 관련된 파일만 읽는다.
3. 정책이 있으면 그대로 적용하고, 없으면 가장 가까운 정책을 밝히고 확인한다.
4. `/ad:*` 요청은 `dev2-ad-commands-ko`도 적용한다.

## 참조

- 진입점: `CLAUDE.md`, `AGENTS.md`. 작업 지도: `docs/harness-guide.md` §작업 플로우(요약: `dev2-ad-commands-ko`)
- 정책: `policies/` — 디렉토리가 SoT (`ls policies/`로 조회)
- 서비스/스프린트/분석: `catalog/{service}.yaml`, `docs/sprint/*.md`, `docs/analysis-guides.md`

## 용어

- "위키"는 `$LOCAL_WIKI_PATH`의 로컬 Obsidian vault만 뜻한다.
- YouTrack Articles는 "지식베이스(KB)" 또는 "기술자료"라고 부른다. `DEV2-A-*`, `REF-A-*`를 위키라고 부르지 않는다.
- "위키에 저장/올려줘" 요청은 로컬 위키 파일 작성으로 처리한다. 지식베이스 변경은 사용자가 KB·지식베이스·기술자료를 명시하고 승인한 경우에만 수행한다.

## 사업부 커뮤니케이션

- 비개발 이해관계자(사업부·기획·운영·CS)용 댓글·보고 초안은 `policies/business-stakeholder-communication-policy.md`를 먼저 적용한다. 내부 구현명 대신 업무 용어로 쓰고(예: `MaxProduct` → "이용권 상품 관리 구조"), 내부 근거는 로컬 위키에 분리한다.

## 외부·승인

- YouTrack은 REST API/`curl`만 사용한다 — 토큰·쓰기 권한 통제. 토큰은 출력하지 않는다.
- GitHub는 `gh`; DB는 MCP 대신 등록된 도구 경로. dev 조회·DML과 staging 읽기는 `policies/local-credentials-policy.md` 사전 동의 범위, 운영은 `policies/production-db-access-policy.md` 승인 후 읽기만 — 매 실행 전문·범위·60초 이내를 제시해 명시 승인받고 전역 동시 1개 — 환경별 위험을 분리한다.
- 승인 전 자동 실행 금지: YouTrack 티켓/Task/상태/필드, YouTrack KB, YouTrack/KB/git commit/push/merge/PR, 개발 사전 동의 범위 밖의 DB/SP, 프로덕션 배포. 이유: 외부 상태 변경은 사용자 승인 범위를 따른다.
- team2 하네스 자체 변경은 DEV2 티켓 없이 가능하다. 서비스 제품 코드는 제외한다. 사용자 명시 지시가 있으면 `[TEAM2]` 커밋/푸시 가능.
- 로컬 Obsidian vault 티켓 노트 생성·갱신·종료 반영은 확인 없이 가능하다. 이는 YouTrack 상태 변경이 아니다.

## 저장 위치

- `$TEAM2_HARNESS_PATH`: 정책, 가이드, 서비스 카탈로그, 스킬, 템플릿, 스프린트 산출물.
- `$LOCAL_WIKI_PATH`: 도메인 분석, Querybook, daily/meetings/tickets 노트.
- 운영 데이터 추출 SQL: `AladinCommunication/data-requests-dev2`.
