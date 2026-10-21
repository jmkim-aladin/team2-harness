---
type: ticket
title: {{ticket_id}} {{title}}
canonical_id: ticket:{{ticket_id_lower}}
status: draft
updated_at: {{date}}
ticket_id: {{ticket_id}}
ticket_status: in-progress
decision_status: none
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
---

> SoT: [docs/sprint/work-prep-note-template.md](../../docs/sprint/work-prep-note-template.md) — frontmatter·본문 구조는 그쪽을 따른다. 이 파일은 new-note용 최소 스켈레톤.

<!-- llm-hint -->
DEV2 티켓 작업 노트. YouTrack이 공식 상태 SoT, vault는 진행·분석·결정 누적용.
status: auto-prep | in-progress | done | backlog (디렉터리와 일치).
첫 50줄 안에 문제, 현재 판단, 해결 방향, 다음 행동을 모두 남긴다. 운영 검증 전달용 SQL은 검증 SQL 섹션에 남기고, 전수검사/콜그래프 출력은 근거 위치만 링크한다.
개발 Task(보통 이상)는 구현 계획 슬라이스가 다음 행동이다. 작성 기준은 SoT §구현 계획 기준.
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

## 구현 계획

- 강도:
- 완료 조건:
  - AC1 → (확인: )
- 검증 명령:
- 경계: 그냥 진행 / 먼저 확인 / 손대지 않음
- 슬라이스:
  - [ ] S1 — seam: / 확인: AC1
- 구현 중 신호:

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

마커 문법과 지원 type은 [tools/README.md](../../tools/README.md) §promote_notes.py 참조.

## Actions

- [ ] 개발 밖 첫 단계 (개발 단계는 구현 계획 슬라이스)
- [ ] 담당자 컨펌
- [ ] 검증 결과 또는 회귀 테스트 정리
- [ ] PR / 배포

## 완료 기록

-
