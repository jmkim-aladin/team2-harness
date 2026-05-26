# 개발 2팀 하네스

팀 공통 정책, 스킬, 서비스 카탈로그의 source of truth.
셋업: [docs/setup-guide.md](./docs/setup-guide.md) | 운영: [docs/harness-guide.md](./docs/harness-guide.md)

## 구조

- `policies/` — 팀 정책 (엔지니어링, 브랜치, 코드리뷰, 배포, AI, 현대화, 보안, 장애대응, 팀원, KB, CLAUDE.md, gstack 오버라이드, mermaid, AWS Secrets, 로컬 자격증명/Keychain, DB 이관/CDC, 위키 문서 언어/제목, 데이터 추출 요청)
- `catalog/` — 서비스 프로파일 (max, tobe, naru, bazaar, aasm, storefront, caravan, shopping, blog)
- `templates/` — 서비스 하네스 템플릿, PR/DoD 체크리스트, 티켓 템플릿
- `.claude/commands/ad/` — 팀 스킬 (ticket, work-prep, code-review, kb-read, kb-list, kb-sync, okr, weekly-report, weekly-planned, harness-optimize, data-request, sprint-close-check, service-activity, capacity-plan)
- `scripts/setup.sh` — 원커맨드 셋업
- `docs/` — 가이드 문서
- `docs/designs/` — 설계 문서 (스토어프론트 플랫폼 방향, 테넌트 모델, 인증, 스코프 등)
- `docs/sprint/` — 스프린트 운영 (워크플로우 실행, 티켓 가이드, SP 가이드, 계획 변경, Velocity, 마감 프로세스, 주간업무 보고)

## 핵심 규칙

- 브랜치: `feature/{이슈ID}` | 커밋: `[{이슈ID}] 작업 내용`
- 모든 작업은 YouTrack 티켓(5W1H)에서 시작
- AI 도구는 YouTrack 티켓/Task 생성, 티켓 상태 변경, 커밋/푸시/머지 전에 반드시 사용자에게 확인한다
- YouTrack KB 생성/수정/삭제/이동은 반드시 사용자 확인 후 수행한다
- 지식 분리: 팀 하네스(repo) = "어떻게 일하나"(정책·템플릿·카탈로그·스킬), Obsidian vault = "무엇을 일하나"(프로젝트 진행·운영·도메인·회의·일지·OKR·티켓 산출물). 결정 트리는 [policies/knowledge-base-policy.md](./policies/knowledge-base-policy.md) 참조
- Feature ≤ 1주 (필수) / Task ≤ 1일 (필수) — 초과 시 분할. 상세: [docs/sprint/ticket-guide.md](./docs/sprint/ticket-guide.md)
- DB/SP 변경 별도 승인, 프로덕션 배포 사람 승인
- 신규 백엔드 Kotlin + Spring Boot, 신규 .NET 금지, SP 직접 호출 금지
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
| shopping (알라딘 쇼핑) | legacy | [catalog/shopping.yaml](./catalog/shopping.yaml) |
| blog (블로그/북플) | legacy | [catalog/blog.yaml](./catalog/blog.yaml) |

## gstack 스킬

gstack 스킬(`/ship`, `/review`, `/cso`, `/qa` 등) 사용 시 반드시 [policies/gstack-override-policy.md](./policies/gstack-override-policy.md) 참조.
팀 Git 컨벤션·배포 정책이 gstack 기본값보다 우선한다.

## 문서 규칙

- 한국어 작성 (코드/기술 용어 영어 허용), 파일명 `kebab-case.md`
- 문서 H1/title 규칙: [policies/wiki-document-language-and-title-policy.md](./policies/wiki-document-language-and-title-policy.md)
- CLAUDE.md 최소화 원칙: [policies/claude-md-policy.md](./policies/claude-md-policy.md)
- 분석/평가 가이드 (Ralph Loop, 레거시 현대화, DB 이관, 운영 위키 탐색 등): [docs/analysis-guides.md](./docs/analysis-guides.md)

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- 티켓 생성, YouTrack 티켓 → invoke ad:ticket
- 작업 준비, 티켓번호/할일로 위키 노트 + 업무 컨텍스트 묶기 → invoke ad:work-prep
- 주간업무 보고, 보고서 → invoke ad:weekly-report
- 주간 계획 스냅샷, planned 태그 트리, 위키 meetings 저장 → invoke ad:weekly-planned
- 스프린트 마감 자가점검, 미종료/결과물링크/SP/5W1H/OKR 누락 후보 → invoke ad:sprint-close-check
- OKR 조회/작성 → invoke ad:okr
- KB 조회 → invoke ad:team2-kb-read
- 하네스 최적화, 중복 제거 → invoke ad:harness-optimize
- 데이터 추출 요청, SQL 등록, data-requests-dev2 → invoke ad:data-request
- 서비스별 작업 활동 조회, "지난주 max/tobe/shopping 작업" → invoke ad:service-activity
- 다음달 가용 맨데이/velocity, capacity plan, SP 초과 판정 → invoke ad:capacity-plan
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
- Code quality, health check → invoke health
- 새 문서 작성, 어디에 둘지 결정 → [policies/knowledge-base-policy.md](./policies/knowledge-base-policy.md) 결정 트리 즉시 적용 (사용자에게 매번 묻지 않음)
- 드리프트 점검, repo↔vault 경계 위반 → invoke ad:harness-optimize
