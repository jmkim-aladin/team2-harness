# gstack 사용 가이드

## 개요

gstack은 Claude Code용 오픈소스 스킬 프레임워크다. 전체 라이프사이클을 커버하지만 팀은 **실사용이 확인된 스킬만 활성 상태로 둔다** — 미사용 스킬의 description이 상주 컨텍스트를 점유하기 때문이다.

- 활성/비활성 판정 근거: [docs/skill-stack-and-workflow-plan.md](./skill-stack-and-workflow-plan.md) §4
- 팀 정책 오버라이드: [policies/gstack-override-policy.md](../policies/gstack-override-policy.md)
- 팀 업무 플로우에서의 위치: [docs/harness-guide.md](./harness-guide.md) §작업 플로우

## 활성 스킬

2026-08-08 실사용 실측 기준. 비활성 스킬은 `~/.claude/skills-disabled/`에 있고 되돌릴 수 있다.

### 기획·설계 검증

| 스킬 | 용도 | 예시 |
|---|---|---|
| `/plan-ceo-review` | 스코프 검증 (확장/유지/축소) | "NARU SSO에 LG LifeCare 추가, 스코프 적정한가?" |
| `/plan-eng-review` | 데이터 플로우 매핑, 엣지 케이스 식별 | "BAZAAR eBay 연동 API 아키텍처 검증" |

### 리뷰·조사

| 스킬 | 용도 | 예시 |
|---|---|---|
| `/review` | Staff Engineer 관점 코드 리뷰, 자동 수정 | "NARU account-api PR 리뷰" |
| `/codex` | 크로스 모델(OpenAI) 세컨드 오피니언 | "BAZAAR Outbox 패턴 구현 검증" |
| `/investigate` | 체계적 근본 원인 분석 | "TOBE SSR 렌더링 간헐적 실패 원인" |

> 팀 PR 리뷰는 `/ad:code-review`가 우선이다 — 기준축·스펙축 분리와 팀 게시 규격이 들어 있다. gstack `/review`는 팀 저장소 밖이나 브랜치 단위 훑기에 쓴다.

### 테스트

| 스킬 | 용도 | 예시 |
|---|---|---|
| `/qa` | 실제 Chromium 브라우저 테스트 + 버그 수정 + 리그레션 테스트 생성 | "MAX 구독 결제 플로우 E2E 테스트" |
| `/browse` | 실제 Chromium으로 페이지 탐색/스크린샷 | "BAZAAR 관리자 페이지 상태 확인" |

### 배포

| 스킬 | 용도 | 팀 오버라이드 |
|---|---|---|
| `/ship` | 테스트 → 커밋 → PR 생성 | 커밋 `[이슈ID] 내용`, PR `[이슈ID] 요약`, Co-Authored-By 제거 |

### 문서·컨텍스트

| 스킬 | 용도 |
|---|---|
| `/document-generate` | 기능·모듈·프로젝트 문서를 없는 상태에서 생성 |
| `/context-save` · `/context-restore` | 작업 컨텍스트 저장·복원 |

### 인프라

| 스킬 | 용도 |
|---|---|
| `/gstack-upgrade` | gstack 최신화 |
| `/setup-gbrain` · `/sync-gbrain` | gbrain 설치·동기화 |

## 보안 감사

gstack `/cso`(OWASP + STRIDE)는 실사용 0으로 비활성됐다. 보안 점검은 Claude Code 내장 **`/security-review`**(현재 브랜치의 변경분 보안 리뷰)를 사용하고, 팀 추가 기준은 [policies/security-policy.md](../policies/security-policy.md)와 [policies/aws-secrets-convention.md](../policies/aws-secrets-convention.md)를 함께 적용한다.

`/cso` 수준의 위협 모델링이 필요한 작업(신규 인증·결제 경계 설계 등)이 생기면 `~/.claude/skills-disabled/cso`를 되살린다.

## 서비스별 추천 조합

| 서비스 | 핵심 스킬 | 이유 |
|---|---|---|
| **MAX** (레거시 현대화) | `/plan-eng-review` → `/ad:code-review` → `/qa` | .NET→Kotlin 전환 아키텍처 검증 + 동작 동일성 테스트 |
| **TOBE** (레거시 유지보수) | `/investigate` → `/ad:code-review` | 공유 DB 5개, SP 200개 안전 디버깅 |
| **NARU** (SSO) | `/security-review` → `/ad:code-review` | 인증 서비스 보안 최우선 |
| **BAZAAR** (마켓플레이스) | `/ad:code-review` → `/qa` | 벤더 연동 E2E 테스트 |
| **AASM** (파일관리) | `/browse` → `/qa` → `/ship` | UI 확인 → 테스트 → PR |

## 팀 오버라이드 요약

| 항목 | gstack 기본 | 팀 규칙 |
|---|---|---|
| 커밋 메시지 | `feat: summary` | `[이슈ID] 작업 내용` |
| Co-Authored-By | 삽입 | 금지 |
| PR 타이틀 | `feat: summary` | `[이슈ID] 작업 요약` |
| 프로덕션 배포 | 자동 | 사람 승인 필수 |
| 보안 점검 | OWASP + STRIDE | + AWS Secrets 네이밍, SP 직접 호출 금지 |

## 설치 및 관리

- 설치 경로: `~/.claude/skills/`
- 비활성 스킬: `~/.claude/skills-disabled/` — 되살리려면 되돌려 옮긴다
- 업그레이드: `/gstack-upgrade`. **업그레이드가 비활성 스킬을 복구할 수 있으므로** 이후 `/ad:harness-optimize 스택`으로 재확인한다
- 활성 목록 점검: `python3 tools/harness_context_audit.py`
