# 스킬 감사 베이스라인

기준: [policies/skill-authoring-principles.md](../policies/skill-authoring-principles.md) | 갱신: `/ad:harness-optimize 스킬` | 통계: `python3 tools/skill_usage_report.py`

최종 감사일: 2026-07-16 (최초 베이스라인)

## 사용 통계 (2026-05-31 ~ 07-16, Claude + Codex 로그 통합)

> Hermes cron 등 로그 밖 자동 실행은 안 잡힘. Codex 열은 `$ad-*` invocation 리터럴 기준.

| 스킬 | Claude 사용자/모델 | Codex | 계 | 마지막 | 판정 |
|------|------------------|-------|----|--------|------|
| work-prep | 19 / 2 | 111 | 132 | 07-15 | 활성 — **Codex 주력** |
| code-review | 70 / 0 | 19 | 89 | 07-15 | 활성 — Claude 주력 |
| weekly-report | 0 / 0 | 16 | 16 | 07-13 | 활성 — Codex 전용 |
| ticket | 5 / 2 | 6 | 13 | 07-15 | 활성 |
| data-request | 4 / 0 | 5 | 9 | 07-15 | 활성 |
| okr | 6 / 1 | 0 | 7 | 07-09 | 활성 |
| sprint-close-check | 1 / 1 | 4 | 6 | 07-01 | 활성 (월말 주기) |
| new-note | 0 / 2 | 0 | 2 | 07-14 | 활성 (모델 호출 전용) |
| team2-kb-read | 0 / 2 | 0 | 2 | 07-09 | 활성 |
| granola-sync | 0 / 0 | 2 | 2 | 06-08 | 유지 — Hermes cron 10분 주기 |
| architecture-analysis | 0 | 0 | 0 | - | 유지 — 신규 (2026-07 구축 중) |
| capacity-plan | 0 | 0 | 0 | - | 관찰 — 월 주기, 7월 말 계획 시점 재확인 |
| harness-optimize | 0 | 0 | 0 | - | 유지 — 본 감사 루프 실행 주체 |
| service-activity | 0 | 0 | 0 | - | 관찰 — 다음 감사까지 0이면 삭제/통합 제안 |
| work-board | 0 | 0 | 0 | - | 관찰 — 동상 |
| team2-kb-list | 0 | 0 | 0 | - | 관찰 — kb-read 통합 후보 |
| team2-kb-sync | 0 | 0 | 0 | - | 관찰 — harness-optimize 동기화와 중복 후보 |
| weekly-planned | 0 | 0 | 0 | - | 관찰 — weekly-report 초안 모드와 기능 겹침 검토 |

## 트리거 분배 (체크리스트 1단계)

| 분류 | 스킬 | 부하 |
|------|------|------|
| 이중 (slash + CLAUDE.md routing) 13개 | ticket, work-prep, weekly-report, weekly-planned, sprint-close-check, okr, team2-kb-read, harness-optimize, data-request, service-activity, capacity-plan, granola-sync, architecture-analysis | routing 줄 13개가 매 요청 컨텍스트 상주 |
| 사용자 호출 전용 5개 | code-review, new-note, work-board, team2-kb-list, team2-kb-sync | 인지 부하만 |

관찰: 최다 사용 스킬(code-review, 70회 전부 사용자 호출)은 routing 없이도 문제 없음. 반면 routing 등록 13개 중 6개는 관측 기간 모델 호출 0회 — routing 줄의 컨텍스트 비용 대비 효과 재검토 대상.

## 구조·유도·가지치기 감사 (체크리스트 2~4단계)

2026-07-16 전수 감사 (18개). 트리거 설계는 전 파일 `ARGUMENTS: $ARGUMENTS` 슬래시 커맨드형으로 일관.

| 스킬 | 단어수 | 구조 | 유도 | 가지치기 후보 |
|------|-------|------|------|--------------|
| weekly-report | 2649 | ✗ 가이드 §4-5를 본문에 재기술 | 약함 | 가이드 중복 ~130줄, frontmatter·팀원표 중복 |
| work-prep | 2422 | ○ 외부 링크 위임 양호 | 보통 | §9(cmux/herdr)·§11(검증 SQL) 독립 규율 분리 후보 |
| capacity-plan | 1740 | ✗ 산식·팀원표 인라인 | 보통 | 저장 frontmatter 스키마 2곳 상충 |
| ticket | 1680 | △ 규칙 다수 인라인 | 양호 | 동일 섹션 리터럴 2회, 사례 changelog 퇴적 |
| code-review | 1282 | ○ | 우수 | `--dangerously-skip-permissions` 권장 문단 (무동작+위험) |
| okr | 1243 | △ | 우수 (Baseline lock 등) | 팀원 이니셜표 별도 유지 |
| data-request | 1118 | ○ | 양호 | 낮음 |
| sprint-close-check | 975 | ○ (조건표는 매번 필요) | 우수 | frontmatter·팀원표 중복 |
| architecture-analysis | 907 | ◎ 모범 (guide/template 위임) | 우수 | 낮음 |
| weekly-planned | 876 | ✗ "동일 정책" 명시 후 재기술 | 보통 | weekly-report와 개념 중복 |
| new-note | 810 | ○ (결정 트리 적절) | 우수 | frontmatter 중복 |
| harness-optimize | 767 | ○ | 우수 | SoT 표 자체가 미최신 (팀원표 참조 누락) |
| service-activity | 561 | ○ | 보통 | 낮음 |
| granola-sync | 517 | ○ 스크립트 위임 | 양호 | 낮음 |
| work-board | 483 | ○ | 양호 | 낮음 |
| team2-kb-list | 212 | ✗ KB 트리 스냅샷 하드코딩 | - | 스냅샷 드리프트 (퇴적물) |
| team2-kb-sync | 191 | ○ | - | 낮음 |
| team2-kb-read | 190 | ○ | - | 낮음 |

## 개선 백로그

사용 빈도 × 감사 결과 교차 우선순위. 적용 시 삭제 테스트(해당 스킬 1회 실행 비교) 필수.

### A. 즉시 수정 (무동작·리터럴 중복·자기불일치) — 2026-07-16 적용 완료

- [x] `ticket.md` — "Task 본문: 수행 내용 섹션" 리터럴 2회 중복 → 1개 삭제
- [x] `code-review.md` — `--dangerously-skip-permissions` 권장 문단 삭제 (게이트는 아래 문단에 이미 존재, 위험 권고만 잔존). 최다 사용 스킬(70회)이라 효과 큼
- [x] `harness-optimize.md` SoT 표 — 팀원 정보 참조 파일에 weekly-report/capacity-plan/sprint-close-check/weekly-planned 추가
- [x] `capacity-plan.md` — 저장 frontmatter 스키마 2곳 상충 → 축약판(퇴적물) 제거, 상세판으로 단일화
- [x] `team2-kb-list.md` — KB 트리 스냅샷에 "예시 (API 재조회 권장)" 명시

### B. 중복 통합 (SoT 링크로 교체) — 2026-07-16 적용 완료

- [x] frontmatter YAML 4중복 (ticket/weekly-report/sprint-close-check/new-note) → `wiki/guides/frontmatter-spec.md` 링크 한 줄
- [x] 팀원 매핑표 5중복 → `policies/team-members.md` 참조로 교체. 스킬별 파생 정보만 잔존: weekly-report(기본 담당자), weekly-planned(기본 담당자 페어), capacity-plan(강인용 baseline 예외), okr(이니셜·파일명 접미사 표 유지)
- [x] `weekly-planned.md` — 기간초과 경고 재기술 → weekly-report §SoT 링크

### C. 대형 슬림화 — 2026-07-16 적용 완료

- [x] `weekly-report.md` — §항목 형식·예정일 산정·기록 필터 bullet·중복 제거 원칙을 가이드 §1/§4/§4.5 링크로 축약 (-92줄). 스킬 고유 규칙(판단 기준 표, Obsidian hard break, KB POST 게이트)만 잔존
- [x] `work-prep.md` §9 → [docs/cmux-herdr-labeling.md](./cmux-herdr-labeling.md) 분리 (2층 구조). §11은 이미 템플릿 링크로 슬림 — 분리 불요 판정

### D. mattpocock/skills 패턴 흡수 — 2026-07-16 완료 (설치 없이 패턴만, MIT)

- [x] `disable-model-invocation: true` 메커니즘 도입 — 사용자 전용 스킬 3개 적용 (code-review·work-board·team2-kb-sync), 설명이 모델 컨텍스트에서 제거됨
- [x] 질문 규율 (하나씩·추천안 동반·사실은 조회/결정만 질문) → ad:ticket, ad:work-prep 이식
- [x] 리뷰 2축 분리 (기준 축 vs 스펙 축, 병합·재순위 금지) → ad:code-review 이식
- [x] 작성 원칙 정책 보강: description 작성 규칙, 점검 가능한 완료 기준, 분리 비용 판단, 용어집 패턴, 2축 패턴
- 도입 안 함: 스킬 28개 직접 설치 (superpowers/gstack/ad:*와 3중 중복 + 컨텍스트 역행 — 판정 근거는 2026-07-16 평가)

### 트리거 재검토 — 2026-07-16 완료

- [x] Codex 로그 교차 확인 결과 routing **전부 유지** 결정
  - weekly-report(Codex 16회)·granola-sync(Codex+cron) — 사용 확인됨
  - weekly-planned·service-activity·capacity-plan·architecture-analysis — 전 경로 0회이나 routing 라인당 비용 미미(~15-20토큰), NL 트리거 실효 있음(work-prep·ticket·okr 모델 호출 실적). 스킬 자체는 "관찰" 판정으로 다음 감사에서 재평가
