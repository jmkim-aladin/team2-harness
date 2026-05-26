# vault 택소노미 정의 (Sub 1) 구현 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** spec `2026-05-27-vault-taxonomy-design.md`에 정의된 5개 guides 문서를 vault에 작성하고, vault `_index.md` / vault `CLAUDE.md` / harness `policies/knowledge-base-policy.md`를 cross-link로 일관화한다. 마이그레이션은 없음 — *구조·표준 명세만*.

**Architecture:** vault `wiki/guides/` 신규 5개 markdown 문서 + 기존 3개 entry 파일 갱신. vault는 별도 git repo(`~/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2`), harness는 `/Users/jm/Documents/workspace/team2`. 양쪽 별도 commit. 모든 commit은 사용자 승인 게이트.

**Tech Stack:** Markdown only. 검증 = grep, link check (수동 또는 vault `scripts/lint_wiki.py`).

**경로 약어:**
- `REPO` = `/Users/jm/Documents/workspace/team2`
- `VAULT` = `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2`

**규칙:**
- 코드/문서 변경은 진행해도, 모든 `git commit`은 사용자 승인 후
- 커밋 메시지에 `Co-Authored-By: Claude ...` 또는 `🤖 Generated with Claude Code` 푸터 금지
- vault commit과 harness commit은 분리
- 현재 harness branch = `feature/knowledge-scope-separation`. vault branch 점검은 Task 0.1에서

---

## File Structure

### 신규 (vault)
- `VAULT/wiki/guides/taxonomy.md` — top-level 디렉터리·서비스 표준·폐지 대상
- `VAULT/wiki/guides/frontmatter-spec.md` — 티켓·서비스·도메인 frontmatter 스키마
- `VAULT/wiki/guides/document-placement.md` — 결정 트리, 시그널 매트릭스, harness cross-link
- `VAULT/wiki/guides/skills-integration.md` — 스킬-vault 경로 매핑, chain
- `VAULT/wiki/guides/harness-link-protocol.md` — generated block 규칙, sync 인터페이스

### 갱신 (vault)
- `VAULT/wiki/_index.md` — 새 top-level 진입점 반영, guides 5건 링크
- `VAULT/CLAUDE.md` — 새 구조 요약, generated block 룰 추가

### 갱신 (harness)
- `REPO/policies/knowledge-base-policy.md` — vault 내부 택소노미 cross-link

### 마이그레이션 (없음)
실제 파일 이동은 Sub 2~3에서. 이 Plan은 구조·표준 문서만 작성.

---

## Phase 0: 사전 점검

### Task 0.1: vault 상태 확인

**Files:** N/A

- [ ] **Step 1: vault 상태 확인**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git status --short | head -10
git branch --show-current
```

Expected: vault가 git repo이며 branch 확인 (보통 main 또는 master). vault는 user 일상 작업 공간이므로 작업 브랜치를 만들지 않고 현재 branch에 직접 작성한다. untracked/M 파일이 있어도 본 Plan은 신규 파일 + 명시 파일만 stage하므로 영향 없음.

- [ ] **Step 2: harness branch 확인**

```bash
cd /Users/jm/Documents/workspace/team2
git branch --show-current
```

Expected: `feature/knowledge-scope-separation` (Sub 0/이전 Plan에서 만든 브랜치). 이 branch에 harness 변경분 누적.

### Task 0.2: 작성할 디렉터리 존재 확인

- [ ] **Step 1: vault guides 디렉터리 확인**

```bash
ls "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/guides" | head -3
```

Expected: 디렉터리 존재 (183건 기존 파일). 신규 5건은 이 디렉터리에 추가.

---

## Phase 1: vault guides 5건 작성

### Task 1.1: `taxonomy.md` 작성

**Files:**
- Create: `VAULT/wiki/guides/taxonomy.md`

- [ ] **Step 1: 파일 작성**

다음 내용으로 `VAULT/wiki/guides/taxonomy.md` 생성 (Write 도구):

````markdown
---
type: guide
title: vault 택소노미
canonical_id: guide:taxonomy
status: canonical
updated_at: 2026-05-27
---

# vault 택소노미

DEV2 운영 지식 위키의 디렉터리 구조·책임·SSOT를 정의한다. 본 문서는 vault 내부 구조의 단일 출처(source of truth)이다. harness 측 source는 [team2 repo `policies/knowledge-base-policy.md`](file://Users/jm/Documents/workspace/team2/policies/knowledge-base-policy.md)이며, repo↔vault 경계는 그쪽에서, vault 내부 구조는 본 문서에서 정의한다.

## 원칙

1. **vault는 누적 지식** — 코드·SQL·스키마 원본은 repo가 SSOT. vault는 해석·결정·도메인 의미·시점성 분석만 담는다.
2. **프로세스 1차, 서비스 2차** — 매일 접근하는 1차 entry는 `processes/`. 서비스 산출물은 `services/{name}/`에서 완결.
3. **도메인 지식은 서비스별** — cross-cutting 도메인은 드물고 도메인 해석·함정·분기는 서비스 안에서 의미 있음.
4. **단일 데이터 모델** — 모든 `/ad:*` 스킬이 같은 frontmatter 스키마를 read/write.
5. **harness ↔ vault 단방향 generated block** — harness 콘텐츠 복제 금지, generated 블록으로 참조.

## top-level 구조

```
wiki/
├── _index.md
├── _log.md
│
├── processes/                    # 1차 entry: 업무 프로세스 (시간축)
│   ├── sprint/                   # 스프린트 운영·마감·캘린더
│   ├── okr/                      # 분기/연간 OKR
│   ├── weekly/                   # 주간업무 보고·계획
│   ├── daily/                    # daily 노트
│   ├── meetings/                 # 회의록
│   ├── tickets/                  # DEV2-* 티켓 산출물 (상태별)
│   ├── incidents/                # 장애 사례
│   └── capacity/                 # 가용 맨데이·velocity 스냅샷
│
├── services/                     # 2차 entry: 서비스별 전체 서브트리
│   ├── {service_id}/             # catalog `service_id` 값 (예: max, tobe, naru, bazaar, aasm, shopping, caravan, blog, storefront)
│
├── projects/                     # cross-service 프로젝트
│
├── guides/                       # 위키 자체 운영 가이드·룰 (메타)
│
└── glossary/                     # canonical 도메인 용어 사전
```

vault 루트 별도 자산 (`wiki/`와 무관):
- `graph/`, `registry/`, `scripts/`, `tests/` — 자동화 자산
- `weekly/` — root 초안 (`wiki/processes/weekly/` 이관 검토는 Sub 2)
- `idc-db-survey/` — IDC DB 조사 자료 (현 위치 유지 또는 Sub 2에서 재배치)

## `processes/` 책임

| 디렉터리 | 책임 |
|---|---|
| `processes/sprint/` | 스프린트 운영·마감 산출물, 회고, 캘린더 |
| `processes/okr/` | 팀/개인 OKR 본문, 분기 KR 정리 |
| `processes/weekly/` | 주간업무 보고서 초안·확정본, 주간 계획 |
| `processes/daily/` | daily 노트 (`YYYY-MM-DD.md`), 오늘의 아젠다 |
| `processes/meetings/` | 회의록 (`YYYY-MM-DD-topic.md`), KB 아님 |
| `processes/tickets/` | DEV2-* 티켓 산출물 (auto-prep/in-progress/done/backlog/archive) |
| `processes/incidents/` | 장애 사례·post-mortem |
| `processes/capacity/` | 가용 맨데이·velocity 스냅샷 (월별 `YYYY-MM.md`) |

## `services/{service_id}/` 표준

```
services/{service_id}/
├── _index.md              # 서비스 home + generated:harness-link 블록
├── domains/               # 도메인 해석 layer
│   ├── {domain}/          # 도메인 폴더 (커지면 승격)
│   │   ├── _index.md      # 도메인 개요·역할·관계
│   │   ├── business-rules.md
│   │   ├── traps.md       # 함정·금지 패턴
│   │   ├── relations.md   # 다른 도메인·서비스와 관계
│   │   └── notes/         # 시점 노트·ad-hoc 분석
│   └── {simple-domain}.md # 단일 파일 (단순 도메인)
├── analysis/              # 시점성 분석 (coverage gap·audit·triage)
├── decisions/             # 서비스 ADR
├── proposals/             # 개선 후보·신청서
└── processes/             # 서비스 전용 runbook (배포 절차 등)
```

규모 작으면 단일 파일 `domains/{domain}.md`로 시작, 커지면 폴더로 승격. lint 강제 없음, 컨벤션만.

### 디렉터리명 규칙

`services/{service_id}/`의 service_id는 harness `catalog/{service_id}.yaml`의 `service_id` 필드 값과 정확히 일치한다. CLAUDE.md 표기명 또는 한국어명이 아니라 카탈로그 id 기준.

현재 서비스 목록: max, tobe, naru, bazaar, aasm, shopping, caravan, blog, storefront.

### vault에 두지 않는 것

| 자료 | SSOT 위치 |
|---|---|
| SP/Table 원본 정의 | DB script repo |
| API 정의 | 서비스 repo OpenAPI/코드 |
| 자동 추출된 graph·registry sidecar | vault `graph/`, `registry/` |
| raw 인벤토리 enumeration | 폐지 (repo 참조 링크로 대체) |

해석·gap·trap·매트릭스만 `services/{service_id}/domains/` 또는 `analysis/`에 둔다.

## `processes/tickets/` 상태별 구조

```
processes/tickets/
├── _index.md
├── auto-prep/             # 야간 자동 분석 산출물 (검토 대기) ← Sub 6 entry
├── in-progress/           # 진행 중 (사용자 또는 ad:work-prep로 이동)
├── done/                  # 완료 (스프린트 마감 후 정리)
├── backlog/               # 향후 작업 후보 (사전 분석)
└── archive/{YYYY-Q}/      # 분기별 done 아카이브
```

frontmatter 스키마는 [[frontmatter-spec]] 참조.

## `projects/` 책임

다중 서비스에 걸치는 프로젝트. 한 프로젝트 안에서 여러 서비스의 도메인·결정·산출물이 묶인다.

현재 후보: storefront-platform (storefront 서비스 자체와 구분 — storefront 서비스 안의 결정 + 다른 서비스 영향 + 인증·테넌트 모델 등 cross-cutting), operational-knowledge-wiki (본 위키 자체 운영 설계).

## `guides/` 책임

vault 운영 메타 가이드. 본 문서 자체, [[frontmatter-spec]], [[document-placement]], [[skills-integration]], [[harness-link-protocol]], lint 룰, generated block 정책 등. service 또는 process 산출물 아님.

## `glossary/` 책임

도메인 용어 canonical 정의. `{term}.md` 단일 파일 (예: `order-type.md`, `book-id.md`). 다른 문서는 본 정의를 wikilink로 참조.

## 폐지·흡수 대상 (현재 → 새 위치)

본 spec 채택 시점에 존재하는 디렉터리 중 폐지 또는 흡수 대상. 실제 마이그레이션은 Sub 2~3에서 파일별 판정 후 일괄 이동.

| 현재 dir | 처리 |
|---|---|
| `wiki/contracts/` (148) | 해석성은 `services/{name}/analysis/` 또는 `domains/`, raw는 폐지 + repo/graph 링크 |
| `wiki/inventory/` (62) | 동일 |
| `wiki/domains/` (12) | 각 서비스 `domains/`로 분산 |
| `wiki/proposals/` (14) | 각 서비스 `proposals/`로 분산 |
| `wiki/decisions/` (5) | 각 서비스 `decisions/`로 분산 |
| `wiki/processes/` (4) | service-specific은 services로, ops-level은 processes로 분리 |
| `wiki/tasks/`, `wiki/usecases/` (8) | services 산하 또는 `processes/tickets/`로 흡수 |
| `wiki/services/` (4) | `services/{name}/_index.md`로 흡수 |
| `wiki/tickets/`, `wiki/okr/`, `wiki/daily/`, `wiki/meetings/`, `wiki/incidents/`, `wiki/capacity/`, `wiki/briefs/` | `processes/{*}/`로 이동 |
| `wiki/indexes/` | `processes/`·`services/` 각 `_index.md`로 분산 |
| `wiki/archive/`, `wiki/exports/`, `wiki/patterns/`, `wiki/imports/`, `wiki/templates/` | 사용처 점검 후 폐지 또는 `guides/`로 |

## 관련

- [[frontmatter-spec]] — frontmatter 표준
- [[document-placement]] — 새 노트 어디에 둘지 결정 트리
- [[skills-integration]] — `/ad:*` 스킬과 vault 통합
- [[harness-link-protocol]] — harness ↔ vault 연결 프로토콜
- harness `policies/knowledge-base-policy.md` — repo↔vault 경계 SoT
````

- [ ] **Step 2: 파일 검증**

```bash
ls -la "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/guides/taxonomy.md"
wc -l "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/guides/taxonomy.md"
```

Expected: 파일 존재, 약 130~150 라인.

### Task 1.2: `frontmatter-spec.md` 작성

**Files:**
- Create: `VAULT/wiki/guides/frontmatter-spec.md`

- [ ] **Step 1: 파일 작성**

다음 내용으로 `VAULT/wiki/guides/frontmatter-spec.md` 생성:

````markdown
---
type: guide
title: frontmatter 표준
canonical_id: guide:frontmatter-spec
status: canonical
updated_at: 2026-05-27
---

# frontmatter 표준

vault 내 문서 frontmatter 스키마를 정의한다. `/ad:*` 스킬이 vault를 단일 데이터 모델로 query할 수 있도록, 주요 문서 타입은 본 스펙을 따른다.

## 공통 필드 (모든 vault 문서)

```yaml
type: <문서 타입>
title: <한국어 제목>
canonical_id: <type:slug 형태 식별자>
status: canonical | draft | candidate | stale
updated_at: YYYY-MM-DD
```

`type` 값:
- `service-index` — `services/{service_id}/_index.md`
- `domain-index` — `services/{service_id}/domains/{domain}/_index.md`
- `ticket` — `processes/tickets/**/*.md`
- `weekly-report` — `processes/weekly/*.md`
- `daily` — `processes/daily/*.md`
- `meeting` — `processes/meetings/*.md`
- `okr` — `processes/okr/*.md`
- `analysis` — `services/{service_id}/analysis/*.md`
- `decision` — `services/{service_id}/decisions/*.md`
- `proposal` — `services/{service_id}/proposals/*.md`
- `guide` — `guides/*.md`
- `glossary` — `glossary/*.md`
- `project` — `projects/{name}/*.md`
- `index` — `_index.md` (각 디렉터리)
- `log` — `_log.md` (변경 로그)

`canonical_id` 형식: `<type>:<slug>` (예: `ticket:DEV2-5749`, `service:max`, `domain:max/order`, `guide:taxonomy`).

## 티켓 산출물 (`processes/tickets/**/*.md`)

```yaml
---
type: ticket
title: <한국어 제목 또는 YouTrack 원제목>
canonical_id: ticket:DEV2-5749
status: canonical
updated_at: 2026-05-27
ticket_id: DEV2-5749
ticket_status: auto-prep | in-progress | done | backlog
assignee: jmkim                 # policies/team-members.md 키
service: max                    # catalog/{service_id}.yaml 의 service_id
sprint: 2026-05                 # YYYY-MM
type_yt: feature | task | bug
related_domains:
  - services/max/domains/order
related_tickets:
  - DEV2-5750
okr_kr: 2026-Q2-KR3             # 선택
created_at: 2026-05-27
---
```

`ticket_status` 값은 디렉터리와 일치한다 (`auto-prep/` 안 파일은 `ticket_status: auto-prep`).

`status` (공통)와 `ticket_status` (티켓 전용)는 별도 필드. 공통 `status`는 문서 신뢰도(canonical/draft 등), `ticket_status`는 작업 워크플로 상태.

## 서비스 `_index.md`

```yaml
---
type: service-index
title: <서비스 한국어 이름>
canonical_id: service:max
status: canonical
updated_at: 2026-05-27
service_id: max                 # harness catalog/{name}.yaml 의 service_id
---
```

본문에 `<!-- generated:harness-link -->` 블록 (상세: [[harness-link-protocol]]).

## 도메인 `_index.md`

```yaml
---
type: domain-index
title: <도메인 한국어 이름>
canonical_id: domain:max/order
status: canonical
updated_at: 2026-05-27
service_id: max
domain: order
---
```

## 주간업무 보고

```yaml
---
type: weekly-report
title: 2026-05-2W 김정민 주간업무
canonical_id: weekly-report:2026-05-2W-jmkim
status: canonical | draft
updated_at: 2026-05-13
assignee: jmkim
year: 2026
month: 5
week_in_month: 2
sprint: 2026-05
---
```

## OKR

```yaml
---
type: okr
title: 김정민 2026 Q2 개인 OKR
canonical_id: okr:2026-Q2-jmkim
status: canonical
updated_at: 2026-05-27
year: 2026
quarter: 2
scope: team | personal
assignee: jmkim                 # personal일 때만
---
```

## 회의록

```yaml
---
type: meeting
title: 2026-05-27 스토어프론트 멀티 테넌시 결정
canonical_id: meeting:2026-05-27-storefront-multi-tenancy
status: canonical
updated_at: 2026-05-27
date: 2026-05-27
participants:
  - jmkim
  - heum2
  - hyeryun
related_tickets:
  - DEV2-6100
related_services:
  - storefront
---
```

## 분석·결정·제안 (서비스 산하)

```yaml
---
type: analysis | decision | proposal
title: <한국어 제목>
canonical_id: <type>:<service_id>/<slug>
status: canonical | draft | candidate
updated_at: 2026-05-27
service_id: max
related_domains:
  - services/max/domains/order
related_tickets:
  - DEV2-5749
---
```

## 신규 필드 추가 절차

본 스펙에 정의되지 않은 필드를 추가할 때:
1. 본 문서에 필드·의미·예시 추가
2. 영향 받는 `/ad:*` 스킬 본문 갱신 (또는 Sub 7 모음)
3. 기존 문서 일괄 갱신은 `scripts/migrate_frontmatter.py` (Sub 5에서 작성)

## 관련

- [[taxonomy]] — 디렉터리 구조
- [[document-placement]] — 새 노트 위치 결정
- [[skills-integration]] — 스킬 chain에서 frontmatter 사용
````

- [ ] **Step 2: 파일 검증**

```bash
ls -la "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/guides/frontmatter-spec.md"
```

Expected: 존재, 약 150~170 라인.

### Task 1.3: `document-placement.md` 작성

**Files:**
- Create: `VAULT/wiki/guides/document-placement.md`

- [ ] **Step 1: 파일 작성**

다음 내용으로 `VAULT/wiki/guides/document-placement.md` 생성:

````markdown
---
type: guide
title: 새 vault 노트 어디에 둘지
canonical_id: guide:document-placement
status: canonical
updated_at: 2026-05-27
---

# 새 vault 노트 어디에 둘지

vault 내부 결정 트리. harness 측 트리(repo↔vault 경계)는 [team2 repo `policies/knowledge-base-policy.md`](file:///Users/jm/Documents/workspace/team2/policies/knowledge-base-policy.md) 참조.

## 결정 트리

```
새 vault 노트 작성 필요
  │
  ├─ 특정 티켓 단위 산출물 (DEV2-*)?
  │     → processes/tickets/{status}/{DEV2-id}.md (frontmatter ticket_status)
  │
  ├─ 주기적 운영 (sprint/weekly/daily/meetings/okr/incidents/capacity)?
  │     → processes/{*}/...
  │
  ├─ 특정 서비스 1개에 묶이는 도메인·해석·결정·개선·runbook?
  │     → services/{service_id}/{domains|analysis|decisions|proposals|processes}/
  │
  ├─ 다중 서비스 cross-cutting 프로젝트?
  │     → projects/{project-name}/
  │
  ├─ 위키 자체 운영 규칙·메타 가이드?
  │     → guides/
  │
  ├─ canonical 도메인 용어 정의?
  │     → glossary/{term}.md
  │
  └─ 위 어디에도 안 맞음?
        → 정지 → user 확인 후 분류 추가 결정
```

판단 모호 시 우선순위:
1. **티켓 단위** > 서비스 단위 (티켓이 1차 작업 unit)
2. **특정 서비스 ≥ 80% 비중** → service 산하
3. **2개 이상 서비스 균등 비중** → `projects/`
4. **시간축 누적 (회의·일지·주간)** → `processes/`

## 시그널 매트릭스

| 시그널 | 위치 |
|---|---|
| "DEV2-* 작업 prep / 결과" | `processes/tickets/{status}/` |
| "5월 4주차 회의" | `processes/meetings/` |
| "5월 2W 주간보고 초안" | `processes/weekly/` |
| "2026-05-27 daily" | `processes/daily/` |
| "5월 capacity plan" | `processes/capacity/` |
| "스프린트 마감 점검 결과" | `processes/sprint/` 또는 `processes/tickets/` 단편 |
| "max 주문 도메인 함정" | `services/max/domains/order/traps.md` |
| "tobe 계정 마이그레이션 평가" | `services/tobe/analysis/account-migration.md` |
| "naru OIDC 결정" | `services/naru/decisions/oidc-flow.md` |
| "max API 방화벽 신청" | `services/max/proposals/...` |
| "storefront 플랫폼 v2 설계" | `projects/storefront-platform/` |
| "lint 룰", "위키 작성법" | `guides/` |
| "OrderType=1 정의" | `glossary/order-type.md` |

## 안티패턴 (피해야 할 위치)

| 안티패턴 | 올바른 위치 |
|---|---|
| 특정 티켓 산출물을 `services/{name}/` 안에 둠 | `processes/tickets/{status}/`, frontmatter로 service 연결 |
| 도메인 가이드를 `wiki/guides/`에 둠 | `services/{service_id}/domains/` |
| 회의록을 YouTrack KB에 두려 함 | `processes/meetings/` |
| 운영 분석을 vault 루트에 두려 함 | `services/{service_id}/analysis/` |
| raw SP/Table enumeration을 vault에 두려 함 | DB script repo 참조 + vault `graph/` |
| 정책 본문을 vault에 복제 | harness `policies/` SSOT, vault는 link만 |

## harness 정책과 cross-link

본 트리는 [team2 repo `policies/knowledge-base-policy.md`](file:///Users/jm/Documents/workspace/team2/policies/knowledge-base-policy.md)의 **vault 내부 세부** 판이다. repo↔vault 경계 1차 결정은 harness 측에서 하고, vault 안 어디로 갈지는 본 문서에서 결정한다. 두 트리는 의미 일치해야 한다 — 차이 발견 시 `ad:harness-optimize` 드리프트 점검에서 surface.

## 관련

- [[taxonomy]] — 디렉터리 구조 정의
- [[frontmatter-spec]] — frontmatter로 분류 보강
- [[skills-integration]] — 스킬이 어디에 쓰는지
````

- [ ] **Step 2: 파일 검증**

```bash
ls -la "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/guides/document-placement.md"
```

Expected: 존재.

### Task 1.4: `skills-integration.md` 작성

**Files:**
- Create: `VAULT/wiki/guides/skills-integration.md`

- [ ] **Step 1: 파일 작성**

다음 내용으로 `VAULT/wiki/guides/skills-integration.md` 생성:

````markdown
---
type: guide
title: 팀 스킬과 vault 통합
canonical_id: guide:skills-integration
status: canonical
updated_at: 2026-05-27
---

# 팀 스킬과 vault 통합

모든 `/ad:*` 스킬이 같은 vault 택소노미와 frontmatter 표준 위에서 동작하도록 경로·데이터 모델·chain을 정의한다.

본 문서는 *명세*이며, 실제 스킬 본문 갱신은 Sub 7에서 일괄 수행한다.

## 스킬별 vault 경로 매핑

| 스킬 | vault 읽기 | vault 쓰기 | harness 참조 |
|---|---|---|---|
| `ad:ticket` | `catalog/{service}.yaml` | (YouTrack 직접) | `policies/branching-strategy`, `docs/sprint/ticket-guide` |
| `ad:work-prep` | `services/{service_id}/domains/`, `processes/tickets/auto-prep/{id}.md` (있으면) | `processes/tickets/in-progress/{id}.md`, `processes/daily/{date}.md` 아젠다 | `catalog/`, `policies/team-members` |
| `ad:weekly-report` | `processes/tickets/{*}/{id}.md` frontmatter query, `processes/sprint/` | `processes/weekly/{YYYY-MM-NW}-draft.md` | `docs/sprint/weekly-report-guide` (KB DEV2-A-696 SoT) |
| `ad:weekly-planned` | (YouTrack `planned` 태그) | `processes/weekly/{date}-w{N}.md`, `processes/meetings/` 링크 | `docs/sprint/weekly-report-guide` |
| `ad:sprint-close-check` | `processes/tickets/{*}/{id}.md` (status·결과물·SP·5W1H·OKR), `processes/sprint/` | (report only) | `docs/sprint/sprint-closing-process` |
| `ad:capacity-plan` | `processes/sprint/{prev}-velocity`, `processes/capacity/` | `processes/capacity/{YYYY-MM}.md` (옵션 저장) | `docs/sprint/velocity-guide`, `docs/sprint/story-point-guide`, KB DEV2-A-1122 |
| `ad:service-activity` | `processes/tickets/{*}/{id}.md` (service filter) | `services/{service_id}/processes/activity-{period}.md` (옵션 저장) | `catalog/` |
| `ad:okr` | `processes/okr/{YYYY-Q}-team-okr.md`, `processes/okr/{YYYY-Q}-{user}.md` | `processes/okr/{YYYY-Q}-{user}.md` | KB REF-A-* |
| `ad:harness-optimize` | vault 전체 + harness `policies/`, `catalog/`, `.claude/commands/ad/` | (제안·surface 출력만) | 전부 + drift check |
| `ad:data-request` | `services/{service_id}/proposals/` (참조) | (data-requests-dev2 repo로 직접) | `policies/data-request-policy` |
| `ad:code-review` | (GitHub) | (없음) | `policies/code-review-policy`, `policies/branching-strategy` |

## 스킬 chain (자동 흐름)

```
                ┌─── ad:capacity-plan (다음달 SP 예측)
                │
[야간] auto-prep ─→ processes/tickets/auto-prep/{id}.md
                              │
[출근] ad:work-prep ──────────▼
                processes/tickets/in-progress/{id}.md
                processes/daily/{date}.md 아젠다 추가
                              │
[작업 중] (개발)               │
                              ▼
[작업 완료] frontmatter ticket_status: done
                processes/tickets/done/{id}.md
                              │
[주중] ad:weekly-planned ─────▼
                processes/weekly/{date}-w{N}.md (회의용)
                              │
[금요] ad:weekly-report ──────▼
                processes/weekly/{YYYY-MM-NW}-draft.md
                              │
[스프린트 마감] ad:sprint-close-check ─▼
                자가점검 보고 (변경 없음)
                              │
[분기 마감] ad:okr (KR 연계 정리)
```

## 데이터 모델 query 패턴

스킬이 vault에서 티켓을 query할 때 공통 패턴:

- **service filter**: `frontmatter.service == "{service_id}"`
- **status filter**: `frontmatter.ticket_status == "{status}"` 또는 디렉터리 경로
- **sprint filter**: `frontmatter.sprint == "{YYYY-MM}"`
- **assignee filter**: `frontmatter.assignee == "{user}"`

Obsidian 측에서는 Dataview 또는 Bases로 같은 필터 사용 가능.

스크립트 측 (예: ad:weekly-report)는 `processes/tickets/` 전체를 `find` + frontmatter 파싱으로 query. 표준 파서는 `scripts/query_tickets.py` (Sub 5에서 작성).

## 신규 스킬 추가 절차

새 `/ad:*` 스킬 추가 시:
1. 본 문서 표에 row 추가 (vault 읽기/쓰기/harness 참조)
2. 스킬 chain에 어디 끼는지 명시
3. 사용하는 frontmatter 필드가 [[frontmatter-spec]]에 없으면 거기 먼저 추가
4. 스킬 본문에 본 문서 cross-link

## 관련

- [[taxonomy]] — 디렉터리 구조
- [[frontmatter-spec]] — 데이터 스키마
- [[document-placement]] — 새 노트 위치
- [[harness-link-protocol]] — harness ↔ vault 연결
- harness `.claude/commands/ad/` — 실 스킬 본문
````

- [ ] **Step 2: 파일 검증**

```bash
ls -la "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/guides/skills-integration.md"
```

Expected: 존재.

### Task 1.5: `harness-link-protocol.md` 작성

**Files:**
- Create: `VAULT/wiki/guides/harness-link-protocol.md`

- [ ] **Step 1: 파일 작성**

다음 내용으로 `VAULT/wiki/guides/harness-link-protocol.md` 생성:

````markdown
---
type: guide
title: harness ↔ vault 연결 프로토콜
canonical_id: guide:harness-link-protocol
status: canonical
updated_at: 2026-05-27
---

# harness ↔ vault 연결 프로토콜

team2 harness(repo)와 vault의 일관성을 generated block 기반으로 유지하는 프로토콜.

**원칙: vault는 harness 콘텐츠를 복제하지 않는다.** `<!-- generated:harness-* -->` 블록에만 자동 갱신되는 참조 표를 둔다. 본문 인간 작성 영역은 generated 블록과 독립.

## generated block 종류

### A. `generated:harness-link` — 서비스별

`services/{service_id}/_index.md` 본문 안:

```markdown
<!-- generated:harness-link source=team2/catalog/{service_id}.yaml updated=YYYY-MM-DD -->
- repo: AladinCommunication/{repo_name}
- 분류: {legacy|new}, 전략: {Wrap|Extract|Observe|Freeze}
- 오너: {담당자 한 명 또는 매트릭스} ← [[../../processes/team/_index|팀]]
- 적용 정책: {policy-list}
- 카탈로그: `team2/catalog/{service_id}.yaml`
<!-- /generated -->
```

입력: `catalog/{service_id}.yaml` (repos, owners.primary, type, strategy, policies).

### B. `generated:team-members` — 팀 페이지

`processes/team/_index.md` 본문 안:

```markdown
<!-- generated:team-members source=team2/policies/team-members.md updated=YYYY-MM-DD -->
| 역할 | 이름 | 담당 서비스 |
|---|---|---|
| 백엔드 개발자 | 김정민 (jmkim) | [[../../services/max/|max]] [[../../services/tobe/|tobe]] ... |
| 백엔드 개발자 | 안혜련 (hyeryun) | [[../../services/storefront/|storefront]] |
| ...
<!-- /generated -->
```

입력: harness `policies/team-members.md` + `catalog/*.yaml` (담당 서비스 cross-link).

### C. `generated:policy-index` — vault root

`wiki/_index.md` 본문 안:

```markdown
<!-- generated:policy-index source=team2/policies/ updated=YYYY-MM-DD -->
| 정책 | 한 줄 요약 |
|---|---|
| [branching-strategy](file:///Users/jm/Documents/workspace/team2/policies/branching-strategy.md) | Git Flow 기반, Feature ID 브랜치 누적 |
| [knowledge-base-policy](file:///Users/jm/Documents/workspace/team2/policies/knowledge-base-policy.md) | repo↔vault 경계 정의 |
| ...
<!-- /generated -->
```

입력: harness `policies/*.md` 파일 목록 + 각 파일 첫 단락 또는 H1 다음 첫 문장.

## 동기화 스크립트

`scripts/sync_harness_links.py` (Sub 5에서 실 구현):

- env: `HARNESS_ROOT=~/Documents/workspace/team2`
- 입력 파싱:
  - `$HARNESS_ROOT/catalog/*.yaml` → 서비스 메타
  - `$HARNESS_ROOT/policies/team-members.md` → 팀원 매트릭스
  - `$HARNESS_ROOT/policies/*.md` → 정책 인덱스
- 출력: vault 내 `<!-- generated:harness-* -->` 블록 갱신
- 기존 `scripts/generate_wiki.py` 패턴 답습 (vault CLAUDE.md 원칙: "generated block만 자동 갱신")
- CLI:
  - `python3 scripts/sync_harness_links.py` — 갱신 실행
  - `python3 scripts/sync_harness_links.py --dry-run` — diff만 출력
- 실행 hook: 수동 + `ad:harness-optimize` 드리프트 점검 단계 통합

## 역방향: harness 변경 시 vault 영향 surface

`ad:harness-optimize`에 점검 단계 추가 (Sub 5에서 구현):

1. 기존 drift 점검 (repo·vault 위치 위반)
2. `sync_harness_links.py --dry-run` (generated block 드리프트 — harness 콘텐츠가 vault generated 영역과 불일치하는 경우)
3. `harness/catalog/*.yaml` 서비스 목록 vs `vault/wiki/services/*/` 디렉터리 목록 일치성 (catalog에 있는데 services/에 없으면 디렉터리 누락, 반대도 surface)
4. frontmatter 스키마 검증 (`processes/tickets/**/*.md`, `services/*/_index.md`, ...)
5. 끊긴 wikilink 검출 (`scripts/lint_wiki.py` 확장)

자동 commit/push 없음. surface된 항목은 사용자 검토 후 수동 또는 명시 명령으로 갱신.

## 변경 영향 매트릭스 (어떤 harness 파일이 어떤 vault 블록을 트리거하는가)

| harness 파일 | 갱신되는 vault 블록 |
|---|---|
| `catalog/{service_id}.yaml` | `services/{service_id}/_index.md` 의 `generated:harness-link` |
| `policies/team-members.md` | `processes/team/_index.md` 의 `generated:team-members` + 모든 `services/*/_index.md` 오너 셀 |
| `policies/*.md` 신규/제거 | `wiki/_index.md` 의 `generated:policy-index` |
| `policies/knowledge-base-policy.md` | vault `guides/document-placement.md` 의 cross-link 표현 (수동 검토 surface, 자동 갱신 X — 의미 변경 시 사람이 vault 측 가이드 갱신) |

## 관련

- [[taxonomy]] — vault 디렉터리
- [[skills-integration]] — `ad:harness-optimize`가 본 프로토콜 호출
- harness `policies/knowledge-base-policy.md` — repo↔vault 경계
````

- [ ] **Step 2: 파일 검증**

```bash
ls -la "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/guides/harness-link-protocol.md"
```

Expected: 존재.

### Task 1.6: Phase 1 vault commit

**Files:** Phase 1에서 만든 5개 파일

- [ ] **Step 1: vault staging**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git add wiki/guides/taxonomy.md wiki/guides/frontmatter-spec.md wiki/guides/document-placement.md wiki/guides/skills-integration.md wiki/guides/harness-link-protocol.md
git status --short | grep guides/
```

Expected: 5개 파일 `A`로 staged.

- [ ] **Step 2: vault commit (사용자 승인 후)**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git commit -m "wiki/guides: vault 택소노미·frontmatter·결정 트리·스킬 통합·harness 연결 명세 추가

Sub 1 (vault 택소노미 정의) 산출물 5건. 마이그레이션은 비범위 (Sub 2~3).
Co-Authored-By 푸터 없음."
```

⚠️ 위 메시지에서 마지막 줄 "Co-Authored-By 푸터 없음" 표현이 footer 검사 grep에 false positive 발생할 수 있으므로 실제 사용 시 마지막 줄 빼고:

```bash
git commit -m "wiki/guides: vault 택소노미·frontmatter·결정 트리·스킬 통합·harness 연결 명세 추가

Sub 1 (vault 택소노미 정의) 산출물 5건. 마이그레이션은 비범위 (Sub 2~3)."
```

Expected: 5 file changed, 0 deletions, ~500+ insertions.

- [ ] **Step 3: footer 검사**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git log -1 --pretty=format:"%B" | tail -3 | grep -i "co-authored\|🤖 generated\|generated with claude code" && echo "BAD" || echo "OK"
```

Expected: `OK no banned footers in last lines`.

---

## Phase 2: vault index/CLAUDE 갱신

### Task 2.1: `wiki/_index.md` 갱신

**Files:**
- Modify: `VAULT/wiki/_index.md`

- [ ] **Step 1: 현재 파일 읽기**

```bash
cat "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/_index.md" | head -60
```

Expected: 현재 _index.md 본문 확인. "주요 진입점" 섹션 위치 파악.

- [ ] **Step 2: "주요 진입점" 또는 "구조" 섹션 보강**

`wiki/_index.md` 본문에 다음 섹션을 적절한 위치(주요 진입점 직전 또는 직후)에 추가. 기존 본문은 보존:

```markdown
## 구조 (택소노미)

새 vault 노트 어디에 둘지 결정은 [[guides/document-placement|문서 위치 결정 트리]] 참조. 디렉터리 의미·책임은 [[guides/taxonomy|vault 택소노미]] 참조.

- `processes/` — 1차 entry: 업무 프로세스 (sprint·okr·weekly·daily·meetings·tickets·incidents·capacity)
- `services/{service_id}/` — 서비스별 전체 (domains·analysis·decisions·proposals·processes)
- `projects/` — cross-service 프로젝트
- `guides/` — vault 운영 메타 가이드
- `glossary/` — canonical 도메인 용어

## 핵심 가이드

- [[guides/taxonomy|vault 택소노미]] — 디렉터리 구조·책임
- [[guides/frontmatter-spec|frontmatter 표준]] — 문서 메타 스키마
- [[guides/document-placement|문서 위치 결정]] — 새 노트 어디에 둘지
- [[guides/skills-integration|팀 스킬 통합]] — `/ad:*` 스킬과 vault 연결
- [[guides/harness-link-protocol|harness 연결 프로토콜]] — repo ↔ vault generated block
```

- [ ] **Step 3: 파일 검증**

```bash
grep -n "guides/taxonomy\|guides/frontmatter-spec\|guides/document-placement\|guides/skills-integration\|guides/harness-link-protocol" "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/_index.md" | wc -l
```

Expected: 최소 5건 매치 (각 가이드 wikilink 1건씩).

### Task 2.2: `CLAUDE.md` (vault) 갱신

**Files:**
- Modify: `VAULT/CLAUDE.md`

- [ ] **Step 1: 현재 파일 읽기**

```bash
cat "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/CLAUDE.md"
```

Expected: 현재 본문 확인. "## 하네스" 섹션은 이전 Plan(knowledge-scope-separation)에서 이미 갱신됨.

- [ ] **Step 2: "## 택소노미" 섹션 신설**

vault `CLAUDE.md` 본문에 새 섹션 추가 (적절한 위치 = "## 핵심 규칙" 또는 "## 하네스" 직전):

```markdown
## 택소노미

vault 내부 구조 SoT는 [[wiki/guides/taxonomy|guides/taxonomy.md]]. 모든 위치 결정은 [[wiki/guides/document-placement|guides/document-placement.md]] 트리를 따른다.

핵심:
- `processes/` — 1차 entry (sprint·okr·weekly·daily·meetings·tickets·incidents·capacity)
- `services/{service_id}/` — 서비스별 (domains·analysis·decisions·proposals·processes), service_id = harness `catalog/{name}.yaml` 의 service_id 필드
- `projects/`, `guides/`, `glossary/` — 나머지

frontmatter 스키마: [[wiki/guides/frontmatter-spec|guides/frontmatter-spec.md]].

`/ad:*` 스킬 통합: [[wiki/guides/skills-integration|guides/skills-integration.md]].

`<!-- generated:harness-* -->` 블록은 [[wiki/guides/harness-link-protocol|guides/harness-link-protocol.md]] 규칙 따른다. 자동 갱신 영역만 스크립트가 다루고, 인간 작성 영역은 보존한다.
```

- [ ] **Step 3: 검증**

```bash
grep -n "guides/taxonomy\|guides/document-placement\|guides/frontmatter-spec\|guides/skills-integration\|guides/harness-link-protocol" "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/CLAUDE.md"
```

Expected: 5건 매치.

### Task 2.3: Phase 2 vault commit

- [ ] **Step 1: staging**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git add wiki/_index.md CLAUDE.md
git status --short
```

Expected: 2개 파일 `M`.

- [ ] **Step 2: commit (사용자 승인 후)**

```bash
git commit -m "wiki/_index, CLAUDE.md: 새 택소노미 진입점·guides 5건 cross-link 추가"
```

- [ ] **Step 3: footer 검사**

```bash
git log -1 --pretty=format:"%B" | tail -3 | grep -i "co-authored\|🤖 generated\|generated with claude code" && echo "BAD" || echo "OK"
```

Expected: OK.

---

## Phase 3: harness 정책 cross-link

### Task 3.1: `policies/knowledge-base-policy.md` 갱신

**Files:**
- Modify: `REPO/policies/knowledge-base-policy.md`

- [ ] **Step 1: 현재 파일 확인**

```bash
grep -n "vault\|결정 트리\|분류" /Users/jm/Documents/workspace/team2/policies/knowledge-base-policy.md | head -10
```

Expected: 기존 본문에 "결정 트리"(repo↔vault 경계) 섹션 존재.

- [ ] **Step 2: "결정 트리" 섹션 말미에 vault 내부 트리 cross-link 추가**

`REPO/policies/knowledge-base-policy.md`의 "## 신규 문서 위치 결정 트리" 섹션 말미(`판단 모호 시 기본값 = **Obsidian vault**.` 라인 뒤)에 한 줄 추가:

```markdown

vault **내부** 결정 트리(어느 디렉터리에 둘지)는 vault 측 [`wiki/guides/document-placement.md`](obsidian://open?vault=team2&file=wiki%2Fguides%2Fdocument-placement) 참조. 본 문서가 정의하는 *경계*는 "어느 저장소에 둘지"까지이고, *vault 내부 분류*는 vault 측 가이드가 SoT.
```

- [ ] **Step 3: 검증**

```bash
grep -n "wiki/guides/document-placement" /Users/jm/Documents/workspace/team2/policies/knowledge-base-policy.md
```

Expected: 1건 매치.

---

## Phase 4: 검증

### Task 4.1: 일관성 검증

- [ ] **Step 1: vault 측 5개 guides + 2개 entry 갱신 확인**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
ls -1 "$VAULT/wiki/guides/" | grep -E "taxonomy|frontmatter-spec|document-placement|skills-integration|harness-link-protocol" | wc -l
```

Expected: 5.

- [ ] **Step 2: vault `_index.md` 와 `CLAUDE.md`에서 모든 guides 링크 확인**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
for g in taxonomy frontmatter-spec document-placement skills-integration harness-link-protocol; do
  count=$(grep -c "guides/$g" "$VAULT/wiki/_index.md" "$VAULT/CLAUDE.md")
  echo "$g: $count"
done
```

Expected: 각 가이드 ≥ 2 (인덱스 + CLAUDE).

- [ ] **Step 3: harness 측 cross-link 확인**

```bash
grep -n "wiki/guides/document-placement" /Users/jm/Documents/workspace/team2/policies/knowledge-base-policy.md
```

Expected: 1.

- [ ] **Step 4: vault guides 간 cross-link 무결성**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
for g in taxonomy frontmatter-spec document-placement skills-integration harness-link-protocol; do
  echo "=== $g referenced by ==="
  grep -l "\[\[$g\]\]\|\[\[guides/$g\]\]\|\[\[../guides/$g\]\]" "$VAULT/wiki/guides/"*.md "$VAULT/wiki/_index.md" "$VAULT/CLAUDE.md" 2>/dev/null
done
```

Expected: 각 가이드가 다른 가이드에서 ≥ 1 참조됨 (각 가이드 본문 "관련" 섹션을 통해).

- [ ] **Step 5: footer 검사 (vault 양 commit)**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git log -2 --pretty=format:"%B%n===" | grep -iE "(co-authored-by:|🤖 generated with|generated with claude code)" && echo "BAD" || echo "OK no banned footers"
```

Expected: OK.

### Task 4.2: harness commit (Sub 1 마무리)

**Files:** Phase 3 변경 + 본 Plan 파일

- [ ] **Step 1: staging**

```bash
cd /Users/jm/Documents/workspace/team2
git add policies/knowledge-base-policy.md docs/superpowers/plans/2026-05-27-vault-taxonomy.md
git status --short
```

Expected: 2개 (M policies/knowledge-base-policy.md, A docs/superpowers/plans/2026-05-27-vault-taxonomy.md).

- [ ] **Step 2: commit (사용자 승인 후)**

```bash
git commit -m "policies/knowledge-base-policy: vault 내부 결정 트리 cross-link 추가

vault 측 wiki/guides/document-placement.md가 vault 내부 분류 SoT. 본 정책은 repo↔vault 경계까지만 다룬다.
+ Sub 1 vault 택소노미 구현 Plan 추가."
```

- [ ] **Step 3: footer 검사**

```bash
git log -1 --pretty=format:"%B" | grep -iE "(co-authored-by|🤖 generated|generated with claude code)" && echo "BAD" || echo "OK"
```

Expected: OK.

---

## Self-Review

- **Spec 커버리지**:
  - Sub 1 산출물 8개 ↔ Phase 1 (5개 guides) + Phase 2 (_index + CLAUDE) + Phase 3 (knowledge-base-policy) = 8 ✓
- **Placeholder 없음**: TBD/TODO/이후 채움 없음. 모든 파일 본문 전체 명시.
- **타입·식별자 일관**:
  - service_id 표현 통일 (max, tobe, ..., storefront)
  - frontmatter 필드명 일관 (`ticket_status` vs `status` 분리 명시)
  - canonical_id 형식 일관 (`<type>:<slug>`)
- **cross-link 일관**: Phase 4 Task 4.1 Step 4가 양방향 cross-link 검증.

빠진 부분 없음. vault `weekly/` root 위치 처리는 Sub 2 비범위로 명시. `idc-db-survey/` 처리 역시 Sub 2.

## 검증 기준 (Plan 완료 조건)

- vault commit 2건 (`wiki/guides:`, `wiki/_index, CLAUDE.md:`)
- harness commit 1건 (`policies/knowledge-base-policy:` + plan 파일 add)
- vault `wiki/guides/`에 새 5개 파일 존재
- vault `_index.md` 와 `CLAUDE.md`에 5개 가이드 모두 wikilink
- harness `policies/knowledge-base-policy.md`에 vault 가이드 cross-link
- 모든 commit에 AI footer 없음
- 마이그레이션 0건 (파일 이동 없음)
