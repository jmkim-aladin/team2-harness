

# 개발 2팀 하네스

팀 공통 정책, 스킬, 서비스 카탈로그의 source of truth.
셋업: [docs/setup-guide.md](./docs/setup-guide.md) | 운영: [docs/harness-guide.md](./docs/harness-guide.md)

## 구조

- `policies/` — 팀 정책 (엔지니어링, 브랜치, 코드리뷰, 배포, AI, 현대화, 보안, 장애대응, 팀원, KB, AGENTS.md, gstack 오버라이드, mermaid)
- `catalog/` — 서비스 프로파일 (max, tobe, naru, bazaar, aasm, storefront, caravan, pod, shopping, blog) 및 `catalog/common-services/registry.yaml` 공통 서비스 registry
- `templates/` — 서비스 하네스 템플릿, PR/DoD 체크리스트, 티켓 템플릿
- `.Codex/commands/ad/` — 팀 스킬 (ticket, code-review, kb-read, kb-list, kb-sync, okr, weekly-report, harness-optimize)
- `scripts/setup.sh` — 원커맨드 셋업
- `docs/` — 가이드 문서
- `docs/designs/` — 설계 문서 (스토어프론트 플랫폼 방향, 테넌트 모델, 인증, 스코프 등)
- `docs/okr/` — OKR 문서 (연간, 분기별 팀/개인)
- `docs/sprint/` — 스프린트 운영 (워크플로우 실행, 티켓 가이드, SP 가이드, 계획 변경, 주간업무 보고)

# Codex 진입점 — 개발 2팀 하네스

이 파일은 Codex에서 `CLAUDE.md`와 같은 역할을 한다.
작업은 항상 **개발 2팀 하네스**(team2)를 source of truth로 한다.

## 팀 하네스 위치

```ㄴ
$TEAM2_HARNESS_PATH = /Users/jm/Documents/workspace/team2
$LOCAL_WIKI_PATH    = /Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2
```

- 가이드/정책/스킬/서비스 카탈로그/스프린트 산출물: 팀 하네스 (`$TEAM2_HARNESS_PATH`)
- 도메인 분석, Graphify 산출물, Querybook, daily/meetings/tickets 노트: 로컬 Obsidian vault (`$LOCAL_WIKI_PATH`)
- `YOUTRACK_TOKEN`이 환경에 없으면 `~/.claude/settings.json`의 `env.YOUTRACK_TOKEN`을 읽되 값은 출력하지 않는다.

## 핵심 규칙

- 브랜치: `feature/{이슈ID}` | 커밋: `[{이슈ID}] 작업 내용`
- 예외: 개발2팀 하네스(`team2`) 자체 변경은 티켓 없이 `team2/{작업-slug}` 브랜치와 `[TEAM2] 작업 내용` 커밋을 사용할 수 있다.

- 모든 작업은 YouTrack 티켓(5W1H)에서 시작한다. 단, 개발2팀 하네스 자체 변경은 [브랜치 전략](./policies/branching-strategy.md)의 하네스 예외를 따른다.
- YouTrack 티켓/Task 생성, 상태 변경, KB 변경, 커밋, 푸시, 머지, PR 생성/머지는 사용자 확인 후에만 수행한다. 하네스 예외 작업은 DEV2 티켓 없이도 사용자 명시 지시로 commit/merge/push 가능하다.
- Feature는 1주 이하, Task는 1일 이하로 유지한다. 초과 시 분할한다.
- DB/SP 변경은 별도 승인, 프로덕션 배포는 사람 승인이 필요하다.
- 알라딘 인증, 뉴빌링 등 공통 서비스 영향은 [policies/common-service-policy.md](./policies/common-service-policy.md)와 [catalog/common-services/registry.yaml](./catalog/common-services/registry.yaml)을 함께 확인한다.
- 신규 빌링, 결제, 정산, 구독, 빌링키 기능은 [catalog/common-services/new-billing.yaml](./catalog/common-services/new-billing.yaml)의 뉴빌링 API 경계를 먼저 확인한다. 현재 팀 서비스 active 연동은 없는 상태로 기록한다.
- 신규 백엔드는 Kotlin + Spring Boot를 우선한다. 신규 .NET 금지, SP 직접 호출 금지.
- 운영 데이터 추출 SQL은 `AladinCommunication/data-requests-dev2` 레포에서 관리한다.
- DB 관련 MCP 도구는 사용하지 않는다. dev RDS `sqlcmd`는 read-only 조회만 허용한다.

## Claude Code 전역 규칙 동기화

- 코드를 작성·수정·리뷰·리팩터하기 전에는 사소한 오타·포맷 수정이 아닌 한 `$karpathy-guidelines`를 먼저 호출한다.
- 커밋 메시지에 AI co-author footer나 도구 자기참조 footer를 추가하지 않는다.
- 커밋 본문은 의사결정·영향 범위 중심으로 짧게 작성하고, 코드 수준 구현 디테일 bullet 나열은 피한다.

## Skill routing

요청이 들어오면 먼저 Codex Skill로 라우팅한다. 매칭되는 Skill이 있으면 다른 도구보다 먼저 호출한다.

| 요청 | Codex Skill |
|------|-------------|
| 개발2팀 정책/카탈로그/KB/OKR/주간업무/코드리뷰 컨텍스트 | `$dev2-team-harness-ko` |
| YouTrack 티켓 생성 (DEV2), `/ad:ticket` | `$youtrack-ticket-5w1h-ko` |
| Claude Code `/ad:*` 명령 호환 실행 | `$dev2-ad-commands-ko` |
| 저장소 전체 아키텍처·Clean/Hexagonal/DDD·네이밍 분석 | `$ad-architecture-analysis` |
| Granola 회의록 가져오기/동기화, Tolaría 회의록 반영 | `$ad-granola-sync` |
| Product ideas, "is this worth building", brainstorming | `$office-hours` |
| Bugs, errors, "why is this broken", 500 errors | `$investigate` |
| Ship, deploy, push, create PR | `$ship` |
| QA, test the site, find bugs | `$qa` |
| Code review, check my diff | `$review` |
| Update docs after shipping | `$document-release` |
| Weekly retro | `$retro` |
| Design system, brand | `$design-consultation` |
| Visual audit, design polish | `$design-review` |
| Architecture review | `$plan-eng-review` |
| Code quality, health check | `$health` |

Claude Code의 `.claude/commands/ad/*.md`는 여전히 source of truth다. `/ad:*` 요청은 해당 command 문서를 먼저 읽고 같은 절차로 수행한다.

## 주요 `/ad:*` 매핑

Codex에서는 아래 `/ad:*` 명령을 같은 의미의 `$ad-*` 스킬 alias로도 실행한다.

- `$ad-ticket` → `/ad:ticket`
- `$ad-work-prep` → `/ad:work-prep`
- `$ad-work-board` → `/ad:work-board`
- `$ad-code-review` → `/ad:code-review`
- `$ad-architecture-analysis` → `/ad:architecture-analysis`
- `$ad-weekly-report` → `/ad:weekly-report`
- `$ad-weekly-planned` → `/ad:weekly-planned`
- `$ad-sprint-close-check` → `/ad:sprint-close-check`
- `$ad-okr` → `/ad:okr`
- `$ad-team2-kb-read` → `/ad:team2-kb-read`
- `$ad-team2-kb-list` → `/ad:team2-kb-list`
- `$ad-team2-kb-sync` → `/ad:team2-kb-sync`
- `$ad-harness-optimize` → `/ad:harness-optimize`
- `$ad-data-request` → `/ad:data-request`
- `$ad-service-activity` → `/ad:service-activity`
- `$ad-capacity-plan` → `/ad:capacity-plan`
- `$ad-granola-sync` → `/ad:granola-sync`
- `$ad-new-note` → `/ad:new-note`

- 티켓 생성, YouTrack 티켓: `/ad:ticket`
- 작업 준비, 티켓번호/할일로 위키 노트 + 업무 컨텍스트 묶기: `/ad:work-prep`
- Hermes work board와 Discord dispatch request 갱신: `/ad:work-board`
- 저장소 전체 구조·설계 철학 분석과 Markdown/HTML 저장: `/ad:architecture-analysis`
- 주간업무 보고: `/ad:weekly-report`
- 주간 계획 스냅샷: `/ad:weekly-planned`
- 스프린트 마감 자가점검: `/ad:sprint-close-check`
- OKR 조회/작성: `/ad:okr`
- KB 조회/목록/동기화: `/ad:team2-kb-read`, `/ad:team2-kb-list`, `/ad:team2-kb-sync`
- 하네스 최적화, repo↔vault 경계 점검: `/ad:harness-optimize`
- 데이터 추출 요청, SQL 등록: `/ad:data-request`
- 서비스별 작업 활동 조회: `/ad:service-activity`
- 다음달 가용 맨데이/velocity, capacity plan: `/ad:capacity-plan`
- Granola 회의록 가져오기, Tolaría 회의록 동기화: `/ad:granola-sync`
- 신규 운영 위키 노트 작성: `/ad:new-note`

## gstack 스킬

gstack 스킬(`/ship`, `/review`, `/cso`, `/qa` 등) 사용 시 반드시 `policies/gstack-override-policy.md`를 참조한다.
팀 Git 컨벤션·배포 정책이 gstack 기본값보다 우선한다.
gstack 본문은 Claude Code 도구명을 사용하므로 Codex에서는 다음처럼 대응한다: `Bash`→`exec_command`, `Read`→`sed`/`rg`/`cat`, `Write/Edit`→`apply_patch`, `Grep/Glob`→`rg`/`find`, `Agent`→가능하면 multi-agent, `AskUserQuestion`→필요 시 짧은 직접 질문.

## 외부 시스템

- YouTrack: `https://aladincommunication.youtrack.cloud` — REST API(`$YOUTRACK_TOKEN`)만 사용. MCP 미사용.
- GitHub: `gh` CLI로 PR/이슈 조회. Org는 `AladinCommunication`, 개인 계정은 `jmkim-aladin`.
- 운영 위키: 도메인 분석/Querybook 산출물은 로컬 위키에, 가이드/정책/스킬은 팀 하네스에 둔다.

## GBrain 공유 brain

- DEV2 공유 brain은 Hermes Docker의 `gbrain-team2` 서비스가 제공하는 HTTP MCP다.
- 로컬 에이전트 MCP URL은 `http://127.0.0.1:3131/mcp`, Hermes 컨테이너 내부 URL은 `http://gbrain-team2:3131/mcp`다.
- Codex, Claude Code, Hermes Discord/CLI는 같은 MCP를 사용한다. Mac의 직접 `gbrain` CLI는 개인 로컬 PGLite일 수 있으므로 공유 brain 운영 명령은 `docker exec gbrain-team2 ...`로 실행한다.
- Docker runtime은 `GBRAIN_SOURCE=team2-vault`로 실행해 업무 원장인 vault를 기본 검색 범위로 둔다. 하네스 검색이 필요하면 명시 source나 로컬 하네스 파일을 사용한다.
- 상시 지식 강화 실행 주체는 Hermes다. Hermes cron은 `tools/run_team2_knowledge_cycle.py`를 실행해 vault projection/board/outbox/status를 갱신하고, `tools/run_granola_sync_cycle.py`를 10분마다 실행해 Granola 회의록을 vault로 동기화한다. 야간 agent job은 GBrain MCP를 사용해 domain hardening draft를 만든다.
- PGLite maintenance는 host LaunchAgent `com.team2.gbrain-maintenance`가 01:40 KST에 `gbrain-team2`를 짧게 중지한 뒤 `/Users/jm/.hermes-team2/scripts/gbrain-maintenance.sh`로 `sync --all`, `sync --source team2-vault --full`, `extract`, `embed`, source별 `dream`, `doctor`를 수행한다. 상태 조회는 `/Users/jm/.hermes-team2/scripts/gbrain-maintenance.sh --status`를 사용하며 maintenance를 실행하지 않아야 한다.
- gbrain 검색 결과는 후보 근거다. 확정 지식, 승인, done/canonical 상태는 vault/YouTrack/코드/사용자 확인으로 검증한다.
- gbrain bearer token과 API key는 문서나 커밋에 기록하지 않는다.

## 문서 규칙

- 한국어 작성, 파일명 `kebab-case.md`.
- 분석/평가 가이드는 `docs/analysis-guides.md`를 참조한다.
- 모든 정책은 `policies/` 하위에서 찾는다.
- 문서 H1/title 규칙은 `policies/wiki-document-language-and-title-policy.md`를 따른다.
- CLAUDE.md/AGENTS.md는 최소화 원칙(`policies/claude-md-policy.md`)을 따른다.
- 모든 작업은 YouTrack 티켓(5W1H)에서 시작. 단, 개발2팀 하네스 자체 변경은 티켓 없이 진행 가능
- Feature ≤ 1주 (필수) / Task ≤ 1일 (필수) — 초과 시 분할. 상세: [docs/sprint/ticket-guide.md](./docs/sprint/ticket-guide.md)
- DB/SP 변경 별도 승인, 프로덕션 배포 사람 승인
- 신규 백엔드 Kotlin + Spring Boot, 신규 .NET 금지, SP 직접 호출 금지

## 서비스

| 서비스 | 유형 | 프로파일 |
|--------|------|----------|
| max (만권당) | legacy | [catalog/max.yaml](./catalog/max.yaml) |
| tobe (투비컨티뉴드) | legacy | [catalog/tobe.yaml](./catalog/tobe.yaml) |
| naru | new | [catalog/naru.yaml](./catalog/naru.yaml) |
| bazaar | new | [catalog/bazaar.yaml](./catalog/bazaar.yaml) |
| aasm | new | [catalog/aasm.yaml](./catalog/aasm.yaml) |
| storefront (스토어프론트) | new (설계 중) | [catalog/storefront.yaml](./catalog/storefront.yaml) |

## gstack 스킬

gstack 스킬(`/ship`, `/review`, `/cso`, `/qa` 등) 사용 시 반드시 [policies/gstack-override-policy.md](./policies/gstack-override-policy.md) 참조.
팀 Git 컨벤션·배포 정책이 gstack 기본값보다 우선한다.

## 문서 규칙

- 한국어 작성, 코드/기술 용어 영어 허용
- 파일명: `kebab-case.md`
- AGENTS.md 최소화 원칙: [policies/claude-md-policy.md](./policies/claude-md-policy.md) (CLAUDE.md/AGENTS.md 공통 적용)

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- 티켓 생성, YouTrack 티켓 → invoke ad:ticket
- 주간업무 보고, 보고서 → invoke ad:weekly-report
- OKR 조회/작성 → invoke ad:okr
- KB 조회 → invoke ad:team2-kb-read
- 하네스 최적화, 중복 제거 → invoke ad:harness-optimize
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health
