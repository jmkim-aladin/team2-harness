# 개발 2팀 하네스

Claude Code·Codex 에이전트와 팀원이 같은 기준으로 일하도록 묶은 개발 2팀의 정책·스킬·서비스 카탈로그 저장소다. 티켓을 받아 닫을 때까지 지금 무엇을 부를지 상황 지도와 `/ad:*` 스킬 26개가 안내하고, 절차의 무게는 걸린 위험에 맞춘다.

이 repo가 팀 정책·스킬·카탈로그의 source of truth(SoT)다. 서비스 repo에서는 여기 스킬을 symlink로 쓰고, 프로젝트 진행·도메인 지식은 로컬 위키(Obsidian vault)에 둔다. 둘의 경계는 [지식베이스 관리 정책](policies/knowledge-base-policy.md)이 정한다.

> **에이전트를 실행기가 아니라 판단자로 쓰고, 판단이 틀렸을 때 걸리는 그물(검증 루프·하드 게이트)을 환경에 깔고, 세션은 짧게, 지식은 아티팩트로.**
>
> [하네스 북극성](policies/harness-north-star.md) 6원칙(효과 순): 검증 루프 > 지시 · 문제를 통째로 · 컨텍스트는 smart zone 안에 · 문서 말고 환경이 진실 · 하드 게이트는 소수·기계 강제 · 기억은 아티팩트에

## 작업 플로우

```text
구상  티켓 전 ──── /ad:grill (세션 하나) · /ad:plan → /ad:plan-run (다세션) · /wayfinder (안개)
  │
  ▼  /ad:ticket 으로 합류
개발  티켓 하나
  /ad:ticket               스펙+분할 — 5W1H Feature 발행 → Task 분할
  /ad:work-prep            착수 준비 — 허브: 강도 판정 · 구현 계획 · "다음 단계" 지목
    ├─ 가벼움  바로 수정 → 직접 확인 → 리뷰
    ├─ 보통    구현 계획(슬라이스 1~2) → tdd → 리뷰
    ├─ 무거움  구현 계획 → 설계 검증 → 슬라이스마다 검증 명령 → 리뷰
    └─ 위험    무거움 + 반증 검토 → 페르소나 리뷰·안전 가정 입증 → 롤백 트리거
  (/ad:eng-review)         설계 검증 — 무거움 이상
  /ad:implement            구현 — 슬라이스 하나를 red→green 후 멈춘다
  /ad:code-review(-self)   리뷰 — 기준축·스펙축 분리 + 구조 재점검
  /ad:work-close           종료 — 소요시간 기록 + Fixed

주기  달력 ────── 주간 /ad:ticket-schedule · /ad:weekly-report / 월말 /ad:sprint-close-check · /ad:capacity-plan
상시  상황 ────── 지식 · 이해 · 협업 · 운영 DB · 하네스 — 티켓과 무관하게 언제든
```

그룹 이름은 시간 축이라 떠올릴 단서는 "지금 티켓 기준 어디냐" 하나다. 아래 요약은 [memory/claude-base.md](memory/claude-base.md) §작업 플로우에서 생성하므로 이 자리를 직접 고치지 말고 원본을 고친 뒤 `python3 tools/lint_harness_rules.py --sync-generated`를 돌린다. 상황별 전체 지도와 강도 기준표는 [harness-guide.md](docs/harness-guide.md) §작업 플로우가 SoT다.

<!-- generated:workflow-summary source=memory/claude-base.md -->
4그룹 — 떠올릴 단서는 "지금 티켓 기준 어디냐". 그룹 허브를 먼저 부르면 나머지를 안내한다. 지도 SoT(상황별 동사·강도·단계별 도구 명칭): `docs/harness-guide.md` §작업 플로우.

| 그룹 | 기억 단서 | 허브 → 흐름 |
|---|---|---|
| 구상 (티켓 전) | 아직 티켓이 없다 | `/ad:plan` · `/ad:grill` — 과제 크기 판정: 세션 하나 `/ad:grill` / 다세션 `/ad:plan`→`/ad:plan-run` / 세션을 넘는 안개 `/wayfinder` |
| 개발 (티켓 하나) | 티켓 하나를 끝낸다 | `/ad:work-prep`(강도 판정 + 구현 계획, "다음 단계" 지목) — `/ad:ticket → /ad:work-prep → (/ad:eng-review) → /ad:implement → /ad:code-review(-self) → /ad:work-close`. 구현 중 `tdd`·`diagnosing-bugs` |
| 주기 (팀 운영) | 달력 | 주간 `/ad:ticket-schedule`·`/ad:weekly-report` / 월말 `/ad:sprint-close-check`·`/ad:capacity-plan` |
| 상시 (언제든) | 상황 | 지식 `/ad:new-note` / 이해 `/wait-what` / 협업 `/ad:orchestration`·`/handoff` / 운영 DB `/ad:data-request` / 하네스 `/ad:harness-optimize` |

강도: 가벼움(1시간·설정) 바로 수정 / 보통(반나절·버그) 구현 계획 → `tdd` / 무거움(Task 여럿·모호·경계 변경) 전체 플로우 + 설계 검증 / 위험(운영 데이터·결제·인증·개인정보·공유 DB 스키마·비가역 — 크기 무관) 무거움 + 반증 검토·페르소나 리뷰·롤백 트리거. `/ad:implement`는 슬라이스 하나를 red→green 후 노트 체크하고 멈춘다.
<!-- /generated:workflow-summary -->

강도는 `/ad:work-prep`이 판정한다. 시간 축으로 고르되 위험 단서가 하나라도 있으면 크기와 무관하게 위험으로 보고, 애매하면 높은 쪽을 고른다 — 낮게 잡은 위험은 리뷰에서야 드러난다.

## 빠른 시작

```bash
git clone https://github.com/jmkim-aladin/team2-harness.git team2
cd team2
python3 tools/setup_harness.py           # harness.manifest.json 선언으로 환경 수렴 — 멱등, Mac/Windows 공통
python3 tools/setup_harness.py --check   # 바꾸지 않고 드리프트만 보고
```

셋업 도구는 `~/.claude/commands/ad`·`~/.claude/skills`·`~/.codex/skills` symlink, settings 훅·env, 팀 메모리 링크, 이 repo의 pre-commit 게이트(`core.hooksPath`)를 맞춘다. 토큰 값은 건드리지 않으므로 `YOUTRACK_TOKEN` 등록과 `gh auth login`은 [셋업 가이드](docs/setup-guide.md)를 따른다. `./scripts/setup.sh`(Windows `scripts/setup.ps1`)는 레거시 경로다.

처음 쓸 때:

1. **티켓이 있으면** 착수 준비 허브부터 부른다 — Claude Code `/ad:work-prep DEV2-XXXX`, Codex `$ad-work-prep DEV2-XXXX`. 강도와 구현 계획을 티켓 노트에 쓰고 다음에 부를 스킬을 알려 준다
2. **티켓이 없으면** `/ad:grill`로 무엇을 만들지 정렬한 뒤 `/ad:ticket`으로 발행한다
3. 그 밖의 일은 말로 요청한다. `/ad:*` 대부분은 모델 호출이라 요청이 description에 맞으면 에이전트가 스스로 부른다

Claude Code의 `/ad:*`는 symlink라 어느 repo에서든 쓸 수 있다. 코드 작업·PR 리뷰는 서비스 repo에서, 정책·스킬 수정은 이 repo에서 한다.

## 왜 이렇게 만들었나

에이전트와 팀이 실제로 겪은 실패마다 막는 장치를 붙였다. 지시를 늘리기보다 허브·검사·게이트로 막는 쪽을 고른다.

| 겪은 실패 | 막는 장치 |
|---|---|
| 무엇을 만들지 합의 없이 바로 만든다 | `/ad:grill` 정렬 인터뷰 → `/ad:ticket` 5W1H. spec은 YouTrack Feature 본문 하나다 |
| 중간 단계를 건너뛴다 — 90일 실측 work-prep 171회, eng-review 0회, implement 1회 | `/ad:work-prep` 허브가 강도를 판정하고 "다음 단계"로 다음 스킬을 지목한다 |
| 빌드 통과를 완료로 본다 | 구현 계획의 검증 명령(실제 실행), DoD의 "변경 전 실패 → 변경 후 통과" 증거 |
| 초록불을 만들려고 테스트·기준을 낮춘다 | 리뷰의 완화 신호 스캔(`tools/gate_loosening_scan.py`) |
| 재시도가 이중 지급·중복 처리를 만든다 | 설계 검증의 멱등키 계약, DB 스크립트·SP PR의 SP 중복 호출 판정 |
| 버튼 문구에도 결제 변경에도 같은 무게의 절차를 쓴다 | 강도 4단 — 가벼운 일은 바로 고치고, 위험한 일은 크기와 무관하게 전체 절차를 거친다 |
| 스킬이 많아 컨텍스트가 붓고 엉뚱한 스킬이 발동한다 | 가지치기(30→26개), 라우팅은 description 한 곳, 메뉴의 `[그룹·단계]` 태그 |
| 세션이 길어져 판단이 흐려진다 — 호출당 평균 컨텍스트 435k, smart zone의 약 3배 | 단계 경계에서 비우기, 넓은 조사는 서브에이전트, 위임은 5요소 계약 |
| 같은 내용을 두 곳에 쓰면 한쪽이 낡아 에이전트가 자신 있게 틀린다 | `canonical` → `generated` 블록과 대조 테스트. 이 README의 요약·스킬 표도 같은 방식으로 지킨다 |

근거: [스킬 감사 베이스라인](docs/skill-audit-baseline.md) 7회차(2026-10-21 실측·가지치기), [외부 스킬 팩 통합 판정](docs/skill-packs-adoption-review.md), [하네스 북극성](policies/harness-north-star.md).

## 스킬 레퍼런스

`/ad:*` 26개를 작업 플로우의 4그룹으로 나눈다. 그룹은 각 command `description` 맨 앞 `[그룹·단계]` 태그와 같다. 호출 열의 **모델**은 요청이 description에 맞으면 에이전트가 스스로 부른다는 뜻이고, **사용자**는 사이드이펙트가 있어 사람이 시점을 정한다는 뜻이다(frontmatter `disable-model-invocation: true`).

<!-- generated:user-only source=policies/skill-authoring-principles.md -->
**사용자 호출 전용 6종**(사이드이펙트, 사람이 시점 결정): `/ad:code-review`, `/ad:code-review-self`, `/ad:explain`, `/ad:implement`, `/ad:plan-run`, `/ad:ticket-schedule`
<!-- /generated:user-only -->

**Codex**에서는 `/ad:{name}`을 `$ad-{name}`으로 부른다. `.codex/skills/ad-{name}/`은 같은 command 파일을 런타임에 읽는 얇은 alias라 절차는 하나다. 정책·티켓·`/ad:*` 호환용 컨텍스트 스킬 `$dev2-team-harness-ko`·`$youtrack-ticket-5w1h-ko`·`$dev2-ad-commands-ko`가 함께 깔린다.

아래 표는 사람이 쓰는 사본이다. 스킬을 추가·삭제하거나 그룹·호출 방식을 바꾸면 `tests/test_work_prep_command_docs.py`가 실패하므로 같은 PR에서 표도 고친다.

### 구상 (티켓 전)

| 스킬 | 언제 쓰나 | 호출 |
|---|---|---|
| `/ad:grill` | 만들기 전에 아이디어·기능·설계를 질문으로 정렬한다 — 세션 하나에 담기는 과제 | 모델 |
| `/ad:plan` | grill 결과를 vault 계획 노트로 합성한다 — 다세션 프로젝트·로드맵 | 모델 |
| `/ad:plan-run` | vault 계획의 internal milestone 하나를 실행하고 진행·근거를 기록한다 | 사용자 |

### 개발 (티켓 하나)

| 스킬 | 언제 쓰나 | 호출 |
|---|---|---|
| `/ad:ticket` | YouTrack DEV2 티켓을 5W1H로 쓰고 Task로 분할한다 | 모델 |
| `/ad:work-prep` | 착수 준비 허브 — 티켓에서 위키 노트·코드 진입점·강도·구현 계획을 만들고 다음 단계를 지목한다 | 모델 |
| `/ad:eng-review` | 구현 전 계획의 스코프·아키텍처·품질·테스트·성능을 이슈 단위로 판정한다 — 무거움 이상 | 모델 |
| `/ad:implement` | 구현 계획의 슬라이스 하나를 TDD로 구현하고 멈춘다. 커밋은 확인 후 | 사용자 |
| `/ad:code-review` | GitHub PR을 팀 기준으로 리뷰한다 — 기준축·스펙축 분리 | 사용자 |
| `/ad:code-review-self` | 자기 PR을 별도 리뷰어 에이전트에 맡기고 반영·답글·재리뷰를 완료까지 반복한다 | 사용자 |
| `/ad:work-close` | 소요시간(work item)을 입력하고 티켓을 Fixed로 닫는다 | 모델 |

### 주기 (팀 운영)

| 스킬 | 언제 쓰나 | 호출 |
|---|---|---|
| `/ad:ticket-schedule` | 주간 — planned 티켓의 시작예정일·완료목표일을 건별 확인 후 코멘트로 일괄 입력한다 | 사용자 |
| `/ad:weekly-report` | 주간 — 주간업무 보고서를 쓴다. `planned` 모드는 계획 스냅샷 | 모델 |
| `/ad:sprint-close-check` | 월말 — 미종료·SP·5W1H·OKR 누락 후보를 자가점검한다 | 모델 |
| `/ad:capacity-plan` | 월말 — 가용 맨데이·velocity 기준으로 SP 초과를 판정한다 | 모델 |
| `/ad:okr` | 수시 — OKR을 조회·작성한다 | 모델 |
| `/ad:wbs` | 수시 — YouTrack 루트 이슈 하위 트리를 WBS·간트(엑셀·HTML)로 뽑는다 | 모델 |
| `/ad:granola-sync` | 수시 — Granola 회의록을 동기화한다 | 모델 |

### 상시 (언제든)

| 스킬 | 언제 쓰나 | 호출 |
|---|---|---|
| `/ad:new-note` | 지식 — 신규 운영 위키 노트를 쓴다(write-time 분류) | 모델 |
| `/ad:team2-kb-read` | 지식 — YouTrack 지식베이스(KB·기술자료) 문서를 조회한다 | 모델 |
| `/ad:kb-publish` | 지식 — 문서를 YouTrack KB에 등록하거나 초안으로 올린다 | 모델 |
| `/ad:explain` | 지식 — 코드 변경·분석 설명서를 만든다. `--tldr`은 아키텍처 one-pager | 사용자 |
| `/ad:architecture-analysis` | 지식 — 저장소 아키텍처를 분석한다(Clean/Hexagonal/DDD, 네이밍) | 모델 |
| `/ad:orchestration` | 협업 — Herdr peer-agent와 위임·핑퐁·병렬 fan-out. `HERDR_ENV=1`일 때 | 모델 |
| `/ad:paperclip-dispatch` | 협업 — DEV2 티켓을 로컬 Paperclip Inbox에 등록하고 프로젝트·정책으로 분류한다(파일럿) | 모델 |
| `/ad:data-request` | 운영 DB — 운영 데이터 추출 SQL을 data-requests-dev2에 등록한다 | 모델 |
| `/ad:db-stop` | 운영 DB — 현재 Mac 계정의 운영 DB 조회 취소·종료를 확인한다 | 모델 |
| `/ad:harness-optimize` | 하네스 — 중복 제거, KB 동기화, 스킬·제약·스택 감사, repo↔vault 드리프트 | 모델 |

## 단계별 보조 장치

외부 스킬 팩(Pocock·pstack·Osmani)에서 가져온 장치는 새 스킬이 아니라 기존 단계 아래 붙였고, 무거운 장치는 강도가 높을 때만 켜진다. 정식 명칭·쓰는 신호·출처 전체는 [harness-guide.md](docs/harness-guide.md) §단계별 도구 명칭이 SoT다.

| 단계 | 보조 장치 | 켜지는 때 |
|---|---|---|
| 착수 준비 | 강도 판정 · 근거 등급 · 구현 계획(완료 조건 · 검증 명령 · 경계 · 슬라이스 · 구현 중 신호) | 강도 판정은 항상, 구현 계획은 보통 이상 개발 Task |
| 설계 검증 | 멱등키 계약 · Expand/Contract · 성능 판정 규칙 · 시도 기록 · 사용 예 선행 설계 · 반증 검토 | 무거움 이상. 반증 검토는 위험의 비가역 결정 |
| 구현 | 슬라이스 실행 · 범위 밖 기록 | 보통 이상 |
| 리뷰 | 완화 신호 스캔 · 교차 모델 리뷰 · 페르소나 리뷰 · 안전 가정 입증 · SP 중복 호출 판정 | 모든 강도. 페르소나 리뷰·안전 가정 입증은 위험 |
| 종료 | DoD 체크리스트 · 롤백 트리거 | 롤백 트리거는 위험 |
| 디버깅 | 경쟁 가설 조사 | `diagnosing-bugs`가 막히거나 재현이 안 될 때 |
| 공통 게이트 | 승인 응답 판별 | 커밋·푸시·티켓·KB 승인 질문에 "알아서"만 돌아올 때 |

**엔진** — 스킬이 조합하는 규율이다. 모델이 이미 아는 이름이라 바꾸지 않는다([스킬 작성 원칙](policies/skill-authoring-principles.md) §구조).

- vendored [mattpocock/skills](vendor/mattpocock/): `grilling` · `domain-modeling` · `tdd` · `codebase-design` · `diagnosing-bugs` · `prototype` · `research` · `/wayfinder` · `/handoff` · `/wait-what` · `/teach` · `/to-questionnaire` · `wizard` · `resolving-merge-conflicts`. 제외 목록과 팀 오버라이드는 [mattpocock 오버라이드 정책](policies/overrides/mattpocock.md)
- 팀 자체: `/eli5` · `/eli5-html` · `/eli5-onboard` — 낯선 주제·저장소를 빨리 이해하고 남에게 옮긴다
- 외부: `aside-browser`(Aside) — 웹 UI 개발·테스트의 기본 브라우저. 규칙은 [memory/claude-base.md](memory/claude-base.md) §브라우저 개발·테스트

**페르소나 리뷰 3종** — 보안 감사 · 테스트 엔지니어 · 데이터 정합성 감사. `/ad:code-review`가 위험 강도 PR에서만 읽는 프롬프트 파일이라 평소 세션의 상주 비용은 0이다([personas.md](docs/code-review/personas.md)).

## 저장소 구조

```text
CLAUDE.md              Claude Code 진입점 — 상주 핵심 규칙
AGENTS.md              Codex 진입점 — Codex에만 해당하는 것
policies/              팀 정책 — 북극성·지시 강도·거버넌스·리뷰·DB 접근 등
catalog/               서비스 프로파일(*.yaml)과 공통 서비스 registry
templates/             서비스 하네스 템플릿, PR·DoD 체크리스트, 티켓·vault 노트 템플릿
docs/                  가이드 — 작업 지도, 셋업, 스프린트 운영, 리뷰·설계 검증 자료
tools/                 검사·동기화·운영 도구 — lint, secret scan, 컨텍스트 감사, 셋업 수렴
tests/                 도구·문서 계약 회귀 테스트
.claude/commands/ad/   팀 스킬 /ad:* 원본 — 절차 SoT
.codex/skills/         Codex alias($ad-*)·컨텍스트 스킬 — command 원본을 읽는 얇은 층
vendor/mattpocock/     vendored 엔진 스킬
memory/                Claude 전역 메모리 원본(claude-base.md)
.githooks/             pre-commit 게이트 — secret scan · lint ratchet · unittest
```

서비스 목록은 [CLAUDE.md](CLAUDE.md) §서비스, 카탈로그 작성법은 [catalog/README.md](catalog/README.md), 도구별 사용법은 [tools/README.md](tools/README.md)에 있다.

## 넣지 않은 것

외부 팩은 교과서로 읽고 통하는 것만 기존 단계에 흡수한다. 통째로 설치했다가 트리거 중복·상주 비용으로 걷어낸 이력이 있어서다.

| 항목 | 판정 | 근거 |
|---|---|---|
| superpowers | 2026-08-08 제거 — mattpocock 엔진이 대체 | [mattpocock 오버라이드 정책](policies/overrides/mattpocock.md) |
| GSD | 2026-08-08 비활성 — 90일 호출 0, 훅 9개가 모든 편집을 검문 | [거버넌스 정책](policies/harness-governance-policy.md) §컨텍스트 예산, 감사 3회차 |
| gstack | 2026-09-28 제거 — `/ad:eng-review`·`diagnosing-bugs`·`/handoff`·`/ad:code-review`로 번안 | [스킬 감사 베이스라인](docs/skill-audit-baseline.md) 6회차 |
| Osmani 플러그인 통째 설치 | 보류 — description 25개 상주와 트리거 중복. 장치만 개별 흡수 | [외부 스킬 팩 통합 판정](docs/skill-packs-adoption-review.md) §가져오지 않은 것 |
| pstack 설치 | 컨셉만 흡수 — 실행 검증 계약·리뷰 증거 | [pstack 적용 검토](docs/pstack-harness-adoption-review.md) |
| 3레벨 네임스페이스 `ad:dev:*` | 보류 — 스킬이 여러 그룹에 걸치면 이름이 거짓이 된다. 분류는 지도와 메뉴 태그가 맡는다 | [스킬 감사 베이스라인](docs/skill-audit-baseline.md) 7회차 |
| `SPEC.md`·`tasks/*.md` 같은 repo 계획 파일 | 미도입 — spec은 YouTrack Feature 본문, 계획은 vault 티켓 노트 `## 구현 계획` | [외부 스킬 팩 통합 판정](docs/skill-packs-adoption-review.md) |
| 세션 시작 라우터 훅 | 미도입 — description이 이미 라우팅이라 이중 라우팅이 된다 | 같은 문서 |

## 하네스 고치기

- **에이전트가 실수하면 스킬·지도를 고친다.** 사람이 같은 실수를 매번 잡는 대신 다음 세션이 덜 틀린다. 원인을 빠진 규칙·반복 업무·위험 행동·컨텍스트 부족으로 나눠 맞는 자리에 보강한다([AI 사용 정책](policies/ai-usage-policy.md) §하네스 개선 루프)
- **정기 감사** — 스프린트 마감 주간에 `/ad:harness-optimize 스킬`·`제약`, 월 1회 `스택`. 결과는 [스킬 감사 베이스라인](docs/skill-audit-baseline.md)에 회차로 남긴다. 에이전트는 제안까지 하고 판정·머지는 사람이 한다([거버넌스 정책](policies/harness-governance-policy.md))
- **방향 판정** — 개선 제안·하네스 PR은 전진시키는 북극성 원칙 번호를 한 줄로 적는다. 지시 추가는 검사·훅·아티팩트로 풀 수 없을 때 쓰는 마지막 수단이다
- **스킬 추가·변경** — [스킬 작성 원칙](policies/skill-authoring-principles.md)(트리거·3층 구조·가지치기)을 따르고, 지도·description 태그·Codex alias·이 README 표를 같은 PR에서 고친다. 갱신하지 않은 지도는 거짓말을 한다
- **지시문 쓰기** — 지시 강도(invariant/policy/heuristic/example)와 이유를 함께 쓴다([지시 강도·우선순위 정책](policies/instruction-precedence-policy.md))
- **브랜치·커밋** — 하네스 자체 변경은 티켓 없이 `team2/{작업-slug}` 브랜치와 `[TEAM2] 작업 내용` 커밋을 쓴다([브랜치 전략](policies/branching-strategy.md) §개발2팀 하네스 예외). 서비스 작업은 `feature/{이슈ID}`와 `[{이슈ID}] 작업 내용`

커밋 전에 아래 검사를 통과시킨다. pre-commit(`.githooks/pre-commit`)도 바뀐 파일에 맞춰 같은 검사를 돌린다.

```bash
python3 tools/lint_harness_rules.py --check            # 지시문 규약 ratchet + generated 드리프트(R7)
python3 tools/lint_harness_rules.py --sync-generated   # canonical → generated 재생성 (README 포함)
python3 -m unittest discover -s tests -p 'test_*.py'   # 지도·스킬·README 대조 등 회귀 테스트
python3 tools/secret_scan.py                           # 시크릿 스캔
```
