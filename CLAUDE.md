# 개발 2팀 하네스

팀 공통 정책, 스킬, 서비스 카탈로그의 source of truth.
셋업: [docs/setup-guide.md](./docs/setup-guide.md) | 운영: [docs/harness-guide.md](./docs/harness-guide.md)

## 구조

- `policies/` — 팀 정책. 디렉토리가 SoT — `ls policies/`로 조회
- `catalog/` — 서비스 프로파일. 디렉토리가 SoT — `ls catalog/`로 조회
- `catalog/common-services/registry.yaml` — 알라딘 인증, 뉴빌링 등 공통 서비스 영향 확인 registry
- `templates/` — 서비스 하네스 템플릿, PR/DoD 체크리스트, 티켓 템플릿
- `.claude/commands/ad/` — 팀 스킬. 디렉토리가 SoT — `ls .claude/commands/ad/`로 조회
- `scripts/setup.sh` — 원커맨드 셋업
- `docs/` — 가이드 문서
- `docs/sprint/` — 스프린트 운영. 디렉토리가 SoT — `ls docs/sprint/`로 조회

## 핵심 규칙

- 하네스 개선의 방향 판정: [policies/harness-north-star.md](./policies/harness-north-star.md) — 검증 루프 > 지시, 문제 단위 위임, smart zone, 환경=진실, 게이트 기계화, 아티팩트 기억
- 지시 강도(invariant/policy/heuristic/example)·충돌 시 우선순위·판단 경계: [policies/instruction-precedence-policy.md](./policies/instruction-precedence-policy.md)
- 세션 컨텍스트 규율: [memory/claude-base.md](./memory/claude-base.md) §세션 컨텍스트 규율
- 브랜치: `feature/{이슈ID}` | 커밋: `[{이슈ID}] 작업 내용`
- 예외: 개발2팀 하네스(`team2`) 자체 변경은 티켓 없이 `team2/{작업-slug}` 브랜치와 `[TEAM2] 작업 내용` 커밋을 사용할 수 있다
- 모든 작업은 YouTrack 티켓(5W1H)에서 시작. 단, 개발2팀 하네스 자체 변경은 [브랜치 전략](./policies/branching-strategy.md)의 하네스 예외를 따른다
- AI 도구는 YouTrack 티켓/Task 생성, 티켓 상태 변경, 커밋/푸시/머지 전에 반드시 사용자에게 확인한다. 하네스 예외 작업은 DEV2 티켓 없이도 사용자 명시 지시로 commit/merge/push 가능하다
- YouTrack KB 생성/수정/삭제/이동은 반드시 사용자 확인 후 수행한다
- 용어: "위키"는 로컬 Obsidian vault만 뜻하고, YouTrack Articles는 "지식베이스(KB)" 또는 "기술자료"라고 부른다. "위키에 저장" 요청은 로컬 위키 저장으로 해석한다
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

gstack 스킬 사용 시 [policies/gstack-override-policy.md](./policies/gstack-override-policy.md) 참조 — 팀 Git 컨벤션·배포 정책이 gstack 기본값보다 우선한다. 실사용 유지분은 [docs/gstack-usage-guide.md](./docs/gstack-usage-guide.md).

superpowers는 제거됐다(2026-08-08) — mattpocock이 대체: `brainstorming`→`/ad:grill`, `systematic-debugging`→`diagnosing-bugs`, `executing-plans`·`tdd`→`/ad:implement`+`tdd`. 판정: [policies/overrides/mattpocock.md](./policies/overrides/mattpocock.md).

## 문서 규칙

- 한국어 작성 (코드/기술 용어 영어 허용), 파일명 `kebab-case.md`
- 문서 H1/title 규칙: [policies/wiki-document-language-and-title-policy.md](./policies/wiki-document-language-and-title-policy.md)
- CLAUDE.md 최소화 원칙: [policies/claude-md-policy.md](./policies/claude-md-policy.md)
- 분석/평가 가이드 (Ralph Loop, 레거시 현대화, DB 이관, 운영 위키 탐색 등): [docs/analysis-guides.md](./docs/analysis-guides.md)

## 스킬 호출

`/ad:*`는 **모델 호출**이다 — 요청이 스킬에 맞으면 다른 도구보다 먼저 호출한다. 판단 근거는 각 스킬의 `description`이며, CLAUDE.md에 라우팅 목록을 따로 두지 않는다. 같은 일을 두 곳에서 하면 한쪽이 반드시 낡는다.

**사용자 호출 전용 6종** — `/ad:code-review`, `/ad:work-board`, `/ad:tldr`, `/ad:explain`, `/ad:implement`, `/ad:plan-run`. 게시·dispatch·구현 같은 사이드이펙트가 있어 사람이 시점을 정한다.

어떤 스킬을 언제 부르는지의 지도는 [docs/harness-guide.md](./docs/harness-guide.md) §작업 플로우. 트리거 설계 기준은 [policies/skill-authoring-principles.md](./policies/skill-authoring-principles.md) §1.

모델이 스스로 적용하는 규칙(스킬 아님):

- 새 문서 작성, 어디에 둘지 결정 → [policies/knowledge-base-policy.md](./policies/knowledge-base-policy.md) 결정 트리 즉시 적용 (사용자에게 매번 묻지 않음)

## GBrain

설정·검색 가이드: [docs/gbrain-config.md](./docs/gbrain-config.md)
