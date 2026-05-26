# /ad:* 스킬 본문 vault 경로 갱신 (Sub 7) 구현 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** spec `2026-05-27-ad-skills-vault-paths-design.md`에 따라 `.claude/commands/ad/*.md` 10개 스킬 본문의 옛 vault 경로를 새 택소노미(processes/services)로 갱신하고, frontmatter 표준·결정 트리 cross-link를 추가한다.

**Architecture:** Edit/Write 도구 기반 텍스트 갱신. 스킬별로 1~3 Edit. 단일 harness commit으로 통합.

**Tech Stack:** 변경 없음 (markdown 텍스트).

**경로 약어:**
- `REPO` = `/Users/jm/Documents/workspace/team2`
- VAULT abs prefix in skill bodies: `/Users/user/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/`

**규칙:**
- harness branch = `feature/knowledge-scope-separation`
- commit 사용자 승인 후
- AI footer 금지

---

## File Structure

### 갱신 (10 파일)
- `REPO/.claude/commands/ad/work-prep.md`
- `REPO/.claude/commands/ad/weekly-report.md`
- `REPO/.claude/commands/ad/weekly-planned.md`
- `REPO/.claude/commands/ad/sprint-close-check.md`
- `REPO/.claude/commands/ad/capacity-plan.md`
- `REPO/.claude/commands/ad/service-activity.md`
- `REPO/.claude/commands/ad/ticket.md`
- `REPO/.claude/commands/ad/okr.md` (frontmatter 추가만)
- `REPO/.claude/commands/ad/data-request.md` (출력 위치 안내)
- `REPO/.claude/commands/ad/harness-optimize.md` (frontmatter validation 추가)

---

## Phase 0: 사전 점검

### Task 0.1: 잔존 옛 경로 grep

- [ ] **Step 1: 패턴별 grep**

```bash
cd /Users/jm/Documents/workspace/team2
for p in "wiki/daily/" "wiki/meetings/" "wiki/tickets/" "wiki/okr/" "wiki/domains/" "wiki/inventory/" "wiki/contracts/" "wiki/capacity/" "wiki/weekly/"; do
  echo "=== $p ==="
  grep -rln --include='*.md' "$p" .claude/commands/ad/ 2>/dev/null | head -5
done
```

Expected: 스킬별 옛 경로 사용 매트릭스 surface. 어느 스킬을 어떤 패턴으로 갱신할지 명확화.

### Task 0.2: vault 새 dir 존재 확인

- [ ] **Step 1: 새 경로 모두 존재**

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
for d in wiki/processes/{daily,meetings,weekly,tickets,okr,incidents,capacity,team}; do
  [ -d "$VAULT/$d" ] && echo "OK $d" || echo "MISSING $d"
done
[ -f "$VAULT/wiki/processes/tickets/_index.md" ] && echo "OK tickets/_index" || echo "MISSING tickets/_index"
```

Expected: weekly만 누락일 수 있음 (Sub 4 미생성). 다른 dir 모두 존재.

---

## Phase 1: 스킬 본문 갱신

### Task 1.1: `work-prep.md` 갱신

**Files:**
- Modify: `REPO/.claude/commands/ad/work-prep.md`

- [ ] **Step 1: 본문 grep로 갱신 대상 찾기**

```bash
grep -n "wiki/daily\|wiki/tickets\|wiki/meetings\|daily 문서\|티켓 노트" /Users/jm/Documents/workspace/team2/.claude/commands/ad/work-prep.md | head
```

- [ ] **Step 2: 옛 경로 → 새 경로 일괄 교체**

work-prep 본문 안 다음 패턴 Edit (각 패턴 file 안 unique한 경우만; 중복이면 replace_all=true):

| 옛 | 새 |
|---|---|
| `wiki/daily/` | `wiki/processes/daily/` |
| `wiki/tickets/` | `wiki/processes/tickets/in-progress/` (작업 시작 시) |
| `wiki/meetings/` | `wiki/processes/meetings/` |
| 옛 daily 문서 경로 표현 | `wiki/processes/daily/{date}.md` |

- [ ] **Step 3: auto-prep 입력 단계 추가**

work-prep 본문 적절 위치 (입력 처리 단계)에 다음 단락 삽입:

```markdown
### 사전 분석 (auto-prep) 활용

vault `wiki/processes/tickets/auto-prep/{DEV2-id}.md` 존재 시 (야간 자동 분석 산출물) 본문을 시작점으로 정리한다. 사람 검토 → in-progress로 이동.
```

- [ ] **Step 4: frontmatter 표준 안내 추가**

work-prep 본문에 출력 파일 frontmatter 예시 추가:

```markdown
### 출력 frontmatter

\`\`\`yaml
---
type: ticket
ticket_id: DEV2-XXXX
ticket_status: in-progress
assignee: jmkim
service: max
sprint: 2026-05
type_yt: feature | task | bug
---
\`\`\`

상세: vault `wiki/guides/frontmatter-spec.md`.
```

- [ ] **Step 5: 결정 트리 cross-link**

본문 적절 위치에 한 줄:

```
> 문서 위치 결정: harness `policies/knowledge-base-policy.md` (repo↔vault 경계) + vault `wiki/guides/document-placement.md` (vault 내부 트리).
```

### Task 1.2: `weekly-report.md` 갱신

**Files:**
- Modify: `REPO/.claude/commands/ad/weekly-report.md`

- [ ] **Step 1: grep**

```bash
grep -n "wiki/weekly\|wiki/tickets\|티켓 노트\|주간업무 보고서" /Users/jm/Documents/workspace/team2/.claude/commands/ad/weekly-report.md | head
```

- [ ] **Step 2: 옛 경로 → 새 경로**

| 옛 | 새 |
|---|---|
| `wiki/weekly/` | `wiki/processes/weekly/` |
| `wiki/tickets/` (수집) | `wiki/processes/tickets/` (모든 status subdir 재귀) |
| `wiki/meetings/` | `wiki/processes/meetings/` |

- [ ] **Step 3: 수집 방식 안내**

스킬 본문 안 "데이터 수집" 단락 부근에 추가:

```markdown
### 데이터 수집 패턴

vault `wiki/processes/tickets/`를 재귀 탐색해 frontmatter parse. 필터:
- `assignee == {본인 id}`
- `sprint == {YYYY-MM}`
- `ticket_status in (in-progress, done)`

YouTrack 직접 조회와 vault frontmatter 보조 병행.
```

- [ ] **Step 4: 양식 source of truth 라인 유지**

본문에 이미 KB `DEV2-A-696` source of truth 표현 있으면 유지. 없으면 추가:

```
양식의 source of truth는 YouTrack KB `DEV2-A-696` 원본. 가이드 `docs/sprint/weekly-report-guide.md` §5 템플릿과 KB가 다르면 KB 따른다.
```

### Task 1.3: `weekly-planned.md` 갱신

**Files:**
- Modify: `REPO/.claude/commands/ad/weekly-planned.md`

- [ ] **Step 1: grep + 교체**

```bash
grep -n "wiki/weekly\|wiki/meetings" /Users/jm/Documents/workspace/team2/.claude/commands/ad/weekly-planned.md | head
```

옛 → 새 (Edit):

| 옛 | 새 |
|---|---|
| `wiki/weekly/` | `wiki/processes/weekly/` |
| `wiki/meetings/` | `wiki/processes/meetings/` |

### Task 1.4: `sprint-close-check.md` 갱신

**Files:**
- Modify: `REPO/.claude/commands/ad/sprint-close-check.md`

- [ ] **Step 1: grep + 교체**

| 옛 | 새 |
|---|---|
| `wiki/tickets/` | `wiki/processes/tickets/` |

- [ ] **Step 2: frontmatter 필터 안내**

본문 적절 위치에:

```markdown
### 데이터 source

YouTrack 본문 + vault `wiki/processes/tickets/` frontmatter:
- `assignee`, `ticket_status`, `sprint`, `service` 필드 활용
- tag(`{YYMM}-planned`)는 YouTrack 직접 조회
```

### Task 1.5: `capacity-plan.md` 갱신

**Files:**
- Modify: `REPO/.claude/commands/ad/capacity-plan.md`

- [ ] **Step 1: grep + 교체**

| 옛 | 새 |
|---|---|
| `wiki/capacity/` 또는 옛 저장 경로 | `wiki/processes/capacity/{YYYY-MM}.md` |

- [ ] **Step 2: 저장 시 frontmatter 안내**

```markdown
### 저장 frontmatter

\`\`\`yaml
---
type: capacity-plan
year: 2026
month: 6
assignees: [jmkim, heum2, pms0905, hyeryun]
updated_at: 2026-05-27
---
\`\`\`
```

### Task 1.6: `service-activity.md` 갱신

**Files:**
- Modify: `REPO/.claude/commands/ad/service-activity.md`

- [ ] **Step 1: grep + 교체**

| 옛 | 새 |
|---|---|
| 옛 vault 저장 경로 | `wiki/services/{service_id}/processes/activity-{period}.md` |

- [ ] **Step 2: frontmatter 필터 안내**

```markdown
### 데이터 source

YouTrack 태그 매칭 + vault frontmatter 보조:
- `frontmatter.service == {service_id}` 인 ticket 산출물
- 기간: 명시 또는 `{이번주|지난주|Nd|YYYY-MM-DD..YYYY-MM-DD}`
```

### Task 1.7: `ticket.md` 갱신

**Files:**
- Modify: `REPO/.claude/commands/ad/ticket.md`

- [ ] **Step 1: grep**

```bash
grep -n "wiki/\|docs/okr/" /Users/jm/Documents/workspace/team2/.claude/commands/ad/ticket.md
```

- [ ] **Step 2: 옛 경로 교체**

이전 Phase 5에서 `docs/okr/` → `Obsidian vault wiki/okr/` 갱신됨. 추가로 `wiki/okr/` → `wiki/processes/okr/`로 정정.

| 옛 | 새 |
|---|---|
| `Obsidian vault wiki/okr/` | `vault wiki/processes/okr/` |
| `wiki/tickets/` (있으면) | `wiki/processes/tickets/` |

### Task 1.8: `okr.md` 갱신 (frontmatter 표준)

**Files:**
- Modify: `REPO/.claude/commands/ad/okr.md`

- [ ] **Step 1: 경로 잔존 확인**

```bash
grep -n "wiki/okr/\|vault wiki/okr" /Users/jm/Documents/workspace/team2/.claude/commands/ad/okr.md
```

Expected: Phase 5에서 갱신됨. 잔존 시 `vault wiki/processes/okr/`로 정정.

- [ ] **Step 2: frontmatter 안내 추가**

본문 끝부근에:

```markdown
### OKR 문서 frontmatter

\`\`\`yaml
---
type: okr
title: 김정민 2026 Q2 개인 OKR
year: 2026
quarter: 2
scope: team | personal
assignee: jmkim  # personal일 때
updated_at: 2026-05-27
---
\`\`\`

상세: vault `wiki/guides/frontmatter-spec.md`.
```

### Task 1.9: `data-request.md` 갱신

**Files:**
- Modify: `REPO/.claude/commands/ad/data-request.md`

- [ ] **Step 1: grep**

Phase 5에서 일부 갱신됨. 잔존 옛 경로 점검:

```bash
grep -n "wiki/inventory\|wiki/tickets" /Users/jm/Documents/workspace/team2/.claude/commands/ad/data-request.md | head
```

- [ ] **Step 2: 경로 갱신**

| 옛 | 새 |
|---|---|
| `vault wiki/inventory/` | `vault wiki/services/{svc}/analysis/` |
| `wiki/tickets/` | `wiki/processes/tickets/{status}/` |

- [ ] **Step 3: 결과물 위치 안내 추가**

```markdown
### 결과물 위치

운영 데이터 추출 SQL = `data-requests-dev2` repo SSOT. vault에 두는 것 = 해석·요약 노트:
- 특정 티켓 산출물 → `wiki/processes/tickets/{status}/{DEV2-id}.md`
- 서비스 분석 결과 → `wiki/services/{svc}/analysis/{topic}.md`
- 도메인 인벤토리 → `wiki/services/{svc}/analysis/` 또는 별도 도구로 graph 생성
```

### Task 1.10: `harness-optimize.md` 갱신 (frontmatter validation)

**Files:**
- Modify: `REPO/.claude/commands/ad/harness-optimize.md`

- [ ] **Step 1: 기존 drift 점검 섹션 확인**

```bash
grep -n "드리프트\|generated:harness\|frontmatter" /Users/jm/Documents/workspace/team2/.claude/commands/ad/harness-optimize.md
```

- [ ] **Step 2: frontmatter 검증 단계 추가**

본문 `## repo↔vault 드리프트 점검` 섹션 끝에:

```markdown
### frontmatter 스키마 검증

vault 티켓 산출물 frontmatter 표준 준수 확인:

\`\`\`bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
for f in $(find "$VAULT/wiki/processes/tickets" -name '*.md' ! -name '_index.md'); do
  for key in ticket_id ticket_status assignee service sprint; do
    grep -q "^$key:" "$f" || echo "MISSING $key in $(basename $f)"
  done
done
\`\`\`

누락 필드 surface된 row는 사람 검토.

### generated block 드리프트

\`\`\`bash
python3 tools/sync_harness_links.py --vault "$VAULT" --harness . 2>&1 | grep -E "replaced|skipped|missing"
\`\`\`

`replaced` 발견되면 sync 실행해 차이 반영.
```

---

## Phase 2: 검증 + commit

### Task 2.1: 옛 경로 잔존 검사

- [ ] **Step 1: 패턴별 grep**

```bash
cd /Users/jm/Documents/workspace/team2
PATTERNS=("wiki/daily/" "wiki/meetings/" "wiki/tickets/" "wiki/okr/" "wiki/domains/" "wiki/inventory/" "wiki/contracts/" "wiki/capacity/" "wiki/weekly/")
for p in "${PATTERNS[@]}"; do
  hits=$(grep -rln --include='*.md' "$p" .claude/commands/ad/ 2>/dev/null)
  if [ -n "$hits" ]; then
    echo "=== JANJON $p ==="
    grep -rn --include='*.md' "$p" .claude/commands/ad/ | grep -v 'wiki/processes/' | grep -v 'wiki/services/' | head -3
  fi
done
```

Expected: 0 잔존 (의도된 표현, 예: 옛-새 매핑 설명에 등장하는 경우만).

### Task 2.2: 스킬 chain 일관성

- [ ] **Step 1: in-progress / auto-prep 경로 cross-reference**

```bash
grep -l "processes/tickets/in-progress" .claude/commands/ad/
grep -l "processes/tickets/auto-prep" .claude/commands/ad/
```

Expected: work-prep 명시. weekly-report, sprint-close-check도 tickets 경로 일관.

### Task 2.3: harness commit

**Files:** 10개 스킬 + plan

- [ ] **Step 1: staging**

```bash
cd /Users/jm/Documents/workspace/team2
git add .claude/commands/ad/work-prep.md .claude/commands/ad/weekly-report.md .claude/commands/ad/weekly-planned.md .claude/commands/ad/sprint-close-check.md .claude/commands/ad/capacity-plan.md .claude/commands/ad/service-activity.md .claude/commands/ad/ticket.md .claude/commands/ad/okr.md .claude/commands/ad/data-request.md .claude/commands/ad/harness-optimize.md docs/superpowers/plans/2026-05-27-ad-skills-vault-paths.md
git status --short | head
```

- [ ] **Step 2: commit (사용자 승인 후)**

```bash
git commit -m "ad: 10개 스킬 본문 vault 경로 갱신 (Sub 7)

옛 wiki/{daily,meetings,tickets,okr,domains,inventory,contracts,capacity,weekly}/ → 새 wiki/processes/{*} 또는 wiki/services/{svc}/{*}. frontmatter 표준 안내 + 결정 트리 cross-link 추가. work-prep: auto-prep 입력, harness-optimize: frontmatter validation·sync drift 점검 단계 추가."
```

- [ ] **Step 3: footer 검사**

```bash
git log -1 --pretty=format:"%B" | grep -iE "(co-authored-by|🤖 generated|generated with claude code)" && echo BAD || echo OK
```

Expected: `OK`.

---

## Self-Review

**Spec 커버리지:**
- work-prep auto-prep + in-progress + daily 아젠다 (Task 1.1) ✓
- weekly-report frontmatter query (Task 1.2) ✓
- weekly-planned 경로 (Task 1.3) ✓
- sprint-close-check 필터 (Task 1.4) ✓
- capacity-plan 저장 위치·frontmatter (Task 1.5) ✓
- service-activity 필터·저장 (Task 1.6) ✓
- ticket 경로 정정 (Task 1.7) ✓
- okr frontmatter (Task 1.8) ✓
- data-request 결과물 위치 (Task 1.9) ✓
- harness-optimize frontmatter validation + sync drift (Task 1.10) ✓
- 공통 결정 트리 cross-link (각 Task) ✓
- 공통 frontmatter 표준 안내 (각 Task) ✓

**Placeholder 없음:** 모든 Step 실 코드/명령/매핑.

**타입 일관:**
- vault 경로 prefix 표현 일관: `wiki/processes/`, `wiki/services/{svc}/`
- frontmatter 필드: ticket_id, ticket_status, assignee, service, sprint 일관
- ticket_status enum: auto-prep | in-progress | done | backlog 일관

빠진 부분 없음.

## 검증 기준

- 옛 경로 잔존 grep 결과 0 (의도된 매핑 설명 제외)
- frontmatter 표준 안내 ticket-handling 스킬 모두에 포함됨
- 결정 트리 cross-link 모든 스킬에 포함됨
- harness commit 1건
- AI footer 0건
