# 스킬 스택 정리 + 워크플로우 도입 계획

> 상태: Phase 4-0b·4-1·4-8 적용 (2026-08-08, 브랜치 `team2/skill-stack-cleanup`, 미커밋). 잔여: 4-0 규율 정착 관찰, 4-2·4-3·4-4·4-5·4-6·4-7.
> 적용 결과: 상주 컨텍스트 8,858 → 6,011 토큰 (−32%), GSD 훅 9개 제거(Edit당 ~280ms), 스킬 79 → 21종.
> 감사 회차 기록: [docs/skill-audit-baseline.md](./skill-audit-baseline.md) 3회차.
> 선행: [harness-instruction-refactor-plan.md](./harness-instruction-refactor-plan.md) Phase 1~3 (2026-08-06 적용). 본 문서는 그 Phase 4에 해당한다.
> 입력: mattpocock/skills 저장소 재분석(2026-08-08, v1.2.3 기준) + 스킬 스택·훅 실사용 실측.
> 확정 사항 (2026-08-08 사용자 판정): ① 모델 자동 호출 층 전면 제거 — 모든 스킬을 사용자 호출 전용으로 ② mattpocock main flow 채택 ③ grilling 질문은 frontier 라운드 일괄

## 1. 실측

### 세션 시작 상주 컨텍스트 (team2 디렉토리 기준)

| 항목 | chars | ~토큰 | 실사용 |
|---|---:|---:|---|
| `team2/AGENTS.md` | 10,144 | 2,536 | — |
| `team2/CLAUDE.md` | 9,397 | 2,349 | — |
| gstack 스킬 description 61종 | 5,573 | 1,393 | 8종 (13%) |
| superpowers description 28종 | 4,519 | 1,129 | 3종 (11%) |
| superpowers SessionStart 강제 주입 | 3,051 | 762 | — |
| GSD 스킬 description 18종 | 1,579 | 394 | **0종** |
| `~/.claude/` CLAUDE+RTK+triple-crown | 3,221 | 804 | — |
| **합계** | **37,603** | **9,367** | |

### 스킬 실사용 (Claude `~/.claude/projects` + Codex `~/.codex/sessions` 전수)

| 스택 | 설치 | 사용된 종 | 총 호출 | 최다 | 마지막 |
|---|---:|---:|---:|---|---|
| ad (team2) | 19 | 15 (79%) | 143 | code-review 81, work-prep 22 | 2026-08-07 |
| gstack | 61 | 8 (13%) | 40 | codex 14, plan-eng-review 11 | 2026-08-06 |
| superpowers | 28 | 3 (11%) | 13 | brainstorming 7, systematic-debugging 5 | 2026-08-07 |
| GSD | 18 | 0 | 0 | — | Codex `$gsd-*` 3세션(전부 6월), `.planning/` 최종 수정 07-16 |

### GSD 훅 — 모든 툴 호출마다 발화 (스킬 사용 0인데 상시 동작)

| 이벤트 | 매처 | 훅 | 실측 |
|---|---|---|---:|
| PreToolUse | `Write\|Edit` | `gsd-prompt-guard.js` | 70ms |
| PreToolUse | `Write\|Edit` | `gsd-read-guard.js` | 60ms |
| PreToolUse | `Write\|Edit` | `gsd-workflow-guard.js` | 70ms |
| PreToolUse | `Bash` | `gsd-validate-commit.sh` | — |
| PostToolUse | `Bash\|Edit\|Write\|MultiEdit\|Agent\|Task` | `gsd-context-monitor.js` | 70ms |
| PostToolUse | `Read` | `gsd-read-injection-scanner.js` | 60ms |
| PostToolUse | `Write\|Edit` | `gsd-phase-boundary.sh` | — |
| SessionStart | (all) | `gsd-check-update.js`, `gsd-session-state.sh` | — |

**Edit 1회당 node 프로세스 5개 스폰 ≈ 280ms.** 툴 호출 100회 세션에서 GSD 훅만으로 10~20초. 휴면 프로젝트용 가드가 모든 편집을 검문한다.

### 스킬 1회 실행 시 추가 로드

`ad:work-prep`이 SoT로 읽는 문서 7종 = **73,654자 ≈ 18,400토큰**. 그중 `docs/sprint/ticket-guide.md` 단독 35,477자.

### 시간·행동·토큰 3축 실측 (최근 30일, Claude 세션 307개)

**토큰 축**

| 항목 | 값 |
|---|---:|
| 입력계 | 8,613M |
| ├ 캐시 읽기 | 8,359M (97.1%) |
| ├ 캐시 쓰기 | 253M |
| └ 실과금 input | 648k |
| 출력 | 46.7M |
| 출력/입력 비 | **0.54%** |

툴 호출 17,832회 ÷ 캐시 읽기 8,359M → **호출 1회당 평균 컨텍스트 약 470k 토큰**. 원문이 말하는 smart zone은 약 150k이므로 **평균이 그 3배**로 돌고 있다. 컨텍스트를 채우는 주체는 툴 결과다 — Read 18.9MB + Bash 15.1MB = 35.2MB chars ≈ **8.8M 토큰**.

**시간 축** (AskUserQuestion 219,100초는 사람 응답 대기이므로 제외)

| 툴 | 호출 | 중앙값 | 평균 | 총합 |
|---|---:|---:|---:|---:|
| Bash | 11,578 | 0.30s | 5.76s | **18.5시간** |
| Agent | 68 | 0.14s | 171s | 3.2시간 |
| Edit | 2,531 | 0.20s | 0.22s | 9.3분 |
| Read | 2,345 | 0.12s | 0.16s | 6.4분 |

Edit 자체는 약 0ms이므로 **평균 0.22s는 사실상 전부 훅 오버헤드**다 (PreToolUse GSD 3종 + PostToolUse 2종). 별도 측정한 280ms/edit와 정합한다.

**행동 축**

- Bash 64.9% vs Read 13.2% — 파일을 Read 대신 Bash로 읽는다 (`grep` 742, `cat` 246, `sed` 205). Bash 결과는 필터링도 캐시 친화도도 낮다
- **`cd` 4,152회 = Bash 호출의 36%** — 셸 cwd가 호출마다 초기화되므로 매번 재진입한다. 순수 낭비
- Bash 오류 381건 (3.3%)
- 같은 파일 반복 Read: storefront 설계문서 24회, `ticket-guide.md` 14회, `code-review.md` 14회 — 스킬이 SoT를 매 실행 통째로 재독한다
- 모델 분포: opus-5 20,124 / fable-5 11,669 / opus-4-8 2,044 / sonnet-5 1,830 / haiku-4.5 818

### 설치 스킬 전수 실사용 (90일, 슬래시 + Skill 툴)

| 사용 | 스킬 | 마지막 |
|---:|---|---|
| 31 | `orchestration` | 2026-08-06 |
| 14 | `codex` | 2026-08-06 |
| 11 | `plan-eng-review` | 2026-08-04 |
| 8 | `dev2-team-harness-ko` | 2026-08-06 |
| 4 | `plan-ceo-review` | 2026-08-04 |
| 3 | `document-generate` / `context-restore` | 2026-07-20 / 07-29 |
| 2 | `youtrack-ticket-5w1h-ko` / `dev2-ad-commands-ko` / `context-save` / `browse` | 2026-07-31 이하 |
| 1 | `_gstack-command` | 2026-07-23 |

**미사용 67종** — GSD 18종 전부, ios-* 5종, design-* 4종, `qa`·`ship`·`review`·`investigate`·`health`·`retro`·`office-hours`·`spec`·`learn` 등.

## 2. 진단

### 문제 0 — 세션이 smart zone 밖에서 돈다 (놓침의 1순위)

툴 호출 1회당 평균 컨텍스트 약 470k 토큰. 모델이 날카롭게 추론하는 대역(약 150k)의 3배다. 고사고 모델을 쓰는데 놓치는 1순위 원인이며, **상주 지시 9.4k 토큰은 470k의 2%에 불과**하므로 스킬 다이어트만으로는 해결되지 않는다.

컨텍스트를 채우는 실제 주체:

1. **툴 결과 누적** — 30일간 Read 18.9MB + Bash 15.1MB ≈ 8.8M 토큰
2. **Bash 편중** — 호출의 64.9%가 Bash. 파일 읽기를 `cat`/`sed`/`grep`으로 하면 Read보다 결과가 크고 거칠다
3. **`cd` 4,152회** — Bash 호출의 36%. 셸 cwd가 호출마다 초기화되는데 절대 경로 대신 `cd`로 재진입한다
4. **SoT 재독** — 스킬이 매 실행 `ticket-guide.md`(35KB) 같은 문서를 통째로 읽는다
5. **단계 경계에서 비우지 않음** — 그릴링·구현·QA가 한 창에 계속 쌓인다

### 문제 A — 지시 강도 평탄화 (놓침의 2순위)

선행 계획 §1 감사 결과가 그대로 유효하다: 지시문 1,435개 중 실제 INVARIANT는 11%인데 89%가 같은 강도로 표기됨. Phase 1~3에서 판정 정책(`instruction-precedence-policy.md`)은 도입했으나 **재표현은 15선 1차만 완료** — 나머지 지시문은 여전히 평평하다. 진짜 게이트가 절차 권장에 묻힌다.

### 문제 B — 상주 지시의 드리프트·중복

- `AGENTS.md` ↔ `CLAUDE.md` 공통줄 29%. AGENTS.md는 존재하지 않는 경로(`docs/designs/`, `docs/okr/`)를 참조하고, 스킬 목록에 `work-close`·`orchestration`이 누락된 구버전이다. 4,885토큰이 상주하며 일부가 사실과 다르다
- CLAUDE.md `Skill routing` 13줄 중 6개는 관측 기간 모델 호출 0회
- superpowers SessionStart 주입("1% 확률이면 반드시 스킬 호출", "clarifying question 전에도 스킬 먼저")과 CLAUDE.md `Skill routing: ALWAYS invoke as FIRST action`이 같은 지시를 2중으로 건다

### 문제 C — 휴면 스택의 상시 비용

- GSD: description 394토큰 + **훅 9개 상시 발화**. 스킬 사용 0
- gstack: 미사용 53종이 1,150토큰 점유
- superpowers: 미사용 25종 + 강제 주입

### 문제 D — 워크플로우 층의 공백

- **용어집 실물 0.** `policies/skill-authoring-principles.md`에 용어집 형식은 있으나 vault `wiki/glossary/`는 비어 있음. 서비스 decisions 노트 7개. 원문이 "가장 강력한 기법"으로 꼽는 층이 규격만 있고 데이터가 없다
- **정렬 단계 부재.** 팀 플로우는 `ad:ticket` → `ad:work-prep` → 구현 → `ad:code-review` → `ad:work-close`. 원문 main flow 1단계(설계 트리를 소진할 때까지 인터뷰)에 대응하는 게 없다. `ad:ticket` 인터뷰는 5W1H 필드 채우기이지 정렬 세션이 아니다
- **구현 단계에 규율이 없다.** 티켓과 리뷰 사이가 비어 있어 매번 즉흥으로 진행된다

### 문제 E — 선행 계획 §4 스킬 매핑 미적용

| 항목 | 상태 |
|---|---|
| `ad:ticket` — Task 간 blocking edges, acceptance 체크박스, 본문 파일경로·스니펫 금지 | 미적용 |
| `ad:work-prep` — redundancy check, 기각 기록 대조, 버그 verify-claim 선행 | 미적용 |
| `ad:code-review` — smell 3원칙 | 적용됨 |
| `ad:code-review` — fixed-point 사전 검증 fail-fast | 미적용 |
| `ad:harness-optimize` — 가지치기 캐시 4종화 | 적용됨 |

## 3. 원칙 — 모델 자동 호출 폐지

**모든 팀 스킬과 외부 스킬은 사용자 호출 전용으로 전환한다.** (2026-08-08 확정)

근거:
- 자동 호출은 **컨텍스트 부하**(description 상주)와 **예측 불가**(호출 누락·오호출)를 동시에 부담한다. 실측상 routing 등록 13개 중 6개는 관측 기간 모델 호출 0회 — 비용만 냈다
- 원문 `writing-for-agents`의 두 부하 중 팀은 **인지 부하**를 택한다. 언제 뭘 부를지는 사람이 기억하고, 컨텍스트는 판단에 쓴다
- `policies/skill-authoring-principles.md` §1이 이미 "확신 없으면 사용자 호출이 기본값"으로 규정 — 본 결정은 그 기본값을 전면 적용하는 것

적용:
- 팀 스킬 전체에 `disable-model-invocation: true`
- CLAUDE.md `Skill routing` 절 제거 (문서 위치 결정 트리처럼 스킬이 아닌 규칙은 유지)
- superpowers SessionStart 강제 주입 무력화
- 대신 **flow 지도**를 `docs/harness-guide.md` 한 절로 둔다 — 사람이 인덱스 역할을 하므로 지도가 있어야 인지 부하가 감당된다 (원문 `ask-matt` 라우터의 변형 채택)

## 4. 판정 — 외부 스킬 스택 존치

| 스택 | 판정 | 근거 |
|---|---|---|
| **GSD** | **제거** (스킬 + 훅) | 호출 0인데 훅 9개가 상시 발화. Edit당 ~280ms. `.planning/` 산출물(B2B SSIS 전환 53 phase)은 repo에 남으므로 스킬 제거로 소실되지 않는다. 재개 시 재설치는 1회 명령 |
| **superpowers** | **유지 + 강제 호출 무력화** | 실사용 3종(brainstorming 7, systematic-debugging 5, executing-plans 1)은 팀 등가물이 없다. 3종만 뽑아 복사하면 다른 5종을 참조하고 있어 포크가 되고 업데이트가 끊긴다. 플러그인은 유지하고 `~/.claude/CLAUDE.md` 오버라이드로 강제 호출만 끈다 — 사용자 지시가 스킬보다 우선한다는 것은 superpowers 자체 규정 |
| **gstack** | **선별 유지 13종** | 실사용 8종(`codex`, `plan-eng-review`, `plan-ceo-review`, `document-generate`, `context-save`, `context-restore`, `browse`, `_gstack-command`) + 배포·QA 경로라 관측 0이어도 남기는 5종(`ship`, `review`, `qa`, `investigate`, `gstack-upgrade`). 나머지 48종(ios-*, design-*, canary, benchmark 등)은 팀 스택(Kotlin/Spring, .NET 레거시)과 무관 |
| **caveman** | 유지 | description 29토큰. 무해 |
| **mattpocock/skills 직접 설치** | **기각 유지** | 프로세스는 팀 스킬로 번안한다 (§5). 저장소 설치는 중복 |

절감 추정: GSD 394 + 훅 스폰 + gstack 약 1,100 ≈ **1,500토큰/세션 + Edit당 280ms**. superpowers 762토큰은 오버라이드 방식이라 남는다 (되돌리기 쉬운 쪽을 택함).

> 스택 제거·비활성은 개인 환경(`~/.claude`) 변경이라 팀 PR 대상이 아니다. 판정 근거만 여기 남긴다.

## 5. 채택 — 팀 main flow

mattpocock main flow를 팀 자산에 번안한다. 저장소는 설치하지 않고 프로세스만 가져온다.

```
/ad:grill  →  /ad:ticket  →  /ad:work-prep  →  /ad:implement  →  /ad:code-review  →  /ad:work-close
  정렬          스펙+분할        착수 준비          구현              리뷰               종료
```

| 원문 | 팀 | 형태 |
|---|---|---|
| `grill-with-docs` | `/ad:grill` | **신설** — frontier 라운드 인터뷰 + 용어집·ADR 인라인 기록 |
| `domain-modeling` | `/ad:grill` 내부 + `ad:work-prep` 용어집 절 | 기존 확장 (§6 Phase 4-3) |
| `to-spec` | `/ad:ticket` **스펙 모드** | 기존 확장 — 대화를 5W1H Feature로 합성해 YouTrack 발행. 인터뷰 없이 합성만 |
| `to-tickets` | `/ad:ticket` **분할 모드** | 기존 확장 — Task 분할 + YouTrack 네이티브 의존 링크(blocking edges) + acceptance 체크박스 |
| `implement` (내부 `tdd` 구동) | `/ad:implement` | **신설** — 얇게. 티켓 1개를 받아 `superpowers:test-driven-development` 구동, 타입체크·단위 테스트 주기 실행, 끝에 `/ad:code-review` 호출, `[이슈ID]` 규약으로 커밋 |
| `code-review` | `/ad:code-review` | 기존 (2축 + 조건부 운영축, 81회 사용, 가장 성숙) |
| — | `/ad:work-prep`, `/ad:work-close` | 팀 고유 — 위키 노트·소요시간 기록. 원문에 대응 없음 |

전부 **사용자 호출 전용** → 컨텍스트 부하 0. flow 지도는 `docs/harness-guide.md`에 둔다.

### 팀 현실과 어긋나는 지점 — 명시적 조정

- **수직 슬라이스 vs 단계 분리.** 원문 `to-tickets`는 tracer-bullet 수직 슬라이스를 요구하지만, 팀 단계 분리(개발/검증/배포)는 QA 주체가 시너지팀이라는 조직 현실 기반 수평 분할이다. **팀 규칙이 우선**한다. 수직 슬라이스는 **개발 Task 내부 분할**에만 적용한다
- **spec의 거처.** 원문은 별도 spec 문서를 만들지만, 팀은 YouTrack Feature 본문(5W1H)이 spec이다. 별도 spec 파일을 만들지 않는다
- **expand–contract.** 원문의 wide refactor 시퀀싱은 DB 이관·CDC 티켓 분할 시 참조한다 (팀은 개념 기보유)

### 컨텍스트 위생

- `/ad:grill` → `/ad:ticket`은 **한 컨텍스트에서 끊지 않고** 진행한다. 분할이 그릴링 사고 위에 서야 하기 때문
- 각 `/ad:implement` 앞에서 `/clear`. 티켓이 자족적이므로 앞 티켓 컨텍스트는 버려도 된다
- 단계 경계에서만 판단한다: 계속 → `/clear` → handoff → 서브에이전트 → `/compact` 순으로 먼저 맞는 것. `/compact`는 기본값이지 첫 선택이 아니다
- 상세는 `docs/harness-guide.md` 세션 위생 절에 둔다

## 6. 실행 계획

### Phase 4-0 — 세션 컨텍스트 규율 (최우선, 효과 최대)

문제 0 해소. 470k → smart zone(약 150k) 복귀가 목표. 다른 어떤 항목보다 효과가 크다.

1. **단계 경계 `/clear` 규율** — §5 컨텍스트 위생을 `docs/harness-guide.md`에 명문화하고 실제로 지킨다. 그릴링→분할은 한 창, 각 구현 앞에서 비운다. 이 항목 하나가 컨텍스트의 대부분을 결정한다
2. **파일 읽기는 Read로** — `cat`/`head`/`sed`/`tail`로 파일을 읽지 않는다. Bash는 실행이 목적일 때만. 근거: 30일 Bash 결과 15.1MB 중 상당량이 파일 내용 재출력
3. **절대 경로 사용** — 셸 cwd가 호출마다 초기화되므로 `cd` 대신 절대 경로로 명령한다. 근거: `cd` 4,152회 = Bash 호출의 36%
4. **한 번 읽은 파일은 다시 읽지 않는다** — 같은 파일 20회 이상 재독이 관측됨. 필요하면 스크래치에 요약을 남기고 그것을 참조
5. **대용량 조사는 서브에이전트로** — 결과만 회수해 메인 컨텍스트를 보호. 이미 `caveman:cavecrew-*`와 `Explore`가 설치돼 있다

위 5개는 `~/.claude/CLAUDE.md`(개인)와 팀 `CLAUDE.md`(PR) 양쪽에 짧게 박는다. 긴 설명 대신 강한 단어로: **smart zone**, **단계 경계**.

### Phase 4-0b — 컨텍스트·훅 다이어트 (저위험, 개인 환경)

1. **GSD 제거** — 스킬 18종 + 훅 9개. `.planning/` 산출물은 보존
2. **미사용 스킬 선별** — 실사용 12종 + 인프라·배포 경로 9종 유지, 나머지 58종 비활성
3. **superpowers 강제 호출 무력화** — `~/.claude/CLAUDE.md` 오버라이드
4. 실행 명령은 §8

### Phase 4-1 — 자동 호출 폐지 (하네스 PR)

1. `.claude/commands/ad/*.md` 전체에 `disable-model-invocation: true` 부여
2. CLAUDE.md `Skill routing` 절 제거
3. `docs/harness-guide.md`에 **flow 지도** 절 신설 — §5의 플로우와 온램프(버그·데이터 요청·월말 주기)를 사람이 읽는 인덱스로
4. `AGENTS.md` ↔ `CLAUDE.md` 정합 — Codex 진입점 고유 내용만 남기고 공통은 링크. 존재하지 않는 경로 참조 제거, 스킬 목록 최신화
5. `policies/skill-authoring-principles.md` §1 갱신 — 트리거 표를 "사용자 호출 전용이 팀 표준"으로 확정

### Phase 4-2 — 지시 강도 재표현 완주

1. `/ad:harness-optimize 제약` 모드를 **스킬 전수**에 실행 (1차는 15선만 처리)
2. 우선순위는 호출량 순: `code-review`(81) → `work-prep`(22) → `ticket`(5) → 나머지
3. heuristic은 "기본:" 접두 + 조정 조건 한 줄, 실패 사례 기반 게이트는 `근거:` 부착, 근거 없는 "반드시"는 강등 후보로 보고
4. 강도 하향은 전부 review-required ([harness-governance-policy.md](../policies/harness-governance-policy.md))

### Phase 4-3 — SoT 로드 다이어트

1. `docs/sprint/ticket-guide.md`(35KB)를 **절 단위 참조**로 전환 — 스킬이 통째로 읽지 않고 필요한 절만 지목
2. 스킬별 SoT 참조를 hard/soft 분류: 없으면 **출력이 틀리는** 참조만 명시 로드, 덜 날카로워질 뿐인 참조는 완만한 서술로 강등
3. `team-members.md`·frontmatter 스펙처럼 여러 스킬이 중복 로드하는 것은 필요 필드만 인용

### Phase 4-4 — 용어집 부트스트랩

1. `ad:work-prep` §3.5(코드 진입점 분석)에 **canonical 용어 lazy write** 절 추가 — 분석 중 확정된 도메인 용어를 vault `wiki/glossary/{term}.md`에 즉시 기록
2. 형식은 원문 `CONTEXT-FORMAT.md` 채택: 정의 1~2문장 + `_금지 동의어_` + 해소된 중의성 기록. 구현 디테일 금지 — 용어집은 글로서리이지 스펙이 아니다
3. 서비스별 `CONTEXT.md`는 만들지 않는다 — vault glossary 하나 + wikilink로 통일 ([knowledge-base-policy.md](../policies/knowledge-base-policy.md) 경계 유지)
4. ADR 3조건(되돌리기 어려움 + 미래 의문 + 실제 트레이드오프, 셋 다 충족)을 [engineering-policy.md](../policies/engineering-policy.md) §ADR에 명문화. 기록 위치는 기존 `wiki/services/{svc}/decisions/`
5. 착수 대상은 호출량 순: max, tobe, shopping

작동 신호: `ad:work-prep` 산출 노트가 glossary 용어를 wikilink로 인용하기 시작하면 가동. **3주 내 glossary 항목 0이면 실패로 판정하고 되돌린다.**

### Phase 4-5 — `/ad:grill` 신설

1. 사용자 호출 전용. 본문은 얇게 — 인터뷰 규율 + 용어집 인라인 기록 지시
2. **frontier 라운드 일괄** (2026-08-08 확정): 의존 없는 독립 질문은 한 라운드에 번호 + 추천안으로 묶고, 답이 선행 결정에 걸리는 질문은 다음 라운드로. 형식:
   ```
   ❓ **Q1** — **<질문 제목>**: <본문, 선택지 포함>

   ➡️ <추천안>
   ```
3. 유지되는 규율: **사실은 조회로 해소하고 결정만 질문.** 사실 조회는 서브에이전트로 돌리고 그 답에 걸리는 질문만 대기시킨다
4. 완료 기준: 프론티어가 빈 상태 — 설계 트리의 모든 가지를 방문. 사용자 확인 전에는 실행하지 않는다
5. `policies/skill-authoring-principles.md` §3의 "한 번에 하나씩"을 위 내용으로 교체

> 규율 변경이므로 review-required. 근거: 레거시 현대화·DB 이관처럼 독립 결정이 다발로 나오는 작업에서 1문1답은 왕복이 과다.

### Phase 4-6 — `/ad:ticket` 2모드 + 잔여 매핑

1. `/ad:ticket` **스펙 모드** — 대화를 5W1H Feature로 합성해 발행. 인터뷰 없이 합성만 (인터뷰는 `/ad:grill`이 이미 함)
2. `/ad:ticket` **분할 모드** — Task 분할 + YouTrack 네이티브 의존 링크(blocking edges) + acceptance criteria 체크박스 + 본문 파일 경로·스니펫 금지 명문화
3. `ad:work-prep` — redundancy check(요청을 도메인 개념으로 기존 구현 검색 + "어디를 찾아봤는지" 보고), 기각 기록 대조, 버그 제보는 재현 검증 선행
4. `ad:code-review` — fixed-point 사전 검증(ref 해석 + diff 비어있음)을 본 작업 전 fail-fast로

### Phase 4-8 — 주기 감사에 편입 (적용 완료)

일회성 정리로 끝나면 같은 퇴적이 다시 쌓인다. 감사 루프에 넣는다.

1. **`/ad:harness-optimize 스택` 모드 신설** — 컨텍스트 예산·외부 스킬 스택·훅·세션 지표를 네 축으로 판정
2. **측정 도구** `tools/harness_context_audit.py` — 임계값 초과를 `[경고]`로 surface. 문서는 [tools/README.md](../tools/README.md)
3. **주기**: 월 1회 + 외부 스킬·플러그인 신규 설치 시 / "느리다·놓친다" 체감 시 / 세션이 자주 컨텍스트 한계에 닿을 때 즉시 ([harness-governance-policy.md](../policies/harness-governance-policy.md) §주기)
4. **예산 정책**: 상주 8,000 tok / 세션 평균 200,000 tok (§컨텍스트 예산)
5. **작성 원칙 갱신**: 사용자 호출 전용이 팀 표준. 2층 구조의 아래층을 모델 호출 스킬 → 참조 파일로 ([skill-authoring-principles.md](../policies/skill-authoring-principles.md) §1)
6. **회차 기록**: [docs/skill-audit-baseline.md](./skill-audit-baseline.md) 3회차

### Phase 4-7 — `/ad:implement` 신설

1. 사용자 호출 전용, 얇게 (원문 `implement`는 15줄)
2. 내용: 티켓 1개를 받아 → 사전 합의된 seam에서 `superpowers:test-driven-development` 구동 → 타입체크·단일 테스트 파일 주기 실행, 전체 스위트는 끝에 1회 → `/ad:code-review` 호출 → `[이슈ID] 작업 내용` 규약으로 커밋
3. 커밋·푸시 전 사용자 확인은 팀 INVARIANT 유지

## 7. 순서와 근거

```
4-0  세션 컨텍스트 규율      ← 470k → smart zone. 효과 최대, 비용 최소
4-0b 컨텍스트·훅 다이어트    ← 개인 환경. 즉시 실행 가능
      ↓
4-1 자동 호출 폐지 + 문서 정합
      ↓
 ├→ 4-3 SoT 로드 다이어트       ← 컨텍스트·지연 양쪽에 직접 작용. 4-2보다 앞
 ├→ 4-2 지시 강도 재표현 완주   ← 놓침의 2순위
 └→ 4-6 ticket 2모드 + 잔여 매핑 ← 기계적, 병행 가능
      ↓
4-4 용어집  →  4-5 /ad:grill  →  4-7 /ad:implement
```

- 4-0을 최상단에 두는 이유: 상주 지시 9.4k는 470k 컨텍스트의 2%다. 스킬 다이어트만으로는 놓침이 해결되지 않는다
- 4-3을 4-2보다 앞에 두는 이유: SoT 재독(`ticket-guide.md` 35KB × 14회)이 컨텍스트와 지연에 동시에 작용한다
- 4-4를 4-2 뒤에 두는 이유: 지시가 평평한 상태에서 용어집 절을 추가하면 그 절도 89% 노이즈에 합류한다
- 4-5를 4-4 뒤에 두는 이유: 용어집이 있어야 인터뷰의 유도력이 산다
- 4-7을 마지막에 두는 이유: 앞 단계가 산출하는 티켓 품질이 올라간 뒤라야 얇은 구현 스킬이 성립한다

## 8. Phase 4-0 실행 명령 (사용자 직접 실행)

```bash
# 백업 먼저
cp ~/.claude/settings.json ~/.claude/settings.json.bak-$(date +%Y%m%d-%H%M%S)

# 1) GSD 스킬 비활성 (삭제 아님 — 되돌리기 가능)
mkdir -p ~/.claude/skills-disabled
mv ~/.claude/skills/gsd-* ~/.claude/skills-disabled/

# 2) GSD 훅 제거 (settings.json에서 gsd- 훅만 걸러냄)
python3 - <<'PY'
import json, pathlib
p = pathlib.Path.home()/".claude/settings.json"
s = json.loads(p.read_text())
removed = 0
for ev, groups in list(s.get("hooks", {}).items()):
    kept = []
    for g in groups:
        hs = [h for h in g.get("hooks", []) if "gsd-" not in h.get("command", "")]
        removed += len(g.get("hooks", [])) - len(hs)
        if hs:
            g["hooks"] = hs
            kept.append(g)
    if kept: s["hooks"][ev] = kept
    else: del s["hooks"][ev]
p.write_text(json.dumps(s, indent=2, ensure_ascii=False))
print(f"제거된 GSD 훅: {removed}개")
PY

# 3) 미사용 스킬 58종 비활성 (21종 유지 — 실사용 12 + 인프라·배포 9)
cd ~/.claude/skills
KEEP="orchestration computer-use codex plan-eng-review plan-ceo-review \
dev2-team-harness-ko dev2-ad-commands-ko youtrack-ticket-5w1h-ko \
document-generate context-save context-restore browse _gstack-command \
gstack gstack-upgrade setup-gbrain sync-gbrain ship review qa investigate"
for d in */; do
  d="${d%/}"
  case " $KEEP " in *" $d "*) continue;; esac
  mv "$d" ~/.claude/skills-disabled/
done
ls ~/.claude/skills | tr '\n' ' '; echo

# 4) 확인
ls ~/.claude/skills | wc -l              # 유지 21
ls ~/.claude/skills-disabled | wc -l     # 비활성 58 (GSD 18 포함)
```

유지 근거:

| 구분 | 스킬 | 근거 |
|---|---|---|
| 실사용 12 | `orchestration`(31), `codex`(14), `plan-eng-review`(11), `dev2-team-harness-ko`(8), `plan-ceo-review`(4), `document-generate`(3), `context-restore`(3), `youtrack-ticket-5w1h-ko`(2), `dev2-ad-commands-ko`(2), `context-save`(2), `browse`(2), `_gstack-command`(1) | 90일 실측 |
| 인프라·배포 9 | `gstack`, `gstack-upgrade`, `setup-gbrain`, `sync-gbrain`, `ship`, `review`, `qa`, `investigate`, `computer-use` | 사용 0이나 업그레이드·gbrain 인프라·배포 경로(`gstack-override-policy` 연결)·`orchestration`의 짝. **관찰 판정** — 다음 감사에도 0이면 비활성 |

`~/.claude/CLAUDE.md`에 추가할 세션 컨텍스트 규율 (Phase 4-0):

```markdown
## 세션 컨텍스트 규율

모델이 날카롭게 추론하는 대역은 **smart zone**(약 150k 토큰)이다. 실측 평균은 470k — 3배 밖에서 돌고 있었다. 다음을 지켜 창을 zone 안에 둔다.

- **단계 경계에서 비운다.** 그릴링→분할은 한 창에서, 각 구현 앞에서 `/clear`. 판단은 단계 경계에서만 하고, 순서는 계속 → `/clear` → handoff → 서브에이전트 → `/compact`
- **파일은 Read로 읽는다.** `cat`/`head`/`tail`/`sed`로 파일 내용을 출력하지 않는다. Bash는 실행이 목적일 때만
- **절대 경로로 명령한다.** 셸 cwd는 호출마다 초기화되므로 `cd`로 재진입하지 않는다
- **한 번 읽은 파일은 다시 읽지 않는다.** 다시 필요하면 스크래치에 요약을 남기고 그것을 참조
- **넓은 조사는 서브에이전트로 보내고 결론만 회수한다** (`Explore`, `caveman:cavecrew-investigator`)

근거: 2026-08-08 30일 실측 — 툴 호출 17,832회, 캐시 읽기 8,359M, 호출당 평균 컨텍스트 470k. Bash가 호출의 64.9%이고 그중 `cd`가 4,152회.
```

`~/.claude/CLAUDE.md`에 추가할 superpowers 오버라이드 (Phase 4-0b 항목 3):

```markdown
## Skill invocation (superpowers 오버라이드)

스킬은 **사용자가 호출할 때만** 실행한다. `superpowers:using-superpowers`의 자동 호출 지시(1% 규칙, 응답 전 스킬 스캔, 체크리스트 todo 강제)는 적용하지 않는다.
사용자가 이름을 대거나 명시적으로 요청하면 그때 호출한다.

근거: 2026-08-08 실측 — superpowers 28종 중 실사용 3종, 자동 호출 강제가 매 턴 스캔 비용을 유발. 팀 표준은 사용자 호출 전용 (docs/skill-stack-and-workflow-plan.md §3).
```

되돌리기: `mv ~/.claude/skills-disabled/* ~/.claude/skills/` + `cp ~/.claude/settings.json.bak-* ~/.claude/settings.json`

## 9. 검증

- 각 Phase는 **삭제 테스트** 동반 ([harness-governance-policy.md](../policies/harness-governance-policy.md)): 변경 전후 해당 스킬 1회 실행 비교
- 대표 시나리오 5개: 티켓 생성 / 주간보고 / 코드리뷰(레거시 diff) / work-prep(콜그래프 無 서비스) / sprint-close-check
- 판정 지표: 필수 게이트 위반 0 / 산출물 필수 항목 누락 0 / 세션 시작 상주 토큰 감소량 / `ad:work-prep` 1회 실행 토큰 감소량 / Edit 왕복 지연 감소량
- 결과는 [docs/skill-audit-baseline.md](./skill-audit-baseline.md)에 회차 기록

## 10. 기각 유지

| 항목 | 근거 |
|---|---|
| mattpocock/skills 직접 설치 | 프로세스는 §5로 번안. 저장소 설치는 중복 (2026-07-16, 08-06 판정 승계) |
| 별도 spec 문서 | YouTrack Feature 본문(5W1H)이 spec 역할. 이중 산출물은 드리프트 원인 |
| `ask-matt` 라우터 스킬 | flow 지도를 `docs/harness-guide.md` 한 절로 두는 것으로 대체 |
| 스킬별 독립 docs 페이지 | 내부 5인 팀에 이중 문서는 과잉. "작동 신호" 한 줄만 audit baseline에 흡수 |
| 디렉토리 버킷 재구성 | 슬래시 네임스페이스 파손. audit baseline 판정(활성/관찰/유지/삭제)이 기능 등가 |
| GSD 완전 삭제 | 비활성(`skills-disabled/` 이동)으로 충분. `.planning/` 재개 가능성 보존 |
