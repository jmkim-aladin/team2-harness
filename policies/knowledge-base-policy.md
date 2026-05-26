# 지식베이스 관리 정책

## 정의

- **팀 하네스 (team2 repo)** = "어떻게 일하나" — 팀 업무 가이드·규칙·구조 (정책, 템플릿, 카탈로그, 스킬, KB↔하네스 매핑 인덱스)
- **Obsidian vault (`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/`)** = "무엇을 일하나" — 팀 업무 실행·운영·도메인 지식 (프로젝트 진행, 운영업무, 도메인, 회의록, 일지, 주간보고, Querybook 산출물)

이 정의가 모든 위치 결정의 1차 기준이다.

## 관리 체계 (SSOT)

| 저장소 | 정체성 | SSOT 범위 | 관리 방식 |
|--------|------|-----------|-----------|
| **team2 repo (git)** | "어떻게 일하나" | 팀 정책·템플릿·서비스 카탈로그·스킬·KB↔하네스 매핑 | git + PR 리뷰 |
| **YouTrack KB** | 사내·팀 공통 지식 단방향 원천 | 전사·사내 공통 컨벤션·가이드·온보딩 | YouTrack REST API |
| **Obsidian vault** | "무엇을 일하나" | 프로젝트 진행·운영업무·도메인 지식·회의록·일지·주간보고 | git (vault 자체 repo) |
| **data-requests-dev2 repo** | 운영 데이터 추출 SQL/산출물 | 추출 쿼리, 요청별 결과물, 요청 이력 | git + 월별 `sprint/YYYY-MM` 브랜치 |
| **각 서비스 repo** | 코드 강결합 매뉴얼 | 그 서비스 코드와 묶여야 의미 있는 매뉴얼만 | git + PR 리뷰 |

## 신규 문서 위치 결정 트리

새 문서 작성 시 다음 트리로 즉시 결정한다. 매번 사용자에게 묻지 않는다.

```
새 문서 작성 필요
  │
  ├─ 팀 정책·규칙·템플릿·카탈로그·스킬?
  │     → team2 repo (policies/ templates/ catalog/ .claude/commands/ad/)
  │
  ├─ 전사·사내 공통 컨벤션·온보딩·가이드?
  │     → YouTrack KB
  │
  ├─ 운영 데이터 추출 SQL/결과물?
  │     → data-requests-dev2 repo
  │
  ├─ 특정 서비스 코드 안에서만 의미 있는 매뉴얼?
  │     → 그 서비스 repo
  │       (예: 서비스 README·빌드/실행, .env.example, local dev 셋업,
  │            그 서비스 전용 migration runbook·ADR)
  │
  └─ 그 외 전부 (프로젝트 진행·운영·도메인·분석·회의·일지·주간보고·Querybook·티켓 산출물·OKR)
        → Obsidian vault
```

판단 모호 시 기본값 = **Obsidian vault**.

vault **내부** 결정 트리(어느 디렉터리에 둘지)는 vault 측 [`wiki/guides/document-placement.md`](obsidian://open?vault=team2&file=wiki%2Fguides%2Fdocument-placement) 참조. 본 문서가 정의하는 *경계*는 "어느 저장소에 둘지"까지이고, *vault 내부 분류*는 vault 측 가이드가 SoT.

## 핵심 경계 시그널

| 시그널 | 위치 |
|---|---|
| "이렇게 일하자" (규칙·합의·process) | repo |
| "이게 우리 업무다" (실행·내용·진행) | Obsidian vault |
| "이건 사내 공통 원천이다" | KB (참조 인덱스만 repo) |
| "repo 클론 안 하면 쓸모없다" | 그 서비스 repo |
| 특정 티켓 산출물 (DEV2-* 등) | vault |
| 도메인 가이드, 도메인 분석 | vault |
| 회의록 | vault `wiki/meetings/` |
| OKR 본문 | vault `wiki/okr/` |

## YouTrack Knowledge Base 용도

### 전사 공통
- 전사 코딩 컨벤션
- 공통 인프라 가이드
- 공통 보안 정책
- 배포/운영 공통 규칙

### 팀 공통 (개발 2팀)
- 팀 코드 컨벤션
- 기술 스택별 가이드 (Kotlin, .NET, Next.js)
- 리뷰 기준 상세
- 온보딩 가이드

회의록은 KB가 아니라 **vault `wiki/meetings/`**에 둔다.

## YouTrack KB API 접근

```
베이스 URL: https://aladincommunication.youtrack.cloud/api/articles
인증: Authorization: Bearer perm:{토큰}
콘텐츠: Markdown
구조: 부모-자식 아티클 트리
```

| 작업 | 메서드 | 엔드포인트 |
|------|--------|-----------|
| 목록 | GET | `/api/articles?fields=id,idReadable,summary,content&$top=100` |
| 조회 | GET | `/api/articles/{id}?fields=id,idReadable,summary,content,parentArticle(id,summary),childArticles(id,summary)` |
| 생성 | POST | `/api/articles` + `{project, summary, content}` |
| 수정 | POST | `/api/articles/{id}` + `{summary, content}` |
| 하위 문서 | GET | `/api/articles/{id}/childArticles?fields=id,summary` |

### 주의사항
- `fields` 파라미터 필수 — 지정하지 않으면 ID만 반환
- 페이지네이션: `$top` (최대), `$skip` (오프셋), 기본 최대 42건
- 콘텐츠는 Markdown 형식
- 토큰: YouTrack Profile > Account Security > New Token

## 드리프트 감시

repo와 vault의 경계 위반을 정기적으로 점검한다. 절차는 `.claude/commands/ad/harness-optimize.md` 참조.

점검 신호:
- repo `policies/`, `templates/`, `catalog/`, `.claude/`, `docs/sprint/`, `docs/superpowers/`, `docs/` 잔류 가이드 외 위치에 운영업무·도메인·회의·티켓 성격 문서 발견
- vault에 정책·템플릿·카탈로그·스킬 성격 문서 발견
- 양쪽에 동일 제목/내용 중복

## 전사 핵심 KB 문서 참조

팀 하네스 정책과 연결되는 전사 공통 문서.

| KB ID | 제목 | 상위 | 하네스 연결 |
|-------|------|------|-------------|
| `REF-A-625` | Git Flow | Software Development Flow | `policies/branching-strategy.md` |
| `REF-A-1958` | Clean Architecture | Software Development Flow | `policies/engineering-policy.md` |
| `REF-A-3131` | Backend Environment | Clean Architecture | 서비스 카탈로그 (naru, bazaar) |
| `REF-A-3133` | Frontend Environment | Clean Architecture | 서비스 카탈로그 (max-front, maxcms-front) |
| `REF-A-3129` | Modularization | Clean Architecture | |
| `REF-A-3130` | Reactive Programming | Clean Architecture | |
| `REF-A-729` | Encrypt & Decrypt | Software Development Flow | `policies/security-policy.md`, naru KMS |

### 참조 방법

| 작업 | 방법 |
|------|------|
| 브라우저 조회 | `https://aladincommunication.youtrack.cloud/articles/{문서ID}` |
| 스킬로 조회 | `/ad:team2-kb-read {문서ID}` |
| 목록 조회 | `/ad:team2-kb-list` |

### KB 변경 시 하네스 동기화

전사 KB 문서가 업데이트되면 하네스 정책도 갱신이 필요할 수 있다.

1. `/ad:team2-kb-read {문서ID}`로 최신 KB 내용 조회
2. 하네스 정책 파일과 비교하여 차이가 있으면 하네스 갱신
3. PR로 리뷰 후 반영
