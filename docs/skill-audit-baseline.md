# 스킬 감사 베이스라인

기준: [policies/skill-authoring-principles.md](../policies/skill-authoring-principles.md) | 갱신: `/ad:harness-optimize 스킬` | 통계: `python3 tools/skill_usage_report.py`

최종 감사일: 2026-07-16 (최초 베이스라인)

## 사용 통계 (2026-05-31 ~ 07-16, Claude Code 로그)

> ⚠️ Codex(`.codex/skills/*`)·Hermes cron 경유 사용은 이 표에 안 잡힘. 0회 ≠ 미사용.

| 스킬 | 사용자 | 모델 | 계 | 마지막 | 판정 |
|------|-------|------|----|--------|------|
| code-review | 70 | 0 | 70 | 07-15 | 활성 |
| work-prep | 19 | 2 | 21 | 07-15 | 활성 |
| okr | 6 | 1 | 7 | 07-09 | 활성 |
| ticket | 5 | 2 | 7 | 07-15 | 활성 |
| data-request | 4 | 0 | 4 | 07-15 | 활성 |
| new-note | 0 | 2 | 2 | 07-14 | 활성 (모델 호출 전용) |
| sprint-close-check | 1 | 1 | 2 | 07-01 | 활성 (월말 주기성) |
| team2-kb-read | 0 | 2 | 2 | 07-09 | 활성 |
| weekly-report | 0 | 0 | 0 | - | 보류 — Codex 사용 추정, 확인 필요 |
| weekly-planned | 0 | 0 | 0 | - | 보류 — Codex 사용 추정, 확인 필요 |
| granola-sync | 0 | 0 | 0 | - | 유지 — Hermes cron 10분 주기 자동 실행 |
| architecture-analysis | 0 | 0 | 0 | - | 유지 — 신규 (2026-07 작업 중) |
| capacity-plan | 0 | 0 | 0 | - | 검토 — 월 주기 스킬, 다음 달 계획 시점 재확인 |
| harness-optimize | 0 | 0 | 0 | - | 유지 — 본 감사 루프의 실행 주체 |
| service-activity | 0 | 0 | 0 | - | 검토 — 사용 이력 없음 |
| work-board | 0 | 0 | 0 | - | 검토 — 사용 이력 없음 |
| team2-kb-list | 0 | 0 | 0 | - | 검토 — kb-read로 통합 후보 |
| team2-kb-sync | 0 | 0 | 0 | - | 검토 — harness-optimize 동기화와 중복 후보 |

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

### A. 즉시 수정 (무동작·리터럴 중복·자기불일치)

- [ ] `ticket.md:198-210` — "Task 본문: 수행 내용 섹션" 리터럴 2회 중복 → 1개 삭제
- [ ] `code-review.md:30-42` — `--dangerously-skip-permissions` 권장 문단 삭제 (게이트는 아래 문단에 이미 존재, 위험 권고만 잔존). 최다 사용 스킬(70회)이라 효과 큼
- [ ] `harness-optimize.md` SoT 표 — 팀원 정보 참조 파일에 weekly-report/capacity-plan/sprint-close-check/weekly-planned 추가
- [ ] `capacity-plan.md` — 저장 frontmatter 스키마 2곳 상충 → 1개로 병합
- [ ] `team2-kb-list.md:32-51` — KB 트리 스냅샷에 "예시 (API 재조회 권장)" 명시

### B. 중복 통합 (SoT 링크로 교체)

- [ ] frontmatter YAML 4중복 (ticket/weekly-report/sprint-close-check/new-note) → `wiki/guides/frontmatter-spec.md` 링크 한 줄
- [ ] 팀원 매핑표 5중복 (weekly-report/capacity-plan/sprint-close-check/weekly-planned/okr) → `policies/team-members.md` 참조 + 스킬별 파생 컬럼만 유지
- [ ] `weekly-planned.md:177-181` — 기간초과 경고 재기술 → weekly-report 정책 링크

### C. 대형 슬림화

- [ ] `weekly-report.md` §항목형식/예정일산정 ~130줄 → `docs/sprint/weekly-report-guide.md §4-5` 링크로 축약 (2649단어 → 절반 목표)
- [ ] `work-prep.md` §9·§11 → 독립 규율 문서로 분리 검토 (2층 구조 패턴)

### 트리거 재검토 (별도)

- [ ] CLAUDE.md routing 등록 13개 중 관측기간 모델 호출 0회 6개 (weekly-report, weekly-planned, service-activity, capacity-plan, granola-sync, architecture-analysis) — routing 줄 유지/제거 판단. 단 Codex·cron 사용 경로 확인 선행
