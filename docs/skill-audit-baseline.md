# 스킬 감사 베이스라인

기준: [policies/skill-authoring-principles.md](../policies/skill-authoring-principles.md) | 갱신: `/ad:harness-optimize 스킬`·`제약`·`스택`
통계: `python3 tools/skill_usage_report.py` (팀 스킬) | `python3 tools/harness_context_audit.py` (컨텍스트·외부 스택·훅)

최종 감사일: 2026-08-08 (3회차 — 스택 모드 신설, 외부 스킬·훅 정리)

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
| team2-kb-list | — | — | — | — | **삭제 (2026-08-03)** — kb-read `목록` 모드로 통합 |
| team2-kb-sync | — | — | — | — | **삭제 (2026-08-03)** — harness-optimize Step 2로 매핑표 흡수 |
| tldr | 0 | 0 | 0 | - | 유지 — 신규, 사용자 호출 전용 |
| explain | 1 | 0 | 0 | 08-03 | 활성 |
| weekly-planned | 0 | 0 | 0 | - | 관찰 — weekly-report 초안 모드와 기능 겹침 검토 |

## 트리거 분배 (체크리스트 1단계)

| 분류 | 스킬 | 부하 |
|------|------|------|
| 이중 (slash + CLAUDE.md routing) 13개 | ticket, work-prep, weekly-report, weekly-planned, sprint-close-check, okr, team2-kb-read, harness-optimize, data-request, service-activity, capacity-plan, granola-sync, architecture-analysis | routing 줄 13개가 매 요청 컨텍스트 상주 |
| 사용자 호출 전용 4개 | code-review, new-note, work-board, tldr | 인지 부하만 |

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

## 2회차 감사 (2026-08-03)

### 적용 완료

- [x] **자기모순 제거** — `ticket.md`의 "13점 금지 → 8점 이하 분할"이 같은 파일의 "SP 상한 3" 규칙과 충돌. 폐기된 8점/13점 규칙을 velocity-guide·velocity-okr-sprint-policy·sprint-closing-process(2곳)에서도 SP 상한 3으로 갱신
- [x] **퇴적물 제거** — `docs/superpowers/` 14개 파일 7,014줄(2026-05-27 완료 plans/specs), `docs/sprint/2026-0X-*` 6개 1,017줄(회고·보고 산출물). 참조 0건 확인 후 삭제
- [x] **0회 스킬 정리** — `team2-kb-list`·`team2-kb-sync` 삭제 + Codex alias 동반 삭제. 기능은 kb-read `목록` 모드와 harness-optimize Step 2로 흡수
- [x] **중복 → SoT 링크** — 수용량 산정식 4중복(velocity-guide를 SoT로), 이월 코멘트 필수항목 3중복(plan-change-process), 설계·분석 SP표 2중복(story-point-guide §6), `ticket.md`의 ticket-guide 2-2/2-3/3-0/3-2/3-3 재기술
- [x] **vault 경로 규약 단일화** — `/Users/user/` placeholder·하드코딩 혼재 → `$LOCAL_WIKI_PATH`. 환경변수 이름 드리프트 `TEAM2_WORKSPACE_ROOT` → `TEAM2_WORKSPACE_PATH`
- [x] **vault taxonomy 반영** — 2026-05-27 이관(`wiki/contracts`·`inventory`·`domains`·`execution`·`indexes`·`tasks`·`templates`·`meetings`·`okr` 폐지) 미반영 참조 18곳 갱신
- [x] **문체 통일** — 하십시오체 → 한다체 전면 적용(37개 파일). 규칙은 [wiki-document-language-and-title-policy.md](../policies/wiki-document-language-and-title-policy.md) §문체. 외부 커뮤니케이션 문구는 예외로 보존
- [x] **CLAUDE.md 드리프트** — 없는 `docs/designs/` 참조 삭제, 스킬 목록 최신화(new-note·work-board 누락분 추가)

### 다음 감사 이관

- `.planning/` 249파일 12,124줄 — 활성 GSD 프로젝트(B2B SSIS 전환 53 phase). "무엇을 일하나" 성격이라 repo↔vault 경계상 vault 후보이나 GSD 도구가 repo 루트 고정 경로를 읽으므로 이동 불가. 프로젝트 종료 후 재판정
- `wiki/processes/activity/` — `service-activity` 스킬 출력 경로가 vault taxonomy에 없음. 첫 실행 시 생성되므로 동작은 하나 분류 근거 없음
- 0회 잔존: `architecture-analysis`·`weekly-planned`·`work-board`·`tldr`·`service-activity`·`capacity-plan`. 도구·cron 연동이 있어 유지, 3회차에서 재평가

## 3회차 감사 (2026-08-08) — 스택 모드 신설

기준·판정 전문: [docs/skill-stack-and-workflow-plan.md](./skill-stack-and-workflow-plan.md). 측정: `python3 tools/harness_context_audit.py`

### 실측

| 지표 | 값 | 판정 |
|---|---:|---|
| 상주 컨텍스트 | 8,858 → 6,011 tok | 상한 8,000 이내로 복귀 |
| 호출당 평균 컨텍스트 | 470,000 tok | **경고** — smart zone(약 150k)의 3배 |
| Bash 비중 / 그중 `cd` | 64.9% / 35.9% | **경고** — 파일을 Read 대신 Bash로 읽음 |
| 설치 스킬 | 79 → 21종 | 90일 실사용 12종 + 인프라·배포 9종 |
| 훅 | 22 → 13개 | GSD 훅 9개 제거 (Edit당 약 280ms) |

### 적용 완료

- [x] **GSD 비활성** — 스킬 18종 + 훅 9개. 90일 Claude 호출 0, Codex 3세션(전부 6월), `.planning/` 최종 수정 07-16. 훅이 모든 `Write`/`Edit`/`Read`/`Bash`를 검문하고 있었다. `~/.claude/skills-disabled/`로 이동(삭제 아님), `.planning/` 산출물 보존
- [x] **미사용 외부 스킬 58종 비활성** — gstack 미사용 48종 등. 유지 21종은 실사용 12 + 인프라·배포 9(`gstack`·`gstack-upgrade`·`setup-gbrain`·`sync-gbrain`·`ship`·`review`·`qa`·`investigate`·`computer-use`, **관찰** 판정)
- [x] **라우팅 이중화 제거** — CLAUDE.md·AGENTS.md `Skill routing` 절 제거, 라우팅은 각 스킬 `description` 한 곳으로 단일화. routing 블록(약 350 tok)을 걷고 트리거를 담은 짧은 description(약 135 tok)만 남겨 **자동 호출을 유지하면서 215 tok 절감**
  - 1차 판정은 "자동 호출 전면 폐지"였으나 재검토 결과 문제는 자동 호출이 아니라 **이중화**였다. routing 0회 6건은 트리거 문구가 약했던 것 — 판정 정정 (2026-08-08)
  - `/ad:*` 16종 모델 호출 유지, 사이드이펙트 4종(`code-review`·`work-board`·`tldr`·`explain`)만 사용자 호출. 2026-07 팀 판정 승계
  - 부작용 확인: 사용자 호출 전용은 다른 스킬도 못 부른다. `ad:*` 간 상호 호출 0건이라 영향 없음
- [x] **비활성 스킬 참조 정정** — `docs/gstack-usage-guide.md` 재작성(비활성 `/cso`·`/land-and-deploy`·`/qa-only`·`/retro`·`/careful`·`/freeze`·`/benchmark`·`/canary`·`/document-release`·`/design-*` 제거), `policies/gstack-override-policy.md` 적용 범위표 갱신. 보안 감사는 내장 `/security-review`로 대체 명시
- [x] **AGENTS.md 재구성** — 13.8KB → 5.0KB. H1 2개, `gstack 스킬`·`문서 규칙`·`Skill routing` 절 각 2회 중복, 없는 경로(`docs/designs/`·`docs/okr/`), 없는 스킬(`checkpoint`) 라우팅 제거. Codex 고유 내용만 남기고 나머지는 CLAUDE.md 링크
- [x] **컨텍스트 예산 정책 신설** — [harness-governance-policy.md](../policies/harness-governance-policy.md) §컨텍스트 예산 (상주 8,000 tok / 세션 평균 200,000 tok)
- [x] **사용자 호출 전용을 팀 표준으로 확정** — [skill-authoring-principles.md](../policies/skill-authoring-principles.md) §1 갱신. 2층 구조의 아래층을 모델 호출 스킬 → 참조 파일로 변경
- [x] **`스택` 모드 신설** — `/ad:harness-optimize 스택`. 월 1회 + 외부 스킬 설치 시·체감 저하 시 즉시
- [x] **측정 도구 신설** — `tools/harness_context_audit.py`

### 2회차 이관 항목 처리

- `.planning/` — GSD 비활성으로 도구 경로 제약 해소. 프로젝트 재개 시 GSD 재활성이 선행 조건. **다음 감사로 재이관**
- 0회 잔존 스킬(`architecture-analysis`·`weekly-planned`·`work-board`·`tldr`·`service-activity`·`capacity-plan`) — 자동 호출 폐지로 routing 비용은 소멸. 인지 부하만 남으므로 flow 지도 등재 여부로 판정. **4회차에서 재평가**

### 다음 감사 이관

- **세션 컨텍스트 470k** — 규율(단계 경계 `/clear`, Read 우선, 절대 경로)은 CLAUDE.md·AGENTS.md에 박았으나 정착은 미확인. 4회차에서 재측정해 200k 이내 진입 여부 판정. 미달이면 규율이 아니라 구조(SoT 통째 읽기) 문제로 재진단
- **SoT 로드 다이어트** — `ticket-guide.md`(35KB)를 절 단위 참조로. 반복 Read 실측에서 14회 재독 확인
- **지시 강도 재표현 완주** — 1차 15선 이후 미완. 호출량 순(`code-review` → `work-prep` → `ticket`)
- **superpowers** — description 465 tok + SessionStart 주입 762 tok은 유지 중. `~/.claude/CLAUDE.md` 오버라이드로 자동 호출만 무력화. 실사용 3종(`brainstorming`·`systematic-debugging`·`executing-plans`)이 계속 쓰이는지 4회차 확인

## 북극성 원칙별 거리 (회차마다 갱신)

기준: [policies/harness-north-star.md](../policies/harness-north-star.md). 측정 신호가 좁혀지는지 회차 간 추이로 본다.

| # | 원칙 | 측정 신호 | 3회차 (2026-08-08) |
|---|---|---|---|
| 1 | 검증 루프 > 지시 | 카탈로그 검증 루프 필드 보유율 | 미표준화 — 0/11 |
| 2 | 문제 단위 위임 | 근거 없는 순서·개수·도구 고정 발견 수 | 1차 15선 재표현 완료, 전수 미완 |
| 3 | smart zone | 호출당 평균 컨텍스트 / 상주 예산 | 470k (목표 200k) / 6,032 tok (상한 8,000) |
| 4 | 환경=진실 | 캐시·죽은 참조 발견 수 | AGENTS.md 죽은 경로 2건 정리, 전수 스캔 미실시 |
| 5 | 게이트 기계화 | INVARIANT 중 훅·권한 강제 비율 | 훅 2건 (DB MCP 차단, sqlcmd readonly) |
| 6 | 아티팩트 기억 | glossary 항목 / decisions 수 | 0건 / 7건 |

### 3회차 추가 (2026-08-08 후속) — 환경 선언화

- [x] **`harness.manifest.json` 신설** — `~/.claude`·`~/.codex` 관리 영역의 SoT. env·팀 링크·외부 스킬 존치·훅 allow·계획 스택(mattpocock)·제거 기록 선언 [북극성 4·5]
- [x] **`tools/setup_harness.py` 신설** — 선언으로 수렴하는 멱등 초기화 도구 (`--check`/`--reset`, 격리 방식, stdlib만). 새 머신 = clone → 실행 [북극성 4·5]
- [x] **Codex 쪽 다이어트** — `~/.codex/skills` 선언 밖 61종 격리 (GSD 18, gstack 미사용분, 깨진 ad-* 링크 2). Claude 쪽만 정리됐던 비대칭 해소
- [x] **개인/팀 메모리 분리** — 팀 규율을 repo `memory/claude-base.md`로 이관, `~/.claude/team2-base.md` 링크 + `@team2-base.md` import. 개인 CLAUDE.md에는 개인 것만 남음 [북극성 4]
- 이관: 팀 스킬 체계 재편(작은 불변 프리미티브로 쪼개고 결합) — manifest 위에서 진행. `scripts/setup.sh`·`setup.ps1` 제거는 Windows 실기 검증 후

### 3회차 추가 (2026-08-08 후속 2) — mattpocock 채택

- [x] **vendor 설치 15종** — `vendor/mattpocock/` (v1.2.3, `6acc160e`, MIT). npx 대신 repo 고정 — 새 머신 재현·PR 리뷰·버전 pin [북극성 1·2·6]
- [x] **제외 8종** — 팀 우위 또는 규칙 우회 위험. 표: [policies/overrides/mattpocock.md](../policies/overrides/mattpocock.md)
- [x] **superpowers 제거 확정** — grill-with-docs·diagnosing-bugs·implement+tdd 가 대체. 플러그인 off + Codex 사본 15종 격리 대상
- [x] **확장점 작성** — `docs/agents/issue-tracker.md`(YouTrack + wayfinding 매핑), `docs/agents/domain.md`(vault glossary·decisions — repo CONTEXT.md 생성 금지)
- [x] **포인터 편집 3건** — implement·domain-modeling·diagnosing-bugs. 등록부: overrides/mattpocock.md §diff
- 계획 변경: Phase 4-5(`/ad:grill`)·4-7(`/ad:implement`) 신설 → **grill-with-docs·implement 채택으로 대체**. Phase 4-4 용어집은 domain-modeling + domain.md 오버라이드가 담당
- 검증 이관: 실 티켓 1건으로 grill→ticket→work-prep→implement→ad:code-review 전 구간 주행 (다음 실작업에서)

### 3회차 추가 (2026-08-08 후속 3) — 스킬 체계 3층화

- [x] **3층 구조 정식화** — 동사(ad:*, 팀 언어) / 엔진(upstream·leading word, 개명 금지) / 자료(SoT). [skill-authoring-principles.md](../policies/skill-authoring-principles.md) §구조 [북극성 2·6]
- [x] **`/ad:grill`(모델 호출)·`/ad:implement`(사용자 호출) 신설** — vendored 엔진 위 얇은 wrapper. 플로우 전 단계가 `ad:*`로 통일. wrapper 생긴 vendored 3종(grill-with-docs·grill-me·implement)은 링크 제외
- [x] **작업 플로우 → 업무 상황 지도** — 개발 티켓 / 서비스 구상·설계 / 버그·장애 / 스프린트·팀 운영 / 지식·문서 / 데이터 / 협업·세션 / 하네스, 상황당 동사 하나
- **엔진 추출 백로그** (monolith 판정 실측): YouTrack API 블록 13스킬×43회 → 공용 참조 1곳 / 환경변수 표 10곳 / 팀원 참조 8곳. 4회차에서 착수 판정
