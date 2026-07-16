# 하네스 최적화 (업데이트·최신화·중복제거)

하네스 문서의 최신화, 중복 제거, YouTrack KB 동기화를 수행합니다.

> 문서 위치 결정: harness `policies/knowledge-base-policy.md` (repo↔vault 경계) + vault `wiki/guides/document-placement.md` (vault 내부 트리).

## 사용법

```
/ad:harness-optimize                    # 전체 최적화 (감사 → 동기화 → 정리)
/ad:harness-optimize 감사               # 중복·불일치 감사만 수행
/ad:harness-optimize 동기화             # YouTrack KB 최신 데이터로 업데이트
/ad:harness-optimize 스프린트            # 스프린트 관련 문서만 최적화
/ad:harness-optimize okr               # OKR 문서만 최적화
/ad:harness-optimize 스킬               # 스킬 사용 통계 + 작성 원칙 감사
```

## 문서 구조 및 Source of Truth

### 역할별 단일 책임 원칙

각 주제는 **하나의 source of truth**만 가집니다. 다른 파일에서는 **링크로 참조**합니다.

| 주제 | Source of Truth | 참조하는 파일들 |
|------|----------------|----------------|
| **5W1H 작성법** | `docs/sprint/ticket-guide.md` 3항 | `.claude/commands/ad/ticket.md`, `templates/ticket-templates/`, `youtrack/ticket-guide.md` |
| **스토리 포인트** | `docs/sprint/story-point-guide.md` | `.claude/commands/ad/ticket.md`, `docs/sprint/sprint-planning-overview.md` |
| **이월 절차** | `docs/sprint/plan-change-process.md` | `docs/sprint/ticket-guide.md` 7항 (요약+링크만) |
| **맨데이 배분** | `docs/sprint/sprint-planning-overview.md` | - |
| **전사 상태 플로우** | `youtrack/ticket-guide.md` | `docs/sprint/ticket-guide.md` 8항 (링크만) |
| **OKR (팀/개인)** | Obsidian vault `wiki/processes/okr/` | `.claude/commands/ad/okr.md` |
| **서비스 프로파일** | `catalog/*.yaml` | `.claude/commands/ad/ticket.md` |
| **팀원 정보** | `policies/team-members.md` | `.claude/commands/ad/ticket.md`, `.claude/commands/ad/okr.md`, `.claude/commands/ad/weekly-report.md`, `.claude/commands/ad/capacity-plan.md`, `.claude/commands/ad/sprint-close-check.md`, `.claude/commands/ad/weekly-planned.md` |

## 실행 지침

### Step 1: 중복·불일치 감사

아래 파일들을 모두 읽고 비교합니다:

```
감사 대상 파일:
├── docs/sprint/ticket-guide.md          (5W1H, 스프린트 상태)
├── docs/sprint/story-point-guide.md     (SP 산정)
├── docs/sprint/plan-change-process.md   (이월/긴급 절차)
├── docs/sprint/sprint-planning-overview.md (맨데이 배분)
├── youtrack/ticket-guide.md             (전사 상태 플로우)
├── .claude/commands/ad/ticket.md        (티켓 스킬)
├── .claude/commands/ad/okr.md           (OKR 스킬)
├── templates/ticket-templates/feature.md (Feature 템플릿)
├── templates/ticket-templates/bugfix.md  (Bugfix 템플릿)
└── CLAUDE.md                            (하네스 진입점)
```

**감사 체크리스트:**
- [ ] 5W1H 정의가 `docs/sprint/ticket-guide.md`에만 존재하는가? (다른 곳은 링크만?)
- [ ] 이월 규칙 상세가 `docs/sprint/plan-change-process.md`에만 존재하는가?
- [ ] SP 기준표가 `docs/sprint/story-point-guide.md`에만 존재하는가?
- [ ] 템플릿의 5W1H 항목명이 가이드와 일치하는가? (Where=적용위치, When=트리거)
- [ ] 스킬 파일이 본문을 복사하지 않고 source of truth를 링크/참조하는가?
- [ ] CLAUDE.md의 구조 설명이 실제 디렉토리와 일치하는가?

### Step 2: YouTrack KB 동기화

KB 원본과 하네스 파일의 최신 여부를 비교합니다.

```bash
BASE="${YOUTRACK_BASE_URL:-https://aladincommunication.youtrack.cloud}"

# 스프린트 관련
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" "$BASE/api/articles/DEV2-A-892?fields=updated,summary,content"  # SP 가이드
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" "$BASE/api/articles/DEV2-A-818?fields=updated,summary,content"  # 티켓 가이드
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" "$BASE/api/articles/DEV2-A-829?fields=updated,summary,content"  # 계획 변경

# OKR 관련
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" "$BASE/api/articles/REF-A-2175?fields=updated,summary,content" # 연간 OKR
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" "$BASE/api/articles/REF-A-2470?fields=updated,summary,content" # 1분기
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" "$BASE/api/articles/REF-A-3122?fields=updated,summary,content" # 2분기
```

**동기화 규칙:**
- KB의 `updated` 타임스탬프가 하네스 파일보다 최신이면 → 하네스 업데이트
- 하네스에만 있는 내용(개인 OKR 초안 등)은 보존
- 변경 사항을 diff 형태로 사용자에게 보여주고 확인 후 반영

### Step 3: 중복 제거 및 정리

감사에서 발견된 중복을 제거합니다.

**중복 제거 원칙:**
1. Source of truth 파일의 내용은 유지
2. 참조 파일에서는 본문 삭제 → `참조: [문서명](경로)` 링크로 교체
3. 요약이 필요한 경우 3줄 이내 핵심만 남기고 "상세는 [문서명] 참조" 추가
4. 스킬 파일(`.claude/commands/ad/`)은 실행에 필요한 최소 정보만 유지

### Step 4: 결과 보고

```markdown
## 하네스 최적화 결과

### 동기화
| 문서 | KB ID | 상태 | 변경 내용 |
|------|-------|------|-----------|

### 중복 제거
| 파일 | 제거된 중복 | 교체 방식 |
|------|------------|-----------|

### 불일치 수정
| 파일 | 수정 내용 |
|------|-----------|

### CLAUDE.md 업데이트
- [ ] 구조 설명 최신화 여부
- [ ] 스킬 목록 최신화 여부
```

## 스킬 감사 (스킬 모드)

기준: [policies/skill-authoring-principles.md](../../../policies/skill-authoring-principles.md) 체크리스트 4단계.

1. **사용 통계**: `python3 tools/skill_usage_report.py --days 90` 실행
   - 주의: Claude Code 로그만 집계. Codex(`.codex/skills/*`)·Hermes cron(granola-sync 등) 사용은 안 잡힘 — 0회여도 즉시 삭제 판단 금지, 사용 경로 확인 후 판정
2. **체크리스트 감사**: 각 스킬을 트리거/구조/유도/가지치기 기준으로 점검, 결과를 `docs/skill-audit-baseline.md`에 갱신 (표 형식 유지, 날짜 갱신)
3. **삭제 테스트**: 무동작 문장 후보를 지운 버전으로 해당 스킬 1회 실행해 결과 비교. 같으면 삭제 확정
4. **판정 보고**: 0회 스킬은 삭제/통합/유지(사유 필수) 중 하나로 사용자에게 제안. 삭제는 사용자 확인 후

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

### frontmatter 스키마 검증

vault 티켓 산출물 frontmatter 표준 준수 확인:

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
for f in $(find "$VAULT/wiki/processes/tickets" -name '*.md' ! -name '_index.md'); do
  for key in ticket_id ticket_status assignee service sprint; do
    grep -q "^$key:" "$f" || echo "MISSING $key in $(basename $f)"
  done
done
```

누락 필드 surface된 row는 사람 검토.

### generated block 드리프트

```bash
python3 tools/sync_harness_links.py --vault "$VAULT" --harness . 2>&1 | grep -E "replaced|skipped|missing"
```

`replaced` 발견되면 sync 실행해 차이 반영.

ARGUMENTS: $ARGUMENTS
