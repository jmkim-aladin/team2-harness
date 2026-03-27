# 지식베이스 관리 정책

## 관리 체계

| 저장소 | 역할 | 관리 방식 |
|--------|------|-----------|
| **team2 레포 (git)** | 팀 공통 하네스 — 정책, 템플릿, 카탈로그 | git + PR 리뷰 |
| **YouTrack KB** | 전사 공통 + 팀 컨벤션 — 조회/참조용 | YouTrack REST API |
| **각 서비스 레포** | 서비스별 하네스 — 현장 매뉴얼 | git + PR 리뷰 |

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
- 트러블슈팅 사례
- 온보딩 가이드

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

## git vs KB 구분 기준

| 항목 | git (하네스 레포) | YouTrack KB |
|------|-------------------|-------------|
| 정책/규칙 | O | |
| 템플릿 | O | |
| 서비스 카탈로그 | O | |
| 컨벤션 상세 가이드 | | O |
| 트러블슈팅 사례 | | O |
| 온보딩 문서 | | O |
| 전사 공통 참조 | | O |
| 회의록/결정사항 | | O |

## 전사 핵심 KB 문서 참조

팀 하네스 정책과 연결되는 전사 공통 문서입니다.

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

전사 KB 문서가 업데이트되면 하네스 정책도 갱신이 필요할 수 있습니다.

1. `/ad:team2-kb-read {문서ID}`로 최신 KB 내용 조회
2. 하네스 정책 파일과 비교하여 차이가 있으면 하네스 갱신
3. PR로 리뷰 후 반영
