---
type: decision
title: {{service_id}} {{title}}
canonical_id: decision:{{service_id}}/{{slug}}
status: canonical
updated_at: {{date}}
service_id: {{service_id}}
related_services:
  - "[[{{service_id}}]]"
decision_date: {{date}}
deciders:
  - {{user}}
status_label: accepted     # proposed | accepted | superseded | deprecated
supersedes: ""
superseded_by: ""
related_tickets: []
related_domains: []
related_okrs: []
relation_status: confirmed
relation_sources:
  - manual
---

<!-- llm-hint -->
서비스 ADR (Architecture Decision Record). 결정 시점·근거·영향 명시. 한 번 채택 후 변경 시 새 decision으로 supersedes.
<!-- /llm-hint -->

# {{title}}

## 배경 / 문제

- 

## 옵션 검토

### 옵션 A: 

- ✅ 장점:
- ❌ 단점:
- 비용: 

### 옵션 B: 

- ✅:
- ❌:

### 옵션 C: 

- 

## 결정

**선택: 옵션 ?** ({{date}})

근거:
- 

## 영향 / 결과

- 코드 영향: 
- 운영 영향: 
- 사용자 영향: 

## 위험·완화

- 

## 후속 조치

- [ ] 

## 관련

- 분석: [[analysis/]]
- 티켓: 
- 이전 결정: 
