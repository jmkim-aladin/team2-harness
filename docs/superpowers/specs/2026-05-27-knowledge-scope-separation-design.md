# 지식 저장소 범위 분리 설계 (팀 하네스 vs 로컬 위키)

## 배경 및 문제

현재 팀 지식은 다음 저장소에 분산되어 있다.

- **team2 repo (git)** — 정책·템플릿·카탈로그·스킬, repo 내부 `wiki/` 일부 운영 인벤토리
- **YouTrack KB** — 사내·팀 공통 컨벤션·온보딩·회의록
- **Obsidian vault (`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/`)** — 주간 초안, daily, decisions, domains, graph, registry 등
- **data-requests-dev2 repo** — 운영 데이터 추출 SQL/산출물
- **각 서비스 repo** — 코드 강결합 매뉴얼

문제:

1. `policies/knowledge-base-policy.md`는 repo 내부 `team2/wiki/`를 "운영업무 지식·도메인 지식 SSOT"로 정의했으나, 실제 운영업무·도메인 지식 작성은 Obsidian vault에 누적되고 있어 정책-실태 불일치.
2. repo `wiki/contracts/`와 vault `wiki/contracts/`가 동시에 존재하여 SSOT 모호.
3. 새 문서를 만들 때마다 위치 판단이 매번 반복됨. 결정 규칙이 명문화되어 있지 않음.
4. 한쪽이 갱신돼도 다른 쪽에 드리프트가 쌓일 위험.

## 정의

- **팀 하네스 (team2 repo)** = "어떻게 일하나" — 팀 업무 가이드·규칙·구조 (정책, 템플릿, 카탈로그, 스킬, KB↔하네스 매핑 인덱스)
- **Obsidian vault** = "무엇을 일하나" — 팀 업무 실행·운영·도메인 지식 (프로젝트 진행, 운영업무, 도메인, 회의록, 일지, 주간보고, Querybook 산출물, 외부 research 인입)

이 정의가 모든 결정의 1차 기준이다.

## SSOT 매트릭스

| 저장소 | 정체성 | 담는 것 | SSOT 범위 |
|---|---|---|---|
| **team2 repo (git)** | "어떻게 일하나" | 정책, 템플릿, 카탈로그, 스킬, KB 단방향 참조 인덱스 | 팀 정책·템플릿·서비스 카탈로그·KB↔하네스 매핑 |
| **YouTrack KB** | 사내·팀 공통 지식 단방향 원천 | 전사 컨벤션, 사내 공통 가이드, 온보딩 | 전사·사내 공통 컨벤션·가이드·온보딩 |
| **Obsidian vault** | "무엇을 일하나" | daily, weekly, briefs, decisions, domains, graph, registry, glossary, meetings, inventory, contracts, exports | 프로젝트 진행·운영업무·도메인·회의록·일지 |
| **data-requests-dev2 repo** | 운영 데이터 추출 SQL/산출물 | 추출 쿼리, 요청별 결과, 요청 이력 | 데이터 추출 요청 |
| **각 서비스 repo** | 코드 강결합 매뉴얼 | 그 서비스 코드와 묶여야 의미 있는 문서만 | 서비스 코드 매뉴얼 |

핵심 변경:

- repo `wiki/` **폐지** — 두 건의 inventory 파일 vault로 이관 후 디렉터리 삭제
- "운영업무 지식 SSOT = repo `team2/wiki/`" 표현 전면 삭제 → Obsidian vault
- 회의록 위치 = **Obsidian vault `wiki/meetings/`** (KB 아님)

## 결정 트리 (새 문서 어디에 둘지)

```
새 문서 작성 필요
  │
  ├─ 팀 정책·규칙·템플릿·카탈로그·스킬?
  │     → team2 repo (policies/ templates/ catalog/ .claude/commands/ad/)
  │
  ├─ 전사·사내 공통 컨벤션/온보딩/가이드?
  │     → YouTrack KB
  │
  ├─ 운영 데이터 추출 SQL/결과물?
  │     → data-requests-dev2 repo
  │
  ├─ 특정 서비스 코드 안에서만 의미 있는 매뉴얼?
  │     → 그 서비스 repo
  │       (예: 서비스 README·빌드/실행, .env.example, local dev 셋업,
  │            그 서비스 전용 migration runbook, 그 서비스 전용 ADR)
  │
  └─ 그 외 전부 (프로젝트 진행·운영·도메인·분석·회의·일지·주간보고·Querybook)
        → Obsidian vault
```

판단 모호 시 기본값 = **Obsidian vault**.

핵심 경계 시그널:

| 시그널 | 위치 |
|---|---|
| "이렇게 일하자" (규칙·합의) | repo |
| "이게 우리 업무다" (실행·내용) | Obsidian vault |
| "이건 사내 공통 원천이다" | KB (참조 인덱스만 repo) |
| "repo 클론 안 하면 쓸모없다" | 그 서비스 repo |

## 이관 절차

스코프 = repo 내 vault 성격 문서 일괄 이관, vault 내부 재배치는 차후 별도 작업.

### vault 이관 대상 (분류)

**repo `wiki/`**
- `wiki/inventory/aladin-infra-login-history.md` → vault `wiki/inventory/`
- `wiki/inventory/max-search-batch-sql.md` → vault `wiki/inventory/`

**`docs/` 루트의 티켓 산출물 (DEV2-*)** — 특정 티켓의 운영 분석/추출 결과
- `docs/DEV2-5283-subtask-updates-0420.md`
- `docs/DEV2-5544-audiobook-runtime-query.md`
- `docs/DEV2-5749-multicampus-srv1119-april-order-export.md`

**`docs/` 도메인 가이드** — 서비스 도메인 지식
- `docs/shopping-order-domain-guide.md`
- `docs/shopping-packman-domain-guide.md`

**`docs/` 운영 신청·운영 산출물**
- `docs/max-api-core-dev-firewall-application.md`

**`docs/designs/` 전체** — 신규 서비스 설계 진행 산출물 ("무엇을 일하나")
- `docs/designs/storefront/` (전체)
- `docs/designs/hybrid-db-service-layer-process.md`
- `docs/designs/operational-knowledge-wiki.md`

**`docs/okr/` 전체** — 팀/개인 OKR 본문 ("무엇을 일하나")
- 모든 `2026-q*-*.md`, `2026-team-okr.md`
- `performance-review-guide.md` (OKR 운영 가이드 — 같은 도메인 cohesion으로 동반 이관)

### 제거 대상 (이관 없이 삭제)
- `docs/hiring/` — `.DS_Store` 외 콘텐츠 없음
- `docs/incidents/` — 빈 디렉터리

### repo 잔류 (변동 없음, "어떻게 일하나" = 가이드/process/setup)
- `docs/analysis-guides.md`, `docs/db-migration-cdc-assessment-guide.md`
- `docs/gstack-usage-guide.md`, `docs/harness-guide.md`
- `docs/legacy-modernization-db-separation-analysis-guide.md`
- `docs/ralph-loop-domain-knowledge-guide.md`, `docs/ralph-loop-service-expansion-guide.md`
- `docs/service-harness-setup.md`, `docs/setup-guide.md`
- `docs/team-harness-design.md`, `docs/wiki-navigation-guide.md`
- `docs/sprint/` (운영 가이드 모음)
- `docs/superpowers/` (본 spec 포함, 메타)

### 진행 순서
1. vault 이관 대상 파일·디렉터리 일괄 이동 (`git mv` 사용해 history 보존)
2. 제거 대상 디렉터리 삭제
3. repo `wiki/` 디렉터리 제거 (이관 후 빈 상태)
4. 정책·CLAUDE·docs 일괄 갱신 (다음 절)
5. 이관과 정책 갱신은 **같은 PR**에서 처리하여 링크 깨짐 방지

### vault 위치 매핑 (초안 — 차후 vault 개편 시 재배치)
- 인벤토리·도메인 가이드·운영 신청 → vault `wiki/` 하위 적절 카테고리
- DEV2-* 티켓 산출물 → vault `exports/` 또는 `briefs/` (vault 기존 구조 따라감)
- `docs/designs/` → vault `decisions/` 또는 신규 `designs/`
- `docs/okr/` → vault 신규 `okr/` 또는 `briefs/okr/`

상세 vault 위치는 구현 plan 단계에서 vault 디렉터리 구조 확인 후 결정.

## 지속 기록 메커니즘 (4-layer)

### Layer 1 — 정책 재정의

- `policies/knowledge-base-policy.md` 전면 재작성
  - SSOT 매트릭스 (위 매트릭스 그대로)
  - "어떻게 일하나 vs 무엇을 일하나" 정의 박스
  - 결정 트리
  - 회의록 = vault 명시 (KB 아님)
  - 기존 "운영업무 지식 SSOT = `team2/wiki/`" 표현 전부 제거
- `policies/wiki-document-language-and-title-policy.md` — `team2/wiki/` 언급 있으면 vault 기준으로 갱신
- `policies/claude-md-policy.md` — 영향 시 갱신

### Layer 2 — 양쪽 CLAUDE.md 교차 참조

- repo `CLAUDE.md`
  - "핵심 규칙"의 "가이드/정책/스킬은 팀 하네스에, 도메인 분석 결과/Querybook은 로컬 Obsidian 운영 지식 위키에 저장한다" 문장을 새 정의("어떻게 일하나" vs "무엇을 일하나") 기반으로 재서술
  - Skill routing 표에 "새 문서 작성" 라우팅 규칙 추가
  - 본문에 repo `wiki/` 디렉터리 참조 있으면 제거 (현재 없으나 갱신 후에도 재발 방지)
- vault `CLAUDE.md`
  - "이 vault는 분석/운영 맥락의 source of truth" 줄을 새 정책 source(`repo policies/knowledge-base-policy.md`)와 명시 연결
  - 회의록 위치 = vault `wiki/meetings/` 유지, KB 아님 명확화

### Layer 3 — Skill routing 강화

- repo `CLAUDE.md` Skill routing 표에 추가:
  - 새 문서 작성 요청 → 결정 트리 적용 후 위치 안내 (사용자에게 매번 묻지 않음)
  - 정책/템플릿/카탈로그 성격 → repo
  - 그 외 운영·도메인·회의·일지 → Obsidian vault
- `.claude/commands/ad/work-prep.md` — "문서 위치 결정" 단계 명시
- `.claude/commands/ad/harness-optimize.md` — 드리프트 점검 절차 추가

### Layer 4 — 드리프트 감시

- `ad:harness-optimize` 확장:
  - repo와 vault 교차 점검
  - repo에 운영업무/도메인 문서 발견 시 surface
  - vault에 정책/템플릿 성격 문서 발견 시 surface
  - 중복 제목·중복 내용 감지
- 실행 시점: 주간보고 작성 시 같이 또는 명시적 호출

## 산출물 (구현 작업 목록)

A. 이관
- repo `wiki/inventory/` 2건 → vault
- `docs/DEV2-*.md` 3건 → vault
- `docs/shopping-*-domain-guide.md` 2건 → vault
- `docs/max-api-core-dev-firewall-application.md` → vault
- `docs/designs/` 전체 → vault
- `docs/okr/` 전체 → vault
- repo `wiki/`, `docs/hiring/`, `docs/incidents/` 디렉터리 삭제

B. 정책 갱신 (repo)
- `policies/knowledge-base-policy.md` 전면 재작성
- `policies/wiki-document-language-and-title-policy.md` 영향 부분 갱신
- `policies/claude-md-policy.md` 영향 시 갱신

C. CLAUDE.md 동기화
- repo `CLAUDE.md`: 핵심 규칙 line 24 문장 재서술, Skill routing 표에 "새 문서 작성" 항목 추가
- vault `CLAUDE.md`: 새 정책 source(repo `policies/knowledge-base-policy.md`) 참조 명시, 회의록 위치 명확화

D. 스킬 갱신
- `.claude/commands/ad/work-prep.md` 문서 위치 결정 단계 추가
- `.claude/commands/ad/harness-optimize.md` 드리프트 점검 절차 추가

E. 참조 grep + 일괄 갱신
- repo 전체 grep: `team2/wiki/`, `wiki/inventory`, `wiki/contracts`, 이관 파일명 경로
- 잔류 가이드(`docs/wiki-navigation-guide.md`, `docs/analysis-guides.md`, `docs/ralph-loop-*.md` 등) 본문에서 이관된 파일 링크는 vault 경로 또는 새 정책 링크로 교체
- `policies/data-request-policy.md`에서 DEV2-* 산출물 위치 표현 영향 시 갱신
- `catalog/*.yaml`, `templates/` 에 이관 파일 참조 있으면 갱신

F. memory 갱신
- `reference_obsidian_vault.md` 본문에 "vault = 운영·도메인·회의·일지 SSOT" 확장
- 신규 memory: `feedback_doc_placement.md` — 새 문서 위치 결정 트리 요약

G. 디자인 doc
- 본 문서 자체

## 비범위

- vault 내부 디렉터리 구조 재개편은 별도 작업으로 분리
- repo `wiki/` 외의 기존 문서 이관·정리는 분리
- YouTrack KB 본문 손질·재분류는 분리

## 검증

- repo grep `team2/wiki/` 결과 0건 (의도된 정책 본문 예시 제외)
- repo `wiki/`, `docs/hiring/`, `docs/incidents/` 디렉터리 부재
- `docs/DEV2-*.md`, `docs/designs/`, `docs/okr/`, `docs/shopping-*-domain-guide.md`, `docs/max-api-core-dev-firewall-application.md` 부재
- vault 해당 경로에 이관 파일 존재 + git history 보존 (`git log --follow` 확인)
- repo `CLAUDE.md`, vault `CLAUDE.md` 양쪽 정책 source 일치
- repo 내부 깨진 마크다운 링크 0건 (link checker 또는 grep으로 확인)
- `ad:harness-optimize` 실행 시 repo↔vault 드리프트 0건 또는 surface 목록 출력
