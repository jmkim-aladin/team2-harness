# Work Prep 노트 템플릿

`/ad:work-prep`이 vault 티켓/제안 노트를 만들거나 갱신할 때 사용하는 상세 템플릿이다. 실행 절차와 승인 게이트의 source는 `.claude/commands/ad/work-prep.md`이고, 이 문서는 frontmatter, 본문 밀도, 검증 SQL 기록 형식을 담당한다.

## 경로

| 모드 | 경로 |
|------|------|
| 티켓 | `$LOCAL_WIKI_PATH/wiki/processes/tickets/dev2-{NNNN}.md` |
| 서비스 추정 자유글 | `$LOCAL_WIKI_PATH/wiki/services/{서비스ID}/proposals/{kebab-slug}.md` |
| 서비스 미추정 자유글 | `$LOCAL_WIKI_PATH/wiki/processes/tickets/{kebab-slug}.md` |

## 티켓 Frontmatter

```yaml
---
type: ticket
title: DEV2-{NNNN} {YouTrack 제목}
canonical_id: ticket:dev2-{nnnn}
status: draft
updated_at: {YYYY-MM-DD}
ticket_id: DEV2-{NNNN}
ticket_status: in-progress
decision_status: none
assignee: {jmkim 등 id}
service: "[[{서비스ID}]]"
related_services:
  - "[[{서비스ID}]]"
related_tickets: []
related_domains: []
related_meetings: []
related_okrs: []
relation_status: inferred
relation_sources:
  - youtrack
  - harness
sprint: {YYYY-MM}
type_yt: feature
youtrack_state: {YouTrack 상태}
youtrack_synced_at: "{YYYY-MM-DD}"
sources:
  - youtrack: {BASE}/issue/DEV2-{NNNN}
  - harness: $TEAM2_HARNESS_PATH/catalog/{서비스}.yaml
  - repo: {서비스 repo 경로}
---
```

`status`는 문서 신뢰도, `ticket_status`는 작업 흐름, `decision_status`는 Hermes board 노출 조건이다. 사용자 결정/승인/검토가 필요하면 `decision_status: decision-needed | approval-needed | review-needed | blocked` 중 하나를 명시한다.

## 자유글 Frontmatter

서비스 추정 시 `proposal` type을 사용한다.

```yaml
---
type: proposal
title: {사람용 제목}
canonical_id: proposal:{서비스ID}/{kebab-slug}
status: draft
updated_at: {YYYY-MM-DD}
service_id: "[[{서비스ID}]]"
related_services:
  - "[[{서비스ID}]]"
related_tickets: []
related_domains: []
related_meetings: []
related_okrs: []
relation_status: inferred
relation_sources:
  - manual
decision_status: none
---
```

서비스 추정 불가 시 backlog ticket으로 둔다.

```yaml
---
type: ticket
title: {사람용 제목}
canonical_id: ticket:backlog/{kebab-slug}
status: draft
updated_at: {YYYY-MM-DD}
ticket_id: TBD
ticket_status: backlog
decision_status: none
assignee: jmkim
service: unknown
related_services: []
related_tickets: []
related_domains: []
related_meetings: []
related_okrs: []
relation_status: inferred
relation_sources:
  - manual
sprint: {YYYY-MM}
type_yt: task
---
```

## 본문 템플릿

````markdown
# {제목}

## 판단 요약

- 문제: {사용자/운영 관점 문제 한 문장}
- 현재 판단: {확정/유력 가설 한 문장}
- 해결 방향: {바꿀 정책/로직/운영 조치 한 문장}
- 다음 행동: {바로 실행할 첫 단계}

## 현재 상태

- 상태: in-progress
- 결정 상태: none
- 마지막 판단: {요약}
- 다음 행동: {사용자 개입 없이 가능한 다음 단계}
- 확인 필요: {없으면 "없음"}

## 요청 요약

- 보고자/담당자: {보고자} / {담당자}
- 원 요청: {요청을 1-2줄로 압축}
- 제약/주의: {외부 티켓 원문 보존, DB 승인, 운영 영향 등}

## 비즈니스 로직

- 트리거: {언제 문제가 발생하거나 기능이 동작하는지}
- 정책/예외: {허용/제한/제외/정산/노출 등 판단 기준}
- 영향 범위: {사용자, 운영, 데이터, 정산, 노출 등}
- 결정 필요: {오너/보고자 확인이 필요한 정책 판단}

## 기술 근거

- 서비스/repo: {서비스ID} / {repo 경로}
- 진입점: {화면/API/배치/모듈 1-3개}
- 의존성: {핵심 SP/API/Table/외부 호출 1-5개}
- 근거 위치: {전수검사/콜그래프 결과가 있으면 링크만}

## 검증

- 목적: {확인하려는 판단}
- 방법: {grep/콜그래프/dev DB 읽기/테스트}
- 결과: {카운트, 패턴, 통과/실패 요약}
- 판단: {이 결과로 확정/기각/보류한 내용}
- 근거 위치: {SQL/Querybook/전수검사 링크. 없으면 생략}

## 검증 SQL

- 목적: {운영/개발 서버에서 확인할 판단}
- 실행 환경: {DB/서버}
- 기대 결과: {사용자가 알려주면 되는 값}

```sql
-- 조회 전용 SQL
```

## 미확정 질문

-

## 결정 패킷

- 현재 없음

## Actions

- [ ] {첫 단계}
- [ ] 담당자/오너 컨펌
- [ ] 검증 결과 또는 회귀 테스트 정리
- [ ] PR / 배포 라인업

## 완료 기록

- {YYYY-MM-DD}: 위키 노트 초안 생성 (`ad:work-prep`).
````

본문은 완료 기록과 링크를 제외하고 120줄 이내를 기본 목표로 한다. 첫 50줄 안에 문제, 현재 판단, 해결 방향, 다음 행동이 보여야 한다.

## 검증 SQL 기준

1. SQL은 조회 전용이다. `INSERT/UPDATE/DELETE/DDL`은 별도 승인 없이는 작성하거나 실행하지 않는다.
2. dev/staging 검증은 작은 모수(`TOP 10`~`100`, 특정 1~3개 그룹, 1일~7일, 빈 임시 테이블 등)로 시작한다.
3. 운영 식별자(계정, CID, OID 등)는 SQL 파라미터로 명시할 수 있으나 row dump는 저장하지 않는다.
4. 검증된 SQL은 data-requests-dev2 등록 전에 먼저 티켓 노트 `검증 SQL` 또는 하위 근거 파일에 저장한다.
5. 결과 기록은 스키마, 카운트, 대표 패턴, 판단만 남긴다. 운영 실데이터, 개인정보, 결제 row, SP 원문, 시크릿은 저장하지 않는다.
6. 여러 목적의 SQL이 3개를 넘거나 길면 `wiki/processes/tickets/dev2-{NNNN}/...` 하위 근거 파일이나 Querybook/data-request 산출물로 분리한다.

dev DB 읽기 쿼리는 [local-credentials-policy.md](../../policies/local-credentials-policy.md)의 사전 동의 범위다. 운영(prod) 조회와 추출은 [data-request-policy.md](../../policies/data-request-policy.md) 절차로 전환한다.
