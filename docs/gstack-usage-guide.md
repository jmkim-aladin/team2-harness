# gstack 사용 가이드

## 개요

gstack은 Claude Code용 오픈소스 스킬 프레임워크로, Think → Plan → Build → Review → Test → Ship → Reflect 전체 개발 라이프사이클을 커버한다.
팀 정책 오버라이드: [policies/gstack-override-policy.md](../policies/gstack-override-policy.md)

## 라이프사이클

```
Think    /office-hours → /plan-ceo-review
Plan     /plan-eng-review → /design-consultation → /design-shotgun → /design-review
Build    구현
Review   /review → /cso → /codex → /careful → /freeze → /investigate
Test     /qa → /qa-only → /benchmark → /browse
Ship     /ship → /land-and-deploy → /canary
Reflect  /document-release → /retro
```

## 스킬 상세

### Think — 기획 검증

| 스킬 | 용도 | 예시 |
|---|---|---|
| `/office-hours` | 6가지 강제 질문으로 가정 검증 | "MAX SP 중 어떤 것부터 Kotlin 전환?" |
| `/plan-ceo-review` | 스코프 검증 (확장/유지/축소) | "NARU SSO에 LG LifeCare 추가, 스코프 적정한가?" |

### Plan — 설계 검증

| 스킬 | 용도 | 예시 |
|---|---|---|
| `/plan-eng-review` | 데이터 플로우 매핑, 엣지 케이스 식별 | "BAZAAR eBay 연동 API 아키텍처 검증" |
| `/design-consultation` | 디자인 시스템 생성, 리서치~목업 | "AASM 파일 매니저 UI 설계" |
| `/design-shotgun` | 다수 디자인 변형 탐색 | "AASM 배포 큐 대시보드 레이아웃 3가지 안" |
| `/design-review` | 디자인 감사 + 자동 수정 | "MAX CMS 프론트 접근성 점검" |

### Review — 코드 품질 + 보안

| 스킬 | 용도 | 예시 |
|---|---|---|
| `/review` | Staff Engineer 관점 코드 리뷰, 자동 수정 | "NARU account-api PR 리뷰" |
| `/cso` | OWASP Top 10 + STRIDE 위협 모델링 | "NARU JWT/KMS 보안 감사" |
| `/codex` | 크로스 모델(OpenAI) 세컨드 오피니언 | "BAZAAR Outbox 패턴 구현 검증" |
| `/careful` | 위험 명령 경고 (rm -rf, DROP TABLE 등) | 레거시 DB 작업 시 안전장치 |
| `/freeze` | 디버깅 중 수정 범위 제한 | "MAX SP 디버깅 시 다른 파일 수정 방지" |
| `/investigate` | 체계적 근본 원인 분석 | "TOBE SSR 렌더링 간헐적 실패 원인" |

### Test — QA

| 스킬 | 용도 | 예시 |
|---|---|---|
| `/qa` | 실제 Chromium 브라우저 테스트 + 버그 수정 + 리그레션 테스트 생성 | "MAX 구독 결제 플로우 E2E 테스트" |
| `/qa-only` | 버그 리포트만 (코드 수정 없음) | "TOBE 에디터 폼 검증 버그 목록화" |
| `/benchmark` | Core Web Vitals 성능 비교 | "AASM 대시보드 LCP/CLS 측정" |
| `/browse` | 실제 Chromium으로 페이지 탐색/스크린샷 | "BAZAAR 관리자 페이지 상태 확인" |

### Ship — PR 생성 + 배포

| 스킬 | 용도 | 팀 오버라이드 |
|---|---|---|
| `/ship` | 테스트 → bisected commit → PR 생성 | 커밋: `[이슈ID] 내용`, PR: `[이슈ID] 요약`, Co-Authored-By 제거 |
| `/land-and-deploy` | merge → CI 검증 → 배포 | **merge까지만** 수행, 프로덕션 배포는 사람 승인 |
| `/canary` | 배포 후 콘솔 에러/성능 모니터링 | staging 검증에 활용 |

### Reflect — 문서 + 회고

| 스킬 | 용도 | 예시 |
|---|---|---|
| `/document-release` | 변경 코드 기반 문서 자동 갱신 | "README, API 문서, CHANGELOG 동기화" |
| `/retro` | 주간/스프린트 회고, 팀원별 기여 분석 | "이번 스프린트 서비스별 변경 분석" |

## 서비스별 추천 조합

| 서비스 | 핵심 스킬 | 이유 |
|---|---|---|
| **MAX** (레거시 현대화) | `/plan-eng-review` → `/review` → `/cso` → `/qa` | SP 410개, .NET→Kotlin 전환 아키텍처 검증 + 보안 + 동작 동일성 테스트 |
| **TOBE** (레거시 유지보수) | `/investigate` → `/careful` → `/qa-only` | 공유 DB 5개, SP 200개 안전 디버깅 + 버그 리포트 |
| **NARU** (SSO) | `/cso` → `/review` → `/benchmark` | 인증 서비스 보안 최우선, WebFlux 성능 측정 |
| **BAZAAR** (마켓플레이스) | `/review` → `/qa` → `/canary` | 벤더 연동 E2E 테스트 + 배포 모니터링 |
| **AASM** (파일관리) | `/design-consultation` → `/qa` → `/ship` | UI 중심 디자인 → 테스트 → PR |

## 팀 오버라이드 요약

| 항목 | gstack 기본 | 팀 규칙 |
|---|---|---|
| 커밋 메시지 | `feat: summary` | `[이슈ID] 작업 내용` |
| Co-Authored-By | 삽입 | 금지 |
| PR 타이틀 | `feat: summary` | `[이슈ID] 작업 요약` |
| 프로덕션 배포 | 자동 | 사람 승인 필수 |
| 보안 점검 | OWASP + STRIDE | + AWS Secrets 네이밍, SP 직접 호출 금지 |

## 설치 및 관리

- 설치 경로: `~/.claude/skills/gstack/`
- 업그레이드: `/gstack-upgrade`
- 오버라이드 정책: [policies/gstack-override-policy.md](../policies/gstack-override-policy.md)
