# 개발 2팀 하네스

팀 공통 정책, 스킬, 서비스 카탈로그의 source of truth.
셋업: [docs/setup-guide.md](./docs/setup-guide.md) | 운영: [docs/harness-guide.md](./docs/harness-guide.md)

## 구조

- `policies/` — 팀 정책 (엔지니어링, 브랜치, 코드리뷰, 배포, AI, 현대화, 보안, 장애대응, 팀원, KB, CLAUDE.md, gstack 오버라이드, mermaid, AWS Secrets, 로컬 자격증명/Keychain, Datadog API, DB 이관/CDC, 내부통신 도메인, 위키 문서 언어/제목, 데이터 추출 요청, 스킬 작성, 지시 강도·우선순위, 하네스 거버넌스)
- `catalog/` — 서비스 프로파일 (max, tobe, naru, bazaar, aasm, storefront, caravan, pod, shopping, blog)
- `catalog/common-services/registry.yaml` — 알라딘 인증, 뉴빌링 등 공통 서비스 영향 확인 registry
- `templates/` — 서비스 하네스 템플릿, PR/DoD 체크리스트, 티켓 템플릿
- `.claude/commands/ad/` — 팀 스킬 (ticket, work-prep, work-close, work-board, code-review, architecture-analysis, team2-kb-read, okr, weekly-report, weekly-planned, harness-optimize, data-request, sprint-close-check, service-activity, capacity-plan, granola-sync, new-note, tldr, explain, orchestration)
- `scripts/setup.sh` — 원커맨드 셋업
- `docs/` — 가이드 문서
- `docs/sprint/` — 스프린트 운영 (워크플로우 실행, 티켓 가이드, SP 가이드, 계획 변경, Velocity, 마감 프로세스, 주간업무 보고, 주간 핵심 목표)

## 핵심 규칙

- 지시 강도(invariant/policy/heuristic/example)·충돌 시 우선순위·판단 경계: [policies/instruction-precedence-policy.md](./policies/instruction-precedence-policy.md)
- 세션 컨텍스트는 **smart zone**(약 150k 토큰) 안에 둔다: 각 구현 앞에서 `/clear` / 파일은 Read로 읽고 `cat`·`sed`로 출력하지 않는다 / 셸 cwd는 호출마다 초기화되므로 절대 경로로 명령한다 / 넓은 조사는 서브에이전트로 보내고 결론만 회수한다. 근거: 2026-08-08 실측 호출당 평균 컨텍스트 470k (zone의 3배)
- 브랜치: `feature/{이슈ID}` | 커밋: `[{이슈ID}] 작업 내용`
- 예외: 개발2팀 하네스(`team2`) 자체 변경은 티켓 없이 `team2/{작업-slug}` 브랜치와 `[TEAM2] 작업 내용` 커밋을 사용할 수 있다
- 모든 작업은 YouTrack 티켓(5W1H)에서 시작. 단, 개발2팀 하네스 자체 변경은 [브랜치 전략](./policies/branching-strategy.md)의 하네스 예외를 따른다
- AI 도구는 YouTrack 티켓/Task 생성, 티켓 상태 변경, 커밋/푸시/머지 전에 반드시 사용자에게 확인한다. 하네스 예외 작업은 DEV2 티켓 없이도 사용자 명시 지시로 commit/merge/push 가능하다
- YouTrack KB 생성/수정/삭제/이동은 반드시 사용자 확인 후 수행한다
- 지식 분리: 팀 하네스(repo) = "어떻게 일하나"(정책·템플릿·카탈로그·스킬), Obsidian vault = "무엇을 일하나"(프로젝트 진행·운영·도메인·회의·일지·OKR·티켓 산출물). 결정 트리는 [policies/knowledge-base-policy.md](./policies/knowledge-base-policy.md) 참조
- 공통 서비스 영향: 로그인/권한/회원 식별/결제/정산/구독/공유 API가 걸리면 [policies/common-service-policy.md](./policies/common-service-policy.md)와 [catalog/common-services/registry.yaml](./catalog/common-services/registry.yaml)을 함께 확인
- 신규 빌링, 결제, 정산, 구독, 빌링키 기능은 [catalog/common-services/new-billing.yaml](./catalog/common-services/new-billing.yaml)의 뉴빌링 API 경계를 먼저 확인한다. 현재 팀 서비스 active 연동은 없는 상태로 기록한다.
- Feature ≤ 1주 (필수) / Task ≤ 1일 (필수) — 초과 시 분할. 상세: [docs/sprint/ticket-guide.md](./docs/sprint/ticket-guide.md)
- Feature 하위 Task는 개발 / 검증 / 배포·운영 반영으로 분리 — 판정 필수, 해당 시 별도 Task, 해당 없으면 Feature 본문에 사유 기재. 검증은 테스트(내부) / QA(시너지팀) / 테스트→QA 중 선택. 상세: [docs/sprint/ticket-guide.md](./docs/sprint/ticket-guide.md) 2-2항
- DB/SP 변경 별도 승인, 프로덕션 배포 사람 승인
- 신규 백엔드 Kotlin + Spring Boot, 신규 .NET 금지, SP 직접 호출 금지
- 신규 앱 도메인: 내부 `{app}.internal.{service}[.{env}].aladin.co.kr` (Internal ALB) / 외부 `api.{service}[.{env}].aladin.co.kr/{app}` (API G/W, path strip). 앱 base-path·절대 URL·쿠키 인증 금지. 상세: [policies/internal-domain-policy.md](./policies/internal-domain-policy.md)
- 운영 데이터 추출 SQL은 [`AladinCommunication/data-requests-dev2`](https://github.com/AladinCommunication/data-requests-dev2)에서 관리 (하네스 `docs/`에 신규 작성 금지). 상세: [policies/data-request-policy.md](./policies/data-request-policy.md)

## 서비스

| 서비스 | 유형 | 프로파일 |
|--------|------|----------|
| max (만권당) | legacy | [catalog/max.yaml](./catalog/max.yaml) |
| tobe (투비컨티뉴드) | legacy | [catalog/tobe.yaml](./catalog/tobe.yaml) |
| naru | new | [catalog/naru.yaml](./catalog/naru.yaml) |
| bazaar | new | [catalog/bazaar.yaml](./catalog/bazaar.yaml) |
| aasm | new | [catalog/aasm.yaml](./catalog/aasm.yaml) |
| storefront (스토어프론트) | new (설계 중) | [catalog/storefront.yaml](./catalog/storefront.yaml) |
| caravan (가상 대기열) | new | [catalog/caravan.yaml](./catalog/caravan.yaml) |
| pod | new | [catalog/pod.yaml](./catalog/pod.yaml) |
| shopping (알라딘 쇼핑) | legacy | [catalog/shopping.yaml](./catalog/shopping.yaml) |
| blog (블로그/북플) | legacy | [catalog/blog.yaml](./catalog/blog.yaml) |
| attendance (근태관리) | new | [catalog/attendance.yaml](./catalog/attendance.yaml) |

## 외부 스킬

gstack 스킬(`/ship`, `/review`, `/qa`, `/investigate`, `/plan-eng-review`, `/plan-ceo-review`, `/codex`, `/browse`, `/context-save`, `/context-restore`, `/document-generate`) 사용 시 [policies/gstack-override-policy.md](./policies/gstack-override-policy.md) 참조 — 팀 Git 컨벤션·배포 정책이 gstack 기본값보다 우선한다.

superpowers는 `brainstorming`·`systematic-debugging`·`executing-plans` 3종만 사용한다. 나머지 외부 스킬(GSD 18종, ios-*, design-*, health, retro, office-hours 등)은 2026-08-08 실사용 실측으로 비활성 판정 — 근거는 [docs/skill-stack-and-workflow-plan.md](./docs/skill-stack-and-workflow-plan.md) §4.

## 문서 규칙

- 한국어 작성 (코드/기술 용어 영어 허용), 파일명 `kebab-case.md`
- 문서 H1/title 규칙: [policies/wiki-document-language-and-title-policy.md](./policies/wiki-document-language-and-title-policy.md)
- CLAUDE.md 최소화 원칙: [policies/claude-md-policy.md](./policies/claude-md-policy.md)
- 분석/평가 가이드 (Ralph Loop, 레거시 현대화, DB 이관, 운영 위키 탐색 등): [docs/analysis-guides.md](./docs/analysis-guides.md)

## 스킬 호출

`/ad:*`는 **모델 호출**이다 — 요청이 스킬에 맞으면 다른 도구보다 먼저 호출한다. 판단 근거는 각 스킬의 `description`이며, CLAUDE.md에 라우팅 목록을 따로 두지 않는다. 같은 일을 두 곳에서 하면 한쪽이 반드시 낡는다.

**사용자 호출 전용 4종** — `/ad:code-review`, `/ad:work-board`, `/ad:tldr`, `/ad:explain`. 게시·dispatch 같은 사이드이펙트가 있어 사람이 시점을 정한다.

어떤 스킬을 언제 부르는지의 지도는 [docs/harness-guide.md](./docs/harness-guide.md) §작업 플로우. 트리거 설계 기준은 [policies/skill-authoring-principles.md](./policies/skill-authoring-principles.md) §1.

모델이 스스로 적용하는 규칙(스킬 아님):

- 새 문서 작성, 어디에 둘지 결정 → [policies/knowledge-base-policy.md](./policies/knowledge-base-policy.md) 결정 트리 즉시 적용 (사용자에게 매번 묻지 않음)

## GBrain Configuration (configured by /setup-gbrain)

- Mode: remote-http shared team2 brain
- Local agent MCP URL: `http://127.0.0.1:3131/mcp`
- Hermes MCP URL: `http://gbrain-team2:3131/mcp`
- Server: Docker service `gbrain-team2` in `/Users/jm/.hermes-team2/docker-compose.yml`
- Engine: pglite at `/Users/jm/.hermes-team2/.gbrain/brain.pglite` (container path: `/opt/data/.gbrain/brain.pglite`)
- Setup date: 2026-06-17
- MCP registered: Hermes `cli`/`discord`, Codex global, Claude Code user scope
- Token storage: `/Users/jm/.hermes-team2/.env` and local agent config only. Do not commit tokens.
- Indexed sources: `team2-harness`, `team2-vault`; code files are indexed under `team2-harness`.
- Default source scope: Docker runtime sets `GBRAIN_SOURCE=team2-vault`; use explicit source selection for `team2-harness` when needed.
- Embeddings: enabled with ZeroEntropy `zembed-1`; run shared maintenance from the Docker service, not the Mac-local `~/.gbrain` PGLite.
- Hermes runtime: cron runs `tools/run_team2_knowledge_cycle.py`; Granola meeting sync runs every 10m through `tools/run_granola_sync_cycle.py`; nightly agent jobs use GBrain MCP for domain hardening drafts. Hermes may write vault draft/projection files but must not mutate YouTrack/KB/DB/prod or promote canonical state without approval.
- GBrain PGLite maintenance: host LaunchAgent `com.team2.gbrain-maintenance` runs `/Users/jm/.hermes-team2/scripts/gbrain-maintenance.sh` at 01:40 KST. This stops `gbrain-team2`, runs `sync --all`, a forced `sync --source team2-vault --full`, `extract --stale`, `embed --stale`, source-level `dream`, writes `/Users/jm/.hermes-team2/gbrain-maintenance-status.json`, then restarts the server. Read status with `/Users/jm/.hermes-team2/scripts/gbrain-maintenance.sh --status`; it must not run maintenance.

## GBrain Search Guidance (configured by /sync-gbrain)
<!-- gstack-gbrain-search-guidance:start -->

GBrain is available through the shared team2 HTTP MCP. The agent should prefer gbrain over Grep when the question is semantic, cross-document, or when the exact identifier is unknown.

Current indexed corpora:
- DEV2 harness markdown, policies, command documentation, and code files.
- Local Obsidian team2 vault notes for tickets, analyses, meetings, and domain knowledge.

Prefer gbrain when:
- "Where is X handled?" or intent-based lookup: use MCP `search` or `query`.
- "Where is symbol Y defined?" or "Who references Y?": use MCP `code_def` or `code_refs`.
- "What calls Y?" / "What does Y depend on?": use MCP `code_callers` / `code_callees`.
- "What did we decide about X?": use MCP `search` or `think`, then verify against source documents.

Grep is still right for exact strings, regex, multiline patterns, and file globs. gbrain results are retrieval candidates, not confirmed source of truth. For shared brain CLI maintenance, run commands inside the Docker service, for example `docker exec gbrain-team2 sh -lc 'HOME=/opt/data /opt/data/.local/bin/gbrain stats'`.

<!-- gstack-gbrain-search-guidance:end -->
