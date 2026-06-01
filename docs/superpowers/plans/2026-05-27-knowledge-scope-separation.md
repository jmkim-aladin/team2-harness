# 지식 저장소 범위 분리 — 구현 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 팀 하네스(repo, "어떻게 일하나")와 로컬 위키(Obsidian vault, "무엇을 일하나") 경계를 명확화하고, repo 내 vault 성격 문서(`wiki/`, `docs/DEV2-*`, `docs/designs/`, `docs/okr/`, 도메인 가이드, 운영 신청)를 vault로 이관하며, 정책·CLAUDE.md·스킬을 갱신해 지속 기록 메커니즘을 4-layer로 구축한다.

**Architecture:** 단일 PR에서 (1) vault에 파일 추가 커밋 (2) repo에서 파일 제거 + 정책·CLAUDE·스킬 갱신 커밋을 묶어 처리한다. cross-repo 이관이므로 `git mv` 대신 `cp` + `git rm` 사용. 이관 후 repo grep으로 끊긴 링크와 잔존 참조를 점검한다.

**Tech Stack:** Bash, git, markdown. 코드 변경 없음. 모든 변경은 문서·정책·스킬 텍스트.

**경로 약어:**
- `REPO` = `/Users/jm/Documents/workspace/team2`
- `VAULT` = `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2`

**중요 규칙 (CLAUDE.md):**
- 모든 git commit/push, YouTrack 변경은 사용자 확인 후 수행
- 커밋 메시지에 `Co-Authored-By: Claude ...` 또는 도구 자기참조 footer 금지

---

## File Structure

### vault landing 매핑

| repo 원본 | vault 대상 |
|---|---|
| `REPO/wiki/inventory/aladin-infra-login-history.md` | `VAULT/wiki/inventory/` |
| `REPO/wiki/inventory/max-search-batch-sql.md` | `VAULT/wiki/inventory/` |
| `REPO/docs/DEV2-5283-subtask-updates-0420.md` | `VAULT/wiki/tickets/` |
| `REPO/docs/DEV2-5544-audiobook-runtime-query.md` | `VAULT/wiki/tickets/` |
| `REPO/docs/DEV2-5749-multicampus-srv1119-april-order-export.md` | `VAULT/wiki/tickets/` |
| `REPO/docs/shopping-order-domain-guide.md` | `VAULT/wiki/domains/` |
| `REPO/docs/shopping-packman-domain-guide.md` | `VAULT/wiki/domains/` |
| `REPO/docs/max-api-core-dev-firewall-application.md` | `VAULT/wiki/proposals/` |
| `REPO/docs/designs/storefront/` (전체) | `VAULT/wiki/projects/storefront/` |
| `REPO/docs/designs/hybrid-db-service-layer-process.md` | `VAULT/wiki/processes/` |
| `REPO/docs/designs/operational-knowledge-wiki.md` | `VAULT/wiki/projects/operational-knowledge-wiki/` |
| `REPO/docs/okr/*.md` | `VAULT/wiki/okr/` (신규 생성) |
| `REPO/docs/okr/performance-review-guide.md` | `VAULT/wiki/okr/` |

### repo 잔류 (변경 없음)
- `docs/analysis-guides.md`, `db-migration-cdc-assessment-guide.md`, `gstack-usage-guide.md`, `harness-guide.md`, `legacy-modernization-db-separation-analysis-guide.md`, `ralph-loop-*.md`, `service-harness-setup.md`, `setup-guide.md`, `team-harness-design.md`, `wiki-navigation-guide.md`
- `docs/sprint/`, `docs/superpowers/`

### 갱신 대상 파일
- `REPO/policies/knowledge-base-policy.md` — 전면 재작성
- `REPO/policies/wiki-document-language-and-title-policy.md` — 영향부 갱신
- `REPO/policies/claude-md-policy.md` — 영향부 갱신
- `REPO/CLAUDE.md` — 핵심 규칙 + Skill routing
- `VAULT/CLAUDE.md` — 정책 source 참조
- `REPO/.claude/commands/ad/work-prep.md` — 문서 위치 결정 단계
- `REPO/.claude/commands/ad/harness-optimize.md` — 드리프트 점검 절차
- repo 내 grep 결과에 따른 docs 참조 갱신
- `REPO/policies/data-request-policy.md` — DEV2-* 산출물 위치 표현 영향 시
- memory: `reference_obsidian_vault.md` 확장, 신규 `feedback_doc_placement.md`

### 삭제 대상
- `REPO/wiki/` (빈 디렉터리)
- `REPO/docs/hiring/` (.DS_Store 외 콘텐츠 없음)
- `REPO/docs/incidents/` (빈 디렉터리)

---

## Phase 0: 사전 점검

### Task 0.1: 작업 브랜치 생성

**Files:** N/A (git 상태만 영향)

- [ ] **Step 1: 현재 상태 확인**

```bash
cd /Users/jm/Documents/workspace/team2
git status --short
git branch --show-current
```

Expected: 현재 브랜치가 main이고, untracked 파일 다수 (스프린트 작업물). 작업 시작 전 사용자 확인.

- [ ] **Step 2: 작업 브랜치 분기 (사용자 승인 후)**

```bash
git checkout -b feature/knowledge-scope-separation
```

Expected: `Switched to a new branch 'feature/knowledge-scope-separation'`

### Task 0.2: 매핑 검증

**Files:** N/A

- [ ] **Step 1: vault landing 경로 존재 확인 및 누락 디렉터리 surface**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
for d in wiki/inventory wiki/tickets wiki/domains wiki/proposals wiki/projects wiki/processes wiki/decisions; do
  [ -d "$VAULT/$d" ] && echo "OK $d" || echo "MISSING $d"
done
```

Expected: 모두 OK (Phase 0 점검에서 확인된 vault `wiki/` 하위 구조와 일치). 누락 발견 시 Task 1.x 시작 전 디렉터리 생성.

- [ ] **Step 2: `wiki/okr/` 신규 디렉터리 표시 (실제 생성은 Task 1.7에서)**

```bash
[ -d "$VAULT/wiki/okr" ] && echo "이미 존재" || echo "신규 생성 필요 (Task 1.7)"
```

---

## Phase 1: 파일 이관 (vault 추가 → repo 제거)

> **공통 원칙:** 각 Task에서 vault에 파일 복사 + vault 커밋 → repo에서 파일 제거 → repo 커밋 (Phase 2 이후 정책 갱신과 묶을 수도 있음). cross-repo이므로 history 보존 불가. 커밋 메시지에 출처 명시.

### Task 1.1: repo `wiki/inventory/` 이관

**Files:**
- Move: `REPO/wiki/inventory/aladin-infra-login-history.md` → `VAULT/wiki/inventory/aladin-infra-login-history.md`
- Move: `REPO/wiki/inventory/max-search-batch-sql.md` → `VAULT/wiki/inventory/max-search-batch-sql.md`

- [ ] **Step 1: 충돌 확인**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
ls "$VAULT/wiki/inventory/aladin-infra-login-history.md" 2>/dev/null && echo "충돌!" || echo "OK"
ls "$VAULT/wiki/inventory/max-search-batch-sql.md" 2>/dev/null && echo "충돌!" || echo "OK"
```

Expected: 둘 다 OK (vault에 동명 파일 없음). 충돌 시 user 확인 필요.

- [ ] **Step 2: vault로 복사**

```bash
REPO="/Users/jm/Documents/workspace/team2"
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
cp "$REPO/wiki/inventory/aladin-infra-login-history.md" "$VAULT/wiki/inventory/"
cp "$REPO/wiki/inventory/max-search-batch-sql.md" "$VAULT/wiki/inventory/"
```

- [ ] **Step 3: vault 커밋 (사용자 승인 후)**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git add wiki/inventory/aladin-infra-login-history.md wiki/inventory/max-search-batch-sql.md
git status --short
git commit -m "wiki/inventory: team2 하네스에서 인벤토리 2건 이관

출처: AladinCommunication/team2 repo wiki/inventory/
이관 사유: knowledge-base-policy 갱신에 따라 도메인·운영 인벤토리 SSOT를 vault로 일원화"
```

Expected: 커밋 1건 생성, 2개 파일 추가.

- [ ] **Step 4: repo에서 제거**

```bash
cd /Users/jm/Documents/workspace/team2
git rm wiki/inventory/aladin-infra-login-history.md wiki/inventory/max-search-batch-sql.md
rmdir wiki/inventory wiki 2>/dev/null || echo "wiki/ 비어있지 않음 — 내용 확인"
ls wiki 2>/dev/null && echo "wiki/ 잔존" || echo "wiki/ 제거됨"
```

Expected: wiki/inventory/ 및 wiki/ 디렉터리 모두 제거.

- [ ] **Step 5: repo 커밋은 Phase 5 정책 갱신과 묶음**

(이 시점에 repo 측 `git rm`만 적용, 커밋은 Phase 5 종합 커밋에서 처리.)

### Task 1.2: `docs/DEV2-*.md` 3건 이관

**Files:**
- Move: `REPO/docs/DEV2-5283-subtask-updates-0420.md` → `VAULT/wiki/tickets/`
- Move: `REPO/docs/DEV2-5544-audiobook-runtime-query.md` → `VAULT/wiki/tickets/`
- Move: `REPO/docs/DEV2-5749-multicampus-srv1119-april-order-export.md` → `VAULT/wiki/tickets/`

- [ ] **Step 1: 충돌 확인**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
for f in DEV2-5283-subtask-updates-0420.md DEV2-5544-audiobook-runtime-query.md DEV2-5749-multicampus-srv1119-april-order-export.md; do
  ls "$VAULT/wiki/tickets/$f" 2>/dev/null && echo "충돌 $f" || echo "OK $f"
done
```

Expected: 3건 모두 OK.

- [ ] **Step 2: vault로 복사**

```bash
REPO="/Users/jm/Documents/workspace/team2"
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
cp "$REPO/docs/DEV2-5283-subtask-updates-0420.md" "$VAULT/wiki/tickets/"
cp "$REPO/docs/DEV2-5544-audiobook-runtime-query.md" "$VAULT/wiki/tickets/"
cp "$REPO/docs/DEV2-5749-multicampus-srv1119-april-order-export.md" "$VAULT/wiki/tickets/"
```

- [ ] **Step 3: vault 커밋 (사용자 승인 후)**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git add wiki/tickets/DEV2-5283-subtask-updates-0420.md wiki/tickets/DEV2-5544-audiobook-runtime-query.md wiki/tickets/DEV2-5749-multicampus-srv1119-april-order-export.md
git commit -m "wiki/tickets: DEV2-* 티켓 산출물 3건 이관

출처: AladinCommunication/team2 repo docs/
이관 사유: 티켓별 운영 분석·추출 결과는 vault SSOT"
```

- [ ] **Step 4: repo에서 제거**

```bash
cd /Users/jm/Documents/workspace/team2
git rm docs/DEV2-5283-subtask-updates-0420.md docs/DEV2-5544-audiobook-runtime-query.md docs/DEV2-5749-multicampus-srv1119-april-order-export.md
```

Expected: 3건 stage 처리.

### Task 1.3: 도메인 가이드 2건 이관

**Files:**
- Move: `REPO/docs/shopping-order-domain-guide.md` → `VAULT/wiki/domains/`
- Move: `REPO/docs/shopping-packman-domain-guide.md` → `VAULT/wiki/domains/`

- [ ] **Step 1: 충돌 확인**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
ls "$VAULT/wiki/domains/shopping-order-domain-guide.md" 2>/dev/null && echo "충돌" || echo "OK"
ls "$VAULT/wiki/domains/shopping-packman-domain-guide.md" 2>/dev/null && echo "충돌" || echo "OK"
```

Expected: 둘 다 OK.

- [ ] **Step 2: vault 복사**

```bash
REPO="/Users/jm/Documents/workspace/team2"
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
cp "$REPO/docs/shopping-order-domain-guide.md" "$VAULT/wiki/domains/"
cp "$REPO/docs/shopping-packman-domain-guide.md" "$VAULT/wiki/domains/"
```

- [ ] **Step 3: vault 커밋 (사용자 승인 후)**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git add wiki/domains/shopping-order-domain-guide.md wiki/domains/shopping-packman-domain-guide.md
git commit -m "wiki/domains: shopping 도메인 가이드 2건 이관

출처: AladinCommunication/team2 repo docs/
이관 사유: 서비스 도메인 지식 SSOT는 vault"
```

- [ ] **Step 4: repo 제거**

```bash
cd /Users/jm/Documents/workspace/team2
git rm docs/shopping-order-domain-guide.md docs/shopping-packman-domain-guide.md
```

### Task 1.4: 운영 신청 문서 1건 이관

**Files:**
- Move: `REPO/docs/max-api-core-dev-firewall-application.md` → `VAULT/wiki/proposals/`

- [ ] **Step 1: 충돌 확인**

```bash
ls "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/proposals/max-api-core-dev-firewall-application.md" 2>/dev/null && echo "충돌" || echo "OK"
```

Expected: OK.

- [ ] **Step 2: vault 복사**

```bash
cp "/Users/jm/Documents/workspace/team2/docs/max-api-core-dev-firewall-application.md" "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/proposals/"
```

- [ ] **Step 3: vault 커밋 (사용자 승인 후)**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git add wiki/proposals/max-api-core-dev-firewall-application.md
git commit -m "wiki/proposals: max-api core-dev 방화벽 신청 문서 이관

출처: AladinCommunication/team2 repo docs/
이관 사유: 운영 신청·승인 산출물 SSOT는 vault"
```

- [ ] **Step 4: repo 제거**

```bash
cd /Users/jm/Documents/workspace/team2
git rm docs/max-api-core-dev-firewall-application.md
```

### Task 1.5: `docs/designs/storefront/` 이관

**Files:**
- Move: `REPO/docs/designs/storefront/` (전체) → `VAULT/wiki/projects/storefront/`

- [ ] **Step 1: vault 측 충돌 확인**

```bash
ls "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/projects/storefront" 2>/dev/null && echo "충돌!" || echo "OK"
```

Expected: OK.

- [ ] **Step 2: vault로 디렉터리 복사 (`.DS_Store` 제외)**

```bash
REPO="/Users/jm/Documents/workspace/team2"
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
mkdir -p "$VAULT/wiki/projects/storefront"
rsync -av --exclude='.DS_Store' "$REPO/docs/designs/storefront/" "$VAULT/wiki/projects/storefront/"
find "$VAULT/wiki/projects/storefront" -name '.DS_Store' -delete
```

Expected: storefront/ 전체 내용 (README.md, admin/, architecture/, domain/, event-storming/, meetings/, reviews/, scope/, skills-lock.json, storefront-*.md, .agents/) 복사.

- [ ] **Step 3: vault 커밋 (사용자 승인 후)**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git add wiki/projects/storefront
git commit -m "wiki/projects: storefront 설계 문서 일괄 이관

출처: AladinCommunication/team2 repo docs/designs/storefront/
이관 사유: 신규 서비스 설계 진행 산출물은 vault SSOT"
```

- [ ] **Step 4: repo 제거**

```bash
cd /Users/jm/Documents/workspace/team2
git rm -r docs/designs/storefront
```

### Task 1.6: `docs/designs/` 잔여 2개 이관

**Files:**
- Move: `REPO/docs/designs/hybrid-db-service-layer-process.md` → `VAULT/wiki/processes/`
- Move: `REPO/docs/designs/operational-knowledge-wiki.md` → `VAULT/wiki/projects/operational-knowledge-wiki/`

- [ ] **Step 1: 충돌 확인**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
ls "$VAULT/wiki/processes/hybrid-db-service-layer-process.md" 2>/dev/null && echo "충돌" || echo "OK"
ls "$VAULT/wiki/projects/operational-knowledge-wiki" 2>/dev/null && echo "충돌" || echo "OK"
```

Expected: 둘 다 OK.

- [ ] **Step 2: vault 복사**

```bash
REPO="/Users/jm/Documents/workspace/team2"
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
cp "$REPO/docs/designs/hybrid-db-service-layer-process.md" "$VAULT/wiki/processes/"
mkdir -p "$VAULT/wiki/projects/operational-knowledge-wiki"
cp "$REPO/docs/designs/operational-knowledge-wiki.md" "$VAULT/wiki/projects/operational-knowledge-wiki/"
```

- [ ] **Step 3: vault 커밋 (사용자 승인 후)**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git add wiki/processes/hybrid-db-service-layer-process.md wiki/projects/operational-knowledge-wiki/operational-knowledge-wiki.md
git commit -m "wiki: designs 잔여 2건 이관 (hybrid-db process, operational-knowledge-wiki 설계)

출처: AladinCommunication/team2 repo docs/designs/
이관 사유: 프로세스/설계 산출물은 vault SSOT"
```

- [ ] **Step 4: repo 제거 (`docs/designs/` 완전 삭제)**

```bash
cd /Users/jm/Documents/workspace/team2
git rm docs/designs/hybrid-db-service-layer-process.md docs/designs/operational-knowledge-wiki.md
# storefront는 Task 1.5에서 이미 제거됨
rmdir docs/designs 2>/dev/null && echo "docs/designs 제거됨" || ls docs/designs
```

Expected: docs/designs/ 디렉터리 부재.

### Task 1.7: `docs/okr/` 이관

**Files:**
- Move: `REPO/docs/okr/*.md` (10건) → `VAULT/wiki/okr/`

- [ ] **Step 1: vault `wiki/okr/` 디렉터리 생성**

```bash
mkdir -p "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/okr"
```

- [ ] **Step 2: vault로 복사**

```bash
cp /Users/jm/Documents/workspace/team2/docs/okr/*.md "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/okr/"
ls "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/okr/" | wc -l
```

Expected: 10건 (2026-q1-*, 2026-q2-*, 2026-q3-kimjeongmin.md, 2026-q4-kimjeongmin.md, 2026-team-okr.md, performance-review-guide.md).

- [ ] **Step 3: vault 커밋 (사용자 승인 후)**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git add wiki/okr
git commit -m "wiki/okr: 팀/개인 OKR 문서 일괄 이관

출처: AladinCommunication/team2 repo docs/okr/
이관 사유: OKR 본문은 운영 실행 산출물 — vault SSOT
performance-review-guide.md는 동일 도메인 cohesion으로 동반 이관"
```

- [ ] **Step 4: repo 제거**

```bash
cd /Users/jm/Documents/workspace/team2
git rm docs/okr/*.md
rmdir docs/okr 2>/dev/null && echo "docs/okr 제거됨" || ls docs/okr
```

### Task 1.8: 빈/잔존 디렉터리 제거

**Files:**
- Delete: `REPO/docs/hiring/` (`.DS_Store` 외 콘텐츠 없음)
- Delete: `REPO/docs/incidents/` (빈 디렉터리)
- Delete: `REPO/wiki/` (Task 1.1에서 이미 제거됐어야 함, 잔존 시 처리)

- [ ] **Step 1: 콘텐츠 재확인**

```bash
find docs/hiring -type f 2>/dev/null
find docs/incidents -type f 2>/dev/null
find wiki -type f 2>/dev/null
```

Expected: 모두 빈 결과 (또는 `.DS_Store`만).

- [ ] **Step 2: 디렉터리 삭제 + .DS_Store 정리**

```bash
find docs/hiring docs/incidents wiki -name '.DS_Store' -delete 2>/dev/null
rm -rf docs/hiring docs/incidents wiki
ls docs/hiring docs/incidents wiki 2>/dev/null || echo "모두 제거됨"
```

Expected: 3개 디렉터리 부재.

### Task 1.9: Phase 1 상태 점검

- [ ] **Step 1: repo 잔존 vault 성격 파일 grep**

```bash
cd /Users/jm/Documents/workspace/team2
ls docs/DEV2-*.md 2>/dev/null && echo "잔존 DEV2" || echo "OK"
ls docs/shopping-*-domain-guide.md 2>/dev/null && echo "잔존 domain" || echo "OK"
ls docs/max-api-core-dev-firewall-application.md 2>/dev/null && echo "잔존 max-api" || echo "OK"
ls -d docs/designs docs/okr docs/hiring docs/incidents wiki 2>/dev/null && echo "잔존 dir" || echo "OK"
```

Expected: 모두 OK.

- [ ] **Step 2: git status 확인**

```bash
git status --short | head -40
```

Expected: 이관 대상 파일들이 `D` (deleted) 상태로 stage됨.

---

## Phase 2: 정책 갱신 — `knowledge-base-policy.md` 전면 재작성

### Task 2.1: `knowledge-base-policy.md` 재작성

**Files:**
- Rewrite: `REPO/policies/knowledge-base-policy.md`

- [ ] **Step 1: 기존 파일 읽고 새 본문으로 전면 교체**

새 본문 (Write 도구 사용):

```markdown
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
```

- [ ] **Step 2: 파일 작성 확인**

```bash
head -20 policies/knowledge-base-policy.md
grep -c "team2/wiki/" policies/knowledge-base-policy.md
```

Expected: 새 본문 시작이 출력되고, `team2/wiki/` 참조는 0건.

### Task 2.2: `wiki-document-language-and-title-policy.md` 영향부 갱신

**Files:**
- Modify: `REPO/policies/wiki-document-language-and-title-policy.md`

- [ ] **Step 1: `team2/wiki/` 또는 repo `wiki/` 참조 확인**

```bash
grep -n "team2/wiki\|repo wiki\|\`wiki/" policies/wiki-document-language-and-title-policy.md
```

- [ ] **Step 2: 발견 시 vault 기준으로 표현 갱신**

각 매치를 vault 위치 또는 새 정책 링크로 교체. 표현이 일반적이면 vault SSOT 문구로 다듬는다.

### Task 2.3: `claude-md-policy.md` 영향 확인

**Files:**
- Modify (필요 시): `REPO/policies/claude-md-policy.md`

- [ ] **Step 1: 영향 grep**

```bash
grep -n "team2/wiki\|repo wiki\|운영업무 지식" policies/claude-md-policy.md
```

- [ ] **Step 2: 영향 발견 시만 갱신, 없으면 변경 없음**

### Task 2.4: `data-request-policy.md` 영향 확인

**Files:**
- Modify (필요 시): `REPO/policies/data-request-policy.md`

- [ ] **Step 1: DEV2-* 산출물 위치 표현 확인**

```bash
grep -n "docs/DEV2\|docs/" policies/data-request-policy.md
```

- [ ] **Step 2: 발견 시 vault 위치로 갱신, 또는 data-requests-dev2 repo SSOT 표현은 그대로 유지**

---

## Phase 3: CLAUDE.md 양쪽 동기화

### Task 3.1: repo `CLAUDE.md` 갱신

**Files:**
- Modify: `REPO/CLAUDE.md`

- [ ] **Step 1: 핵심 규칙 line 24 재서술**

기존:
```
- 가이드/정책/스킬은 팀 하네스에, 도메인 분석 결과/Querybook은 로컬 Obsidian 운영 지식 위키에 저장한다
```

신규:
```
- 지식 분리: 팀 하네스(repo) = "어떻게 일하나"(정책·템플릿·카탈로그·스킬), Obsidian vault = "무엇을 일하나"(프로젝트 진행·운영·도메인·회의·일지·OKR·티켓 산출물). 결정 트리는 [policies/knowledge-base-policy.md](./policies/knowledge-base-policy.md) 참조
```

- [ ] **Step 2: Skill routing 표에 "새 문서 작성" 항목 추가**

기존 Skill routing 표 마지막에 다음 두 줄 추가:

```
- 새 문서 작성, 어디에 둘지 결정 → [policies/knowledge-base-policy.md](./policies/knowledge-base-policy.md) 결정 트리 즉시 적용 (사용자에게 매번 묻지 않음)
- 드리프트 점검, repo↔vault 경계 위반 → invoke ad:harness-optimize
```

- [ ] **Step 3: 구조 섹션에 잔존 `wiki/` 참조 확인**

```bash
grep -n "wiki/" CLAUDE.md
```

Expected: `policies/wiki-document-language-and-title-policy.md` 링크 1건만 남음. 다른 wiki/ 참조 발견 시 제거.

### Task 3.2: vault `CLAUDE.md` 갱신

**Files:**
- Modify: `VAULT/CLAUDE.md`

- [ ] **Step 1: 정책 source 참조 명시**

기존 "## 하네스" 섹션을 다음으로 교체:

```markdown
## 하네스

- 팀 하네스 경로: `/Users/user/Documents/workspace/team2`
- 지식 분리 정책 source: `/Users/user/Documents/workspace/team2/policies/knowledge-base-policy.md`
- 이 vault = "무엇을 일하나" (프로젝트 진행·운영·도메인·회의·일지·OKR·티켓 산출물 SSOT)
- 팀 하네스(repo) = "어떻게 일하나" (정책·템플릿·카탈로그·스킬 SSOT)
- 회의록은 KB가 아니라 `wiki/meetings/YYYY-MM-DD-topic.md`에 둔다 (기존 규칙 유지, 정책에서 명시화)
```

- [ ] **Step 2: vault 커밋 (사용자 승인 후)**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git add CLAUDE.md
git commit -m "CLAUDE.md: 지식 분리 정책 source를 팀 하네스로 명시"
```

---

## Phase 4: 스킬 갱신

### Task 4.1: `ad:work-prep` 스킬 갱신

**Files:**
- Modify: `REPO/.claude/commands/ad/work-prep.md`

- [ ] **Step 1: 기존 스킬 본문에 "문서 위치 결정" 단계 추가**

스킬 본문 적절한 위치에 다음 단락 추가:

```markdown
## 문서 위치 결정

작업 중 생성하는 노트·산출물은 `policies/knowledge-base-policy.md`의 결정 트리에 따라 즉시 위치를 결정한다. 매번 사용자에게 묻지 않는다.

- 정책/템플릿/카탈로그/스킬 → repo
- 전사·사내 공통 컨벤션·온보딩 → YouTrack KB
- 운영 데이터 추출 SQL/결과물 → data-requests-dev2 repo
- 특정 서비스 코드와 강결합된 매뉴얼만 → 그 서비스 repo
- 그 외 (프로젝트 진행·운영·도메인·회의·일지·티켓 산출물·OKR) → Obsidian vault
```

### Task 4.2: `ad:harness-optimize` 스킬 갱신

**Files:**
- Modify: `REPO/.claude/commands/ad/harness-optimize.md`

- [ ] **Step 1: 드리프트 점검 절차 추가**

스킬 본문에 다음 섹션 추가:

```markdown
## repo↔vault 드리프트 점검

새 항목이 잘못된 저장소에 들어갔는지 정기 점검한다.

### repo에서 vault 성격 파일 surface

```bash
REPO="/Users/jm/Documents/workspace/team2"
# 운영업무/도메인/회의/티켓/OKR 성격 후보
find "$REPO/docs" -maxdepth 2 -type f -name '*.md' \
  | grep -Ev 'sprint/|superpowers/|setup-guide|harness-guide|gstack-usage-guide|analysis-guides|wiki-navigation-guide|service-harness-setup|team-harness-design|db-migration|legacy-modernization|ralph-loop' \
  | grep -E 'DEV2-|domain-guide|firewall-application|okr|meeting'
```

### vault에서 정책/템플릿 성격 파일 surface

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
find "$VAULT/wiki" -type f -name '*.md' \
  | grep -E 'policy|template|catalog|skill|harness-setup' \
  | head -20
```

### 중복 제목 surface

```bash
REPO="/Users/jm/Documents/workspace/team2"
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
(find "$REPO/docs" "$REPO/policies" "$REPO/templates" "$REPO/catalog" -name '*.md' -exec basename {} \; ;
 find "$VAULT/wiki" -name '*.md' -exec basename {} \;) | sort | uniq -d
```

매치되는 파일은 사용자와 함께 어느 쪽이 SSOT인지 결정 후 반대편 제거.
```

---

## Phase 5: 참조 grep + 일괄 갱신

### Task 5.1: repo 내 끊긴 링크 surface

**Files:**
- Multiple: 잔류 가이드 문서들

- [ ] **Step 1: 이관된 파일 경로 참조 grep**

```bash
cd /Users/jm/Documents/workspace/team2
TARGETS=(
  "docs/DEV2-5283-subtask-updates-0420"
  "docs/DEV2-5544-audiobook-runtime-query"
  "docs/DEV2-5749-multicampus-srv1119-april-order-export"
  "docs/shopping-order-domain-guide"
  "docs/shopping-packman-domain-guide"
  "docs/max-api-core-dev-firewall-application"
  "docs/designs/storefront"
  "docs/designs/hybrid-db-service-layer-process"
  "docs/designs/operational-knowledge-wiki"
  "docs/okr/"
  "team2/wiki"
  "wiki/inventory"
)
for t in "${TARGETS[@]}"; do
  echo "=== $t ==="
  grep -rn "$t" --include='*.md' --include='*.yaml' . 2>/dev/null | grep -v 'docs/superpowers/'
done
```

Expected: 매치 목록 출력. 0건이면 Task 5.2 스킵.

### Task 5.2: 매치 발견 시 갱신

**Files:** 매치된 파일들

- [ ] **Step 1: 각 매치 검토 후 갱신 (vault 위치 링크 또는 정책 링크로)**

원칙:
- 단순 언급 → vault 위치 명시 또는 "Obsidian vault" 표현
- 활성 링크 → 정책 링크 또는 vault 경로 표현
- 정책 본문 인용 → `policies/knowledge-base-policy.md`로 redirect

- [ ] **Step 2: 갱신 후 재grep 0건 확인**

```bash
for t in "${TARGETS[@]}"; do
  grep -rn "$t" --include='*.md' --include='*.yaml' . 2>/dev/null | grep -v 'docs/superpowers/' && echo "잔존"
done
```

### Task 5.3: `team2/wiki/` 표현 전수 점검

- [ ] **Step 1: grep**

```bash
grep -rn "team2/wiki" --include='*.md' --include='*.yaml' . 2>/dev/null | grep -v 'docs/superpowers/'
```

Expected: 0건. 의도된 인용(정책 본문의 옛 표현 예시)이 아닌 한 모두 정리.

---

## Phase 6: 통합 커밋

### Task 6.1: repo 측 종합 커밋

**Files:** 본 Phase에서 변경된 모든 repo 파일

- [ ] **Step 1: git status 확인**

```bash
cd /Users/jm/Documents/workspace/team2
git status --short
```

Expected: 이관 삭제(D) + 정책/CLAUDE/스킬 변경(M) + 신규 spec/plan(?? 또는 A).

- [ ] **Step 2: 스테이징**

```bash
git add policies/knowledge-base-policy.md \
        policies/wiki-document-language-and-title-policy.md \
        policies/claude-md-policy.md \
        policies/data-request-policy.md \
        CLAUDE.md \
        .claude/commands/ad/work-prep.md \
        .claude/commands/ad/harness-optimize.md \
        docs/superpowers/specs/2026-05-27-knowledge-scope-separation-design.md \
        docs/superpowers/plans/2026-05-27-knowledge-scope-separation.md
# Phase 1의 git rm은 이미 stage됨
# Phase 5의 갱신 파일도 stage
git add docs/  # 잔류 가이드 갱신분
```

(실제로는 변경된 파일만 add — 변경 없는 정책 파일은 제외)

- [ ] **Step 3: 커밋 (사용자 승인 후)**

```bash
git commit -m "knowledge-base-policy: 팀 하네스/Obsidian vault 경계 재정의 + 이관

- 정의: repo = '어떻게 일하나' (정책·템플릿·카탈로그·스킬), vault = '무엇을 일하나' (프로젝트·운영·도메인·회의·일지·OKR·티켓 산출물)
- 신규 문서 위치 결정 트리 명시, 회의록 = vault (KB 아님)
- repo wiki/, docs/DEV2-*, docs/shopping-*-domain-guide, docs/max-api-core-dev-firewall-application,
  docs/designs/, docs/okr/, docs/hiring/, docs/incidents/ 일괄 vault 이관 또는 제거
- CLAUDE.md 양쪽(repo·vault) 동기화, 새 문서 작성 라우팅 명시
- ad:work-prep, ad:harness-optimize 스킬 갱신 (위치 결정·드리프트 점검)
"
```

- [ ] **Step 4: 푸시는 PR 단계에서 사용자 승인 후**

(이 시점에 자동 push 금지.)

---

## Phase 7: memory 갱신

### Task 7.1: 기존 memory 확장

**Files:**
- Modify: `/Users/jm/.claude/projects/-Users-jm-Documents-workspace-team2/memory/reference_obsidian_vault.md`

- [ ] **Step 1: 본문 확장**

기존 본문에 다음 라인 추가:

```markdown
- vault = 운영·도메인·회의·일지·OKR·티켓 산출물 SSOT ([[feedback_doc_placement]])
- 정책 source = `policies/knowledge-base-policy.md` (repo)
- 회의록 위치 = `wiki/meetings/YYYY-MM-DD-topic.md`
- OKR 위치 = `wiki/okr/`
- 티켓 산출물 위치 = `wiki/tickets/`
```

### Task 7.2: 신규 memory 작성

**Files:**
- Create: `/Users/jm/.claude/projects/-Users-jm-Documents-workspace-team2/memory/feedback_doc_placement.md`
- Modify: `/Users/jm/.claude/projects/-Users-jm-Documents-workspace-team2/memory/MEMORY.md`

- [ ] **Step 1: feedback_doc_placement.md 작성**

```markdown
---
name: feedback_doc_placement
description: 새 문서 위치 결정 트리 — 매번 사용자에게 묻지 말고 즉시 적용
metadata:
  type: feedback
---

새 문서 작성 시 다음 결정 트리를 즉시 적용한다. 사용자에게 매번 묻지 않는다.

- 팀 정책·규칙·템플릿·카탈로그·스킬 → team2 repo
- 전사·사내 공통 컨벤션·온보딩 → YouTrack KB
- 운영 데이터 추출 SQL/결과물 → data-requests-dev2 repo
- 특정 서비스 코드와만 의미 있는 매뉴얼 → 그 서비스 repo
- 그 외 전부 (프로젝트 진행·운영·도메인·회의·일지·OKR·티켓 산출물·Querybook) → Obsidian vault ([[reference_obsidian_vault]])

판단 모호 시 기본값 = vault.

**Why:** 사용자 명시 — "팀하네스는 가이드·KB·정책, 위키는 업무·운영·도메인 지식 SSOT". 매번 위치 질문 = 마찰. 결정 트리 확정 후 즉시 적용이 사용자 요구.

**How to apply:** 새 `.md` 파일 작성 직전 트리 적용. repo `docs/` 루트나 `policies/`에 운영업무·도메인·티켓 성격 문서를 두려는 경향이 보이면 정지하고 vault로 라우팅. 정책 source = `policies/knowledge-base-policy.md`.
```

- [ ] **Step 2: MEMORY.md 인덱스에 추가**

기존 MEMORY.md 끝에 한 줄 추가:

```markdown
- [새 문서 위치 결정 트리](feedback_doc_placement.md) — repo=어떻게 일하나, vault=무엇을 일하나. 묻지 말고 즉시 라우팅.
```

---

## Phase 8: 최종 검증

### Task 8.1: 검증 체크리스트

- [ ] **Step 1: 이관 검증**

```bash
cd /Users/jm/Documents/workspace/team2
ls docs/DEV2-*.md docs/shopping-*-domain-guide.md docs/max-api-core-dev-firewall-application.md 2>/dev/null | wc -l
ls -d docs/designs docs/okr docs/hiring docs/incidents wiki 2>/dev/null | wc -l
```

Expected: 둘 다 0.

- [ ] **Step 2: 정책·CLAUDE 동기화 검증**

```bash
grep "knowledge-base-policy.md" CLAUDE.md
grep "knowledge-base-policy.md" "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/CLAUDE.md"
```

Expected: 양쪽 모두 매치 1건 이상.

- [ ] **Step 3: 끊긴 링크 검증**

```bash
grep -rn "team2/wiki\|docs/DEV2-\|docs/shopping-.*-domain-guide\|docs/max-api-core-dev-firewall-application\|docs/designs/\|docs/okr/" --include='*.md' --include='*.yaml' . 2>/dev/null | grep -v 'docs/superpowers/' | grep -v "^Binary"
```

Expected: 정책 본문 인용 외 0건.

- [ ] **Step 4: 드리프트 감시 스킬 동작 확인**

```bash
grep -A 5 "drift\|드리프트" .claude/commands/ad/harness-optimize.md | head -20
```

Expected: 신규 절차 본문 출력.

- [ ] **Step 5: vault 측 커밋 로그 확인**

```bash
cd "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
git log --oneline -10
```

Expected: Phase 1·3에서 만든 커밋 7~8건 (`wiki/inventory:`, `wiki/tickets:`, `wiki/domains:`, `wiki/proposals:`, `wiki/projects: storefront`, `wiki: designs 잔여`, `wiki/okr:`, `CLAUDE.md: 정책 source`).

- [ ] **Step 6: repo 측 커밋 로그 확인**

```bash
cd /Users/jm/Documents/workspace/team2
git log --oneline -5
```

Expected: Phase 6의 통합 커밋 1건.

---

## Self-Review

- ✅ 스펙 모든 산출물 A-G 커버 (Phase 1=A, 2=B, 3=C, 4=D, 5=E, 7=F, spec+plan=G)
- ✅ placeholder 없음 (TBD/TODO 없음, 모든 step 실행 가능한 코드 또는 본문 포함)
- ✅ 타입/식별자 일관성: `REPO`/`VAULT` 변수 표기 통일, 파일명 일관, vault 디렉터리명 일관
- ✅ cross-repo `git mv` 불가 사실 명시, cp + git rm 패턴 사용
- ✅ 사용자 승인 게이트 모든 커밋 step에 명시
- ✅ AI co-author footer 금지 규칙 본문에 명시

빠진 부분: vault 측 `_index.md`, `_log.md` 등 인덱스 갱신 — Task 8.1 다음 후속 작업으로 분리 (vault 내부 개편은 차후 별도 작업이라는 spec 결정에 따라).
