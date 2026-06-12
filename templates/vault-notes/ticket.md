---
type: ticket
title: {{ticket_id}} {{title}}
canonical_id: ticket:{{ticket_id_lower}}
status: canonical
updated_at: {{date}}
ticket_id: {{ticket_id}}
ticket_status: in-progress
assignee: {{user}}
service: "[[{{service_id}}]]"
sprint: {{sprint}}
type_yt: feature
related_services:
  - "[[{{service_id}}]]"
related_domains: []
related_tickets: []
related_okrs: []
related_meetings: []
related_projects: []
relation_status: confirmed
relation_sources:
  - manual
okr_kr: ""
---

<!-- llm-hint -->
DEV2 티켓 작업 노트. YouTrack이 공식 상태 SoT, vault는 진행·분석·결정 누적용.
status: auto-prep | in-progress | done | backlog (디렉터리와 일치).
첫 50줄 안에 문제, 현재 판단, 해결 방향, 다음 행동을 모두 남긴다. 운영 검증 전달용 SQL은 검증 SQL 섹션에 남기고, 전수검사/콜그래프 출력은 근거 위치만 링크한다.
<!-- /llm-hint -->

# {{ticket_id}} {{title}}

## 판단 요약

- 문제:
- 현재 판단:
- 해결 방향:
- 다음 행동:

## 요청 요약

- 보고자/담당자: / {{user}}
- 원 요청:
- 제약/주의:

## 비즈니스 로직

- 트리거:
- 정책/예외:
- 영향 범위:
- 결정 필요:

## 기술 근거

- YouTrack: https://aladincommunication.youtrack.cloud/issue/{{ticket_id}}
- 서비스: [[{{service_id}}]]
- 관련 도메인:
- 관련 KB:
- 진입점:
- 의존성:
- 근거 위치:

## 검증

- 확인함:
- 남음:

## 검증 SQL

- 목적:
- 실행 환경:
- 기대 결과:

```sql
-- 조회 전용 SQL
```

## 미확정 질문

-

## 진행 메모

- {{date}}: 노트 초안 생성.

## 도메인 지식 promote

작업 중 확정된 도메인 지식·결정·분석은 본문에 마커로 묶어 두면 `tools/promote_notes.py`가 별도 노트로 분리 + wikilink로 치환:

```
<!-- promote:analysis/{{service_id}}/{slug} title="분석 제목" -->
{본문 markdown}
<!-- /promote -->
```

지원 type: domain / analysis / decision / proposal / glossary.

## Actions

- [ ] 첫 단계
- [ ] 담당자 컨펌
- [ ] 검증 결과 또는 회귀 테스트 정리
- [ ] PR / 배포

## 완료 기록

-
