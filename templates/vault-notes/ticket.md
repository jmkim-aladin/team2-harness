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
related_domains: []
related_tickets: []
okr_kr: ""
---

<!-- llm-hint -->
DEV2 티켓 작업 노트. YouTrack이 공식 상태 SoT, vault는 진행·분석·결정 누적용.
status: auto-prep | in-progress | done | backlog (디렉터리와 일치).
<!-- /llm-hint -->

# {{ticket_id}} {{title}}

## 한눈 요약 (TL;DR)

- 무엇을: 
- 왜: 
- 어디서: 

## 요청 요약

- 보고자: 
- 담당자: {{user}}
- 유형/상태/우선순위/스프린트: 
- 발생 사실: 
- 원 요청: 
- 추가 회신/맥락: 

## 연결 리소스

- YouTrack: https://aladincommunication.youtrack.cloud/issue/{{ticket_id}}
- 서비스: [[../../services/{{service_id}}/{{service_id}}-index|{{service_id}}]]
- 관련 도메인: 
- 관련 KB: 

## 가설 / 영향 분리

- 

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

## 검증

- 검증 SQL / 회귀 테스트 항목: 

## Actions

- [ ] 첫 단계
- [ ] 담당자 컨펌
- [ ] 검증 작성
- [ ] PR / 배포

## 완료 기록

- 
