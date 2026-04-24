# 개발 2팀 하네스

팀 공통 정책, 스킬, 서비스 카탈로그의 source of truth.
셋업: [docs/setup-guide.md](./docs/setup-guide.md) | 운영: [docs/harness-guide.md](./docs/harness-guide.md)

## 구조

- `policies/` — 팀 정책 (엔지니어링, 브랜치, 코드리뷰, 배포, AI, 현대화, 보안, 장애대응, 팀원, KB, CLAUDE.md, gstack 오버라이드, mermaid)
- `catalog/` — 서비스 프로파일 (max, tobe, naru, bazaar, aasm, b2b-store)
- `templates/` — 서비스 하네스 템플릿, PR/DoD 체크리스트, 티켓 템플릿
- `.claude/commands/ad/` — 팀 스킬 (ticket, code-review, kb-read, kb-list, kb-sync, okr, weekly-report, harness-optimize)
- `scripts/setup.sh` — 원커맨드 셋업
- `docs/` — 가이드 문서
- `docs/designs/` — 설계 문서 (스토어프론트 플랫폼 방향, 테넌트 모델, 인증, 스코프 등)
- `docs/okr/` — OKR 문서 (연간, 분기별 팀/개인)
- `docs/sprint/` — 스프린트 운영 (워크플로우 실행, 티켓 가이드, SP 가이드, 계획 변경, 주간업무 보고)

## 핵심 규칙

- 브랜치: `feature/{이슈ID}` | 커밋: `[{이슈ID}] 작업 내용`
- 모든 작업은 YouTrack 티켓(5W1H)에서 시작
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
| storefront (스토어프론트) | new (설계 중) | [catalog/b2b-store.yaml](./catalog/b2b-store.yaml) |

## gstack 스킬

gstack 스킬(`/ship`, `/review`, `/cso`, `/qa` 등) 사용 시 반드시 [policies/gstack-override-policy.md](./policies/gstack-override-policy.md) 참조.
팀 Git 컨벤션·배포 정책이 gstack 기본값보다 우선한다.

## 문서 규칙

- 한국어 작성, 코드/기술 용어 영어 허용
- 파일명: `kebab-case.md`
- CLAUDE.md 최소화 원칙: [policies/claude-md-policy.md](./policies/claude-md-policy.md)

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
