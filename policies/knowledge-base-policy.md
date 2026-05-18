# 지식베이스 관리 정책

## 관리 체계 (SSOT)

| 저장소 | 역할 | SSOT 범위 | 관리 방식 |
|--------|------|-----------|-----------|
| **team2 레포 (git)** | 팀 공통 하네스 — 정책, 템플릿, 카탈로그 | 정책/템플릿/카탈로그 | git + PR 리뷰 |
| **YouTrack KB** | 사내·팀 공통 지식 — 컨벤션, 가이드, 회의록 | 사내·팀 공통 지식 | YouTrack REST API |
| **로컬 위키 (`team2/wiki/`)** | 서비스 코드 내 지식 + 운영업무 지식 | 서비스/운영 도메인 지식 | git + PR 리뷰 (하네스 레포 내) |
| **data-requests-dev2 레포** | 운영 데이터 추출 SQL/산출물 | 추출 쿼리, 요청별 결과물, 요청 이력 | git + 월별 `sprint/YYYY-MM` 브랜치 |
| **각 서비스 레포** | 서비스별 하네스 — 현장 매뉴얼 | 서비스 코드와 강결합된 매뉴얼만 | git + PR 리뷰 |

## SSOT 구분 원칙

| 지식 유형 | SSOT |
|---|---|
| 사내·팀 공통 컨벤션·가이드·회의록·온보딩 | **YouTrack KB** |
| 서비스 코드 내 지식 (SP/Table 인벤토리, 도메인 매핑, 데이터 모델) | **로컬 위키** (`team2/wiki/`) |
| 운영업무 지식 (장애 사례, 정산·이관 진단, 트러블슈팅, Querybook/Graphify 산출물) | **로컬 위키** (`team2/wiki/`) |
| 운영 데이터 추출 SQL/산출물/요청 이력 | **data-requests-dev2 레포** (상세: [data-request-policy.md](./data-request-policy.md)) |
| 팀 정책·템플릿·서비스 카탈로그 | team2 레포 (git) |
| 특정 서비스 코드와만 강결합된 현장 매뉴얼 | 각 서비스 레포 |

**원칙**: 사내·팀 공통 문서는 YouTrack KB, **서비스 코드 지식·운영업무 지식은 로컬 위키(`team2/wiki/`)가 SSOT**. 두 곳에 같은 내용을 복제하지 않으며, 한 쪽이 갱신되면 다른 쪽은 링크만 유지한다.

## 신규 문서 작성 우선순위

새 문서를 어디에 둘지 결정할 때는 다음 순서로 판단한다.

1. **기본은 팀 하네스 (`team2` 레포 git)** — 정책·템플릿·서비스 카탈로그에 해당하면 `policies/`, `templates/`, `catalog/`에 작성한다.
2. **그 다음은 로컬 위키 (`team2/wiki/`)** — 1순위에 해당하지 않는 서비스 코드 지식·운영업무 지식은 모두 로컬 위키에 작성한다.
3. 사내·팀 공통 컨벤션·가이드·온보딩 성격이면 → YouTrack KB.
4. 특정 서비스 코드와 강결합되어 그 레포 밖에서는 무의미한 매뉴얼이면 → 각 서비스 레포.

판단이 모호할 때는 **팀 하네스 → 로컬 위키** 순으로 검토하고, 둘 중 어디에도 자연스럽게 들어가지 않을 때만 KB나 서비스 레포를 고려한다.

## 로컬 위키 작성 원칙

로컬 위키(`team2/wiki/`) 문서는 **사람이 읽고 바로 운영 판단을 내릴 수 있는 형태**가 목적이다. 다음 원칙을 따른다.

- **비즈니스 로직 중심** — 코드·SQL·스키마 세부보다 도메인 의미, 분기 기준, 운영 함정을 먼저 적는다. 코드 레벨 디테일도 중요하지만 그 자체가 결론이 되어서는 안 된다.
- **핵심 개념 우선, 히스토리는 보조** — 현재의 핵심 개념(역할, 관계, 분기 조건, 함정 테이블)을 문서 상단에 정리한다. 발견 경로·변경 이력·작성자 정보는 필요할 때만 하단에 짧게 남긴다.
- **간결성** — 길게 풀어쓰지 않는다. 표·짧은 문장·요점 정리로 구성하고, 전체 쿼리/스크립트는 "활용 예시" 섹션에 모아 둔다.
- **판단 단서 명시** — "왜 이 테이블을 쓰면 안 되는가", "어떤 조건이 케이스를 가르는가"처럼 사람이 의사결정할 때 필요한 근거를 표나 별도 절로 분리한다.
- **재현 가능한 코드는 보조 자료** — SQL/SP/스크립트 전문은 운영 재현용으로 유용하지만, 본문은 그 코드가 무엇을 의미하고 언제 쓰는지 한국어로 먼저 설명한다.

문서 언어·제목 규칙은 [wiki-document-language-and-title-policy.md](./wiki-document-language-and-title-policy.md), 탐색 절차는 [docs/wiki-navigation-guide.md](../docs/wiki-navigation-guide.md) 참조.

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

## git / KB / 로컬 위키 구분 기준

| 항목 | git (하네스 레포 `policies/`) | YouTrack KB | 로컬 위키 (`team2/wiki/`) |
|------|----|----|----|
| 정책/규칙 | O | | |
| 템플릿 | O | | |
| 서비스 카탈로그 | O | | |
| 사내·팀 공통 컨벤션 상세 가이드 | | O | |
| 전사 공통 참조 | | O | |
| 온보딩 문서 | | O | |
| 회의록/결정사항 | | O | |
| 서비스 코드 내 지식 (SP/Table 인벤토리, 도메인 매핑) | | | O |
| 운영업무 지식 (장애·정산·이관·진단·트러블슈팅 사례) | | | O |
| Querybook / Graphify 산출물 | | | O |

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
