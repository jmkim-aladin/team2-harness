# vault 택소노미 정의 (Sub 1) 설계

## 배경

`2026-05-27-knowledge-scope-separation-design.md`에서 repo 하네스 = "어떻게 일하나", Obsidian vault = "무엇을 일하나" 경계를 정의·구현했다. 이관은 완료되었으나 vault 내부 구조 자체가 여전히 27개 top-level 디렉터리로 흩어져 있고, 다음 문제를 안고 있다.

- top-level dir 책임·SSOT 불명확 (`guides` vs `processes` vs `decisions` vs `proposals` vs `usecases` 의미 중복)
- 분포 불균형 (`guides=183`, `contracts=148`, `inventory=62`, 다수 dir이 한 자릿수)
- 빈/희박 dir 다수 (`archive=0`, `exports=0`, `patterns=0`, `imports=5`, `tasks=5`, `templates=2` 등)
- 서비스 prefix 파일(`tobe-*`, `aasm-*`, `max-*`)이 `guides/`·`inventory/`·`proposals/`에 흩어져 서비스별 탐색이 어려움
- raw enumeration(SP/Table/API 목록)이 vault에 누적되어 코드와 드리프트 발생 — 소스가 바뀌면 vault가 stale
- `/ad:*` 스킬과 vault 경로가 일관되지 않음. 스킬마다 가정하는 위치가 다름
- harness `policies/team-members.md`, `catalog/*.yaml` 변경 시 vault에 반영되는 메커니즘 없음

본 Sub 1의 목표는 **vault 내부 구조와 frontmatter 표준을 정의**하고, **harness·스킬과의 통합 프로토콜을 명문화**하는 것이다. **마이그레이션은 별도 Sub로 분리**한다. 즉 이 spec의 결과물은 *명세 문서들*이며, 실제 파일 이동·재배치는 Sub 2~3에서 수행한다.

## 원칙

1. **vault는 누적 지식**: 코드·SQL·스키마 원본은 repo가 SSOT. vault는 해석·결정·도메인 의미·시점성 분석만 담는다 (Karpathy "context document" 관점).
2. **프로세스 1차, 서비스 2차**: 매일 접근하는 1차 entry는 `processes/` (sprint·weekly·daily·meetings·tickets·okr·incidents·capacity). 서비스 산출물은 `services/{name}/` 안에서 완결성 확보.
3. **도메인 지식은 서비스별**: 알라딘 다수 서비스 환경에서 cross-cutting 도메인은 드물고, 도메인 해석·함정·분기 기준은 대부분 그 서비스 안에서 의미 있음. 따라서 `services/{name}/domains/`.
4. **단일 데이터 모델**: 모든 `/ad:*` 스킬이 같은 frontmatter 스키마(`ticket_id`, `status`, `service`, `sprint` 등)를 read/write. 스킬은 vault 위에서 chain 동작.
5. **harness ↔ vault 단방향 generated block**: harness 콘텐츠는 vault에 복제하지 않고 `<!-- generated:harness-* -->` 블록으로만 참조. 변경 시 sync 스크립트로 갱신.
6. **자동화 친화적 미래 비전 수용**: 야간 auto-prep 워크플로(본인 할당 티켓 자동 분석 → 다음날 검토)를 수용할 수 있도록 `processes/tickets/` 상태별 디렉터리 분리.

## 목표 택소노미

### top-level 구조

```
wiki/
├── _index.md                     # vault root 진입점
├── _log.md                       # 변경 로그 (기존 유지)
│
├── processes/                    # 1차 entry: 업무 프로세스 (시간축 누적)
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
│   ├── {service_id}/             # 디렉터리명 = harness `catalog/{name}.yaml` 의 service_id 필드 (예: max, tobe, naru, bazaar, aasm, shopping, caravan, blog, b2b-store)
│   │   ├── _index.md             # 서비스 home (generated:harness-link 블록)
│   │   ├── domains/              # 서비스 X 도메인 지식 (해석 layer)
│   │   ├── analysis/             # 시점성 분석 (coverage gap·audit·triage)
│   │   ├── decisions/            # 서비스 ADR
│   │   ├── proposals/            # 개선 후보·신청서
│   │   └── processes/            # 서비스 전용 runbook
│
├── projects/                     # cross-service 프로젝트
│   ├── storefront-platform/, operational-knowledge-wiki/, ...
│
├── guides/                       # 위키 자체 운영 가이드·룰 (메타)
│
└── glossary/                     # canonical 도메인 용어 사전
```

vault 루트 별도 유지 (`wiki/`와 무관):
- `graph/`, `registry/`, `scripts/`, `tests/` — 자동화 자산
- `weekly/` — 현재 root 위치 (`wiki/processes/weekly/`로 이관 검토는 Sub 2)
- `idc-db-survey/` — IDC DB 조사 자료 (현 위치 유지 또는 `services/`로 이관 — Sub 2)

### `services/{name}/` 표준 구조

```
services/{name}/
├── _index.md              # 서비스 개요 + harness-link generated block
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

규모 작으면 단일 파일 `domains/{domain}.md`로 시작, 커지면 폴더로 승격. lint 룰로 강제하지 않고 컨벤션만 정의.

**제거 (vault에 두지 않음)**: `inventory/`, `contracts/` 같은 raw enumeration. 다음 위치 활용:
- SP/Table 원본 정의 → DB script repo
- API 정의 → 서비스 repo OpenAPI/코드
- 자동 추출된 graph·registry sidecar → vault `graph/`, `registry/`
- 해석·gap·trap·매트릭스 → `services/{name}/domains/` 또는 `analysis/`

### `processes/tickets/` 상태별 구조

```
processes/tickets/
├── _index.md
├── auto-prep/             # 야간 자동 분석 산출물 (검토 대기) ← Sub 6 entry
├── in-progress/           # 진행 중 (사용자 또는 ad:work-prep로 이동)
├── done/                  # 완료 (스프린트 마감 후 정리)
├── backlog/               # 향후 작업 후보 (사전 분석)
└── archive/{YYYY-Q}/      # 분기별 done 아카이브
```

### 폐지·흡수 대상 (현재 → 새 위치)

| 현재 dir | 처리 방향 |
|---|---|
| `wiki/contracts/` (148) | 해석성은 각 서비스 `analysis/` 또는 `domains/`, raw는 폐지 + repo/graph 링크 |
| `wiki/inventory/` (62) | 동일 |
| `wiki/domains/` (12) | 각 서비스 `domains/`로 분산 |
| `wiki/proposals/` (14) | 각 서비스 `proposals/`로 분산 |
| `wiki/decisions/` (5) | 각 서비스 `decisions/`로 분산 |
| `wiki/processes/` (4) | service-specific은 services로, ops-level은 processes로 분리 |
| `wiki/tasks/`, `wiki/usecases/` (8) | services 산하 또는 processes/tickets로 흡수 |
| `wiki/services/` (4) | `services/{name}/_index.md`로 흡수 |
| `wiki/tickets/`, `wiki/okr/`, `wiki/daily/`, `wiki/meetings/`, `wiki/incidents/`, `wiki/capacity/`, `wiki/briefs/` | `processes/{*}/`로 이동 |
| `wiki/indexes/` | `processes/`·`services/` 각 `_index.md`로 분산 |
| `wiki/archive/`, `wiki/exports/`, `wiki/patterns/`, `wiki/imports/`, `wiki/templates/` | 사용처 점검 후 폐지 또는 `guides/`로 |

실제 매핑은 Sub 2 (감사 + 분류 매트릭스)에서 파일별 판정.

## frontmatter 표준

### 티켓 산출물 (`processes/tickets/**/*.md`)

```yaml
---
ticket_id: DEV2-5749
status: auto-prep | in-progress | done | backlog
assignee: jmkim                # team-members.md 키
service: max                   # catalog/{service}.yaml id
sprint: 2026-05                # YYYY-MM
type: feature | task | bug
related_domains:
  - services/max/domains/order
related_tickets:
  - DEV2-5750
okr_kr: 2026-Q2-KR3            # 선택 (OKR 연계 시)
created_at: 2026-05-27
updated_at: 2026-05-27
---
```

### 서비스 `_index.md`

```yaml
---
type: service-index
service_id: max
canonical_id: service:max
status: canonical
updated_at: 2026-05-27
---
```

본문에 `<!-- generated:harness-link -->` 블록.

### 도메인 `_index.md`

```yaml
---
type: domain-index
service_id: max
domain: order
canonical_id: domain:max/order
status: canonical
updated_at: 2026-05-27
---
```

### 일반 노트

기존 vault frontmatter 컨벤션 유지 (`type`, `title`, `canonical_id`, `status`, `updated_at`). 신규 필드는 위 스킬 chain에서 필요한 경우만 추가.

## 분류 결정 트리

```
새 vault 노트 작성 필요
  │
  ├─ 특정 티켓 단위 산출물 (DEV2-*)?
  │     → processes/tickets/{status}/{DEV2-id}.md
  │
  ├─ 주기적 운영 (sprint/weekly/daily/meetings/okr/incidents/capacity)?
  │     → processes/{*}/...
  │
  ├─ 특정 서비스 1개에 묶이는 도메인·해석·결정·개선·runbook?
  │     → services/{name}/{domains|analysis|decisions|proposals|processes}/
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

### 시그널 매트릭스

| 시그널 | 위치 |
|---|---|
| "DEV2-* 작업 prep / 결과" | `processes/tickets/{status}/` |
| "5월 4주차 회의" | `processes/meetings/` |
| "5월 2W 주간보고 초안" | `processes/weekly/` |
| "2026-05-27 daily" | `processes/daily/` |
| "max 주문 도메인 함정" | `services/max/domains/order/traps.md` |
| "tobe 계정 마이그레이션 평가" | `services/tobe/analysis/account-migration.md` |
| "naru OIDC 결정" | `services/naru/decisions/oidc-flow.md` |
| "storefront 플랫폼 v2 설계" | `projects/storefront-platform/` |
| "lint 룰", "위키 작성법" | `guides/` |
| "OrderType=1 정의" | `glossary/order-type.md` |

## 팀 스킬 통합 매트릭스

### 스킬별 vault 경로 매핑

| 스킬 | vault 읽기 | vault 쓰기 | harness 참조 |
|---|---|---|---|
| `ad:ticket` | `catalog/{service}.yaml` | (YouTrack 직접) | `policies/branching-strategy`, `docs/sprint/ticket-guide` |
| `ad:work-prep` | `services/{name}/domains/`, `processes/tickets/auto-prep/{id}.md` (있으면) | `processes/tickets/in-progress/{id}.md`, `processes/daily/{date}.md` 아젠다 | `catalog/`, `policies/team-members` |
| `ad:weekly-report` | `processes/tickets/{*}/{id}.md` frontmatter query, `processes/sprint/` | `processes/weekly/{YYYY-MM-NW}-draft.md` | `docs/sprint/weekly-report-guide` (KB DEV2-A-696 SoT) |
| `ad:weekly-planned` | (YouTrack `planned` 태그) | `processes/weekly/{date}-w{N}.md`, `processes/meetings/` 링크 | `docs/sprint/weekly-report-guide` |
| `ad:sprint-close-check` | `processes/tickets/{*}/{id}.md` (status·결과물·SP·5W1H·OKR), `processes/sprint/` | (report only) | `docs/sprint/sprint-closing-process` |
| `ad:capacity-plan` | `processes/sprint/{prev}-velocity`, `processes/capacity/` | `processes/capacity/{YYYY-MM}.md` (옵션 저장) | `docs/sprint/velocity-guide`, `docs/sprint/story-point-guide`, KB DEV2-A-1122 |
| `ad:service-activity` | `processes/tickets/{*}/{id}.md` (service filter) | `services/{name}/processes/activity-{period}.md` (옵션 저장) | `catalog/` |
| `ad:okr` | `processes/okr/{YYYY-Q}-team-okr.md`, `processes/okr/{YYYY-Q}-{user}.md` | `processes/okr/{YYYY-Q}-{user}.md` | KB REF-A-* |
| `ad:harness-optimize` | vault 전체 + harness `policies/`, `catalog/`, `.claude/commands/ad/` | (제안·surface 출력만) | 전부 + drift check |
| `ad:data-request` | `services/{name}/proposals/` (참조) | (data-requests-dev2 repo로 직접) | `policies/data-request-policy` |
| `ad:code-review` | (GitHub) | (없음) | `policies/code-review-policy`, `policies/branching-strategy` |

### 스킬 chain

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
[작업 완료] frontmatter status: done
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

스킬 본문 갱신은 Sub 7에서 일괄.

## harness ↔ vault 연결 프로토콜

### A. `services/{name}/_index.md` generated block

```markdown
# {서비스 이름}

<!-- generated:harness-link source=team2/catalog/{name}.yaml updated=YYYY-MM-DD -->
- repo: AladinCommunication/{repo}
- 분류: {legacy|new}, 전략: {Wrap|Extract|Observe|Freeze}
- 오너: {담당자} (한 명 또는 매트릭스) ← [[../../processes/team/_index|팀]]
- 적용 정책: {policy-list}
- 카탈로그: `team2/catalog/{name}.yaml`
<!-- /generated -->

## 도메인
- ...

## 진행 중 분석
- ...
```

### B. `processes/team/_index.md` generated block

```markdown
<!-- generated:team-members source=team2/policies/team-members.md updated=YYYY-MM-DD -->
| 역할 | 이름 | 담당 서비스 |
|---|---|---|
...
<!-- /generated -->
```

### C. vault `_index.md` 정책 인덱스 generated block

harness `policies/*.md` 목록 + 한 줄 요약 자동 인덱싱. 정책 본문은 harness에만, vault는 링크만.

### D. 동기화 스크립트 (Sub 5에서 실 구현)

`scripts/sync_harness_links.py`:
- env: `HARNESS_ROOT=~/Documents/workspace/team2`
- 파싱: `catalog/*.yaml`, `policies/team-members.md`, `policies/` 디렉터리
- 출력: vault 내 `<!-- generated:harness-* -->` 블록 갱신
- 기존 `scripts/generate_wiki.py` 패턴 답습
- 실행 hook: 수동 + `ad:harness-optimize` 드리프트 점검 단계 통합

### E. 역방향: harness 변경 시 vault 영향 surface

`ad:harness-optimize`에 단계 추가:
1. drift 점검 (이미 완료)
2. `sync_harness_links.py --dry-run`
3. `harness/catalog/*.yaml` 서비스 ↔ `vault/wiki/services/*/` 디렉터리 일치성
4. frontmatter 스키마 검증
5. 끊긴 wikilink 검출

자동 push 없음. 사용자 검토 후 vault commit.

## Sub 1 산출물

1. `vault/wiki/guides/taxonomy.md` (신규) — top-level 디렉터리·서비스 표준·폐지 대상
2. `vault/wiki/guides/frontmatter-spec.md` (신규) — 티켓·서비스·도메인 frontmatter 스키마
3. `vault/wiki/guides/document-placement.md` (신규) — 결정 트리, 시그널 매트릭스, harness 정책과 cross-link
4. `vault/wiki/guides/skills-integration.md` (신규) — 스킬-vault 경로 매핑, chain, frontmatter 사용
5. `vault/wiki/guides/harness-link-protocol.md` (신규) — generated block 규칙, sync 스크립트 인터페이스
6. `vault/wiki/_index.md` 갱신 — 새 top-level 진입점 반영
7. `vault/CLAUDE.md` 갱신 — 새 구조 안내, generated block 룰 추가
8. `harness/policies/knowledge-base-policy.md` 갱신 — vault 내부 택소노미 cross-link 추가 (예: "vault 내부 결정 트리는 `vault/wiki/guides/document-placement.md` 참조")

## 비범위

- **Sub 2:** 600+ 기존 파일 감사 + 분류 매트릭스 (이동/유지/병합/삭제 판정)
- **Sub 3:** 일괄 이관 + wikilink 재작성 + git history
- **Sub 4:** `_index.md`, `services/*/`, `processes/*/` 인덱스 자동 생성기
- **Sub 5:** `sync_harness_links.py` 실 구현 + `ad:harness-optimize` lint 통합
- **Sub 6:** 야간 auto-prep 자동화 (cron + LLM 분석 + `processes/tickets/auto-prep/` 작성)
- **Sub 7:** 모든 `/ad:*` 스킬 본문 일괄 갱신

## 검증 기준

- 5개 guides 문서가 vault에 작성·commit됨
- `vault/_index.md`, `vault/CLAUDE.md`, `harness/policies/knowledge-base-policy.md` cross-link 일관 (서로 끊긴 링크 0)
- 마이그레이션 0건 (구조 정의만 — 실제 파일 이동은 Sub 2~3)
- `harness/policies/knowledge-base-policy.md` 결정 트리 vs `vault/wiki/guides/document-placement.md` 의미 일치 (모순 0)
- `vault/wiki/guides/skills-integration.md`에 명시된 스킬별 경로가 현 스킬 본문과 어떤 불일치를 갖는지 surface(Sub 7 입력)
