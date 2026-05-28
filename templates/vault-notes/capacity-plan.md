---
type: capacity-plan
title: {{year}}년 {{month}}월 capacity {{user}}
canonical_id: capacity:{{year}}-{{month}}-{{user}}
status: canonical
updated_at: {{date}}
year: {{year}}
month: {{month}}
assignees:
  - jmkim
  - heum2
  - pms0905
  - hyeryun
---

<!-- llm-hint>
월별 가용 맨데이·velocity 스냅샷. /ad:capacity-plan 결과 저장.
산식: 스프린트 평일 - 공휴일 - PTO × 계획업무 비율.
<!-- /llm-hint -->

# {{year}}년 {{month}}월 가용 용량 분석 ({{user}})

## 가용 맨데이

| 항목 | 수치 |
|------|------|
| 스프린트 평일 | 일 |
| 공휴일 | -일 |
| PTO/연차 | -일 |
| 계획업무 비율 | % |
| **최종 가용 맨데이** | **일** |

## 팀 수용량 (KB DEV2-A-1122 BD PLAN)

| 시나리오 | 전월 velocity | ×80% | ×가용률 | 수용량 |
|----------|---------------|------|---------|--------|
| 전체 (AASM 100%) | | | | SP |
| AASM 제거 (0%) | | | | SP |
| **AASM 30% (권장)** | | | | **SP** |

## 본인 계획 SP

| 태그 | 본인 SP | 비고 |
|------|---------|------|
| {{year_month}}-planned | | |

## 판정

```
가용 맨데이: 일
팀 수용량: SP
본인 환산 가용 SP: SP
정합: %
```

## 조정안

- KR 우선 / 균형 / 이월: 
