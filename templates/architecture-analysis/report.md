---
type: analysis
title: {{service_title}} 전체 아키텍처 분석
canonical_id: analysis:{{service_id}}/{{note_stem}}
status: draft
updated_at: {{date}}
service_id: {{service_id}}
related_services:
  - "[[{{service_id}}]]"
related_domains: []
related_tickets: []
related_okrs: []
relation_status: inferred
relation_sources:
  - "source:{{repo_path}}@{{commit_sha}}"
review_state: needs-review
evidence_level: {{evidence_level}}
resources:
  - path: ./assets/{{note_stem}}/{{note_stem}}.html
    type: html
    role: rendered-view
    status: generated
    title: {{service_title}} 전체 아키텍처 분석 HTML Reader
---

<!-- llm-hint -->
{{service_title}} 저장소의 실행 구조, 설계 철학, Clean/Hexagonal/DDD 적합성, 운영 위험과 이어갈 원칙을 소스 근거로 정리한 시점성 분석.
<!-- /llm-hint -->

# {{service_title}} 전체 아키텍처 분석

## 결론

> {{one_sentence_model}}

{{executive_summary}}

## 분석 기준

| 항목 | 값 |
|---|---|
| 서비스 | {{service_id}} |
| 저장소 | `{{repo_path}}` |
| 브랜치 | `{{branch}}` |
| 커밋 | `{{commit_sha}}` |
| worktree | {{worktree_state}} |
| 분석일 | {{date}} |
| 분석 방식 | {{analysis_mode}} |

### 범위와 규모

{{scope_and_scale}}

### 실행한 검증

{{verification_summary}}

## 아키텍처 맵

```text
{{architecture_map}}
```

### Runtime과 모듈

{{runtime_and_modules}}

### 핵심 흐름과 상태

{{flows_and_state_machines}}

### 외부 시스템 경계

{{external_boundaries}}

## 설계 철학

### 코드에서 확인한 실제 철학

{{actual_philosophy}}

### 문서에 선언된 철학

{{declared_philosophy}}

### 유지할 장점

{{strengths}}

## Clean·Hexagonal·DDD 평가

| 관점 | 판정 | 근거 | 해석 |
|---|---|---|---|
{{architecture_assessment_rows}}

### 문서와 구현의 차이

{{documentation_drift}}

## 우선순위 발견

| 우선순위 | 발견 | 영향 | 근거 | 확신도 | 권장 방향 |
|---|---|---|---|---|---|
{{finding_rows}}

## 네이밍과 구조

### 오타와 불일치

{{naming_issues}}

### 역할 용어 기준

{{role_vocabulary}}

## 이어갈 원칙

### 유지할 원칙

{{continuation_rules}}

### 피할 패턴

{{patterns_to_avoid}}

### 현실적인 개선 순서

{{improvement_order}}

## 검증과 한계

### 검증 결과

{{verification_results}}

### 미검증 범위

{{limitations}}

### 근거 위치

{{evidence_paths}}
