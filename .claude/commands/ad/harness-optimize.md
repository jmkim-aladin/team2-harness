# 하네스 최적화 (업데이트·최신화·중복제거)

하네스 문서의 최신화, 중복 제거, YouTrack KB 동기화를 수행한다.

> 문서 위치 결정: harness `policies/knowledge-base-policy.md` (repo↔vault 경계) + vault `wiki/guides/document-placement.md` (vault 내부 트리).
> 유지보수 규칙(주기·권한·기록·SoT 등록부): [policies/harness-governance-policy.md](../../../policies/harness-governance-policy.md)

## 사용법

```
/ad:harness-optimize                    # 전체 최적화 (감사 → 동기화 → 정리)
/ad:harness-optimize 감사               # 중복·불일치 감사만 수행
/ad:harness-optimize 동기화             # YouTrack KB 최신 데이터로 업데이트
/ad:harness-optimize 스프린트            # 스프린트 관련 문서만 최적화
/ad:harness-optimize okr               # OKR 문서만 최적화
/ad:harness-optimize 스킬               # 스킬 사용 통계 + 작성 원칙 감사
/ad:harness-optimize 제약               # 지시 강도·과잉제약 감사
```

## Source of Truth

주제별 SoT 등록부는 [policies/harness-governance-policy.md](../../../policies/harness-governance-policy.md) §Source of Truth 등록부 — 감사(Step 1·3)의 기준표로 사용한다.

## 실행 지침

Step 순서는 기본 접근이다 — 상황에 따라 순서 조정·병렬 수행 가능하며, 판정 기준은 각 Step의 완료(감사 결과 확보 → 동기화 diff 확인 → 중복 제거 → 보고)다.

### Step 1: 중복·불일치 감사

아래 파일들을 모두 읽고 비교한다:

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

KB 원본과 하네스 파일의 최신 여부를 비교한다.

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

**전사 KB ↔ 하네스 매핑** (DEV2 외 참조 문서)

| KB 문서 | 하네스 파일 |
|---------|------------|
| `REF-A-625` (Git Flow) | `policies/branching-strategy.md` |
| `REF-A-1958` (Clean Architecture) | `policies/engineering-policy.md` |
| `REF-A-3131` (Backend Environment) | 서비스 카탈로그 (naru, bazaar) |
| `REF-A-3133` (Frontend Environment) | 서비스 카탈로그 (max-front, maxcms-front) |

**동기화 규칙:**
- KB의 `updated` 타임스탬프가 하네스 파일보다 최신이면 → 하네스 업데이트
- 하네스에만 있는 내용(개인 OKR 초안 등)은 보존
- 변경 사항을 diff 형태로 사용자에게 보여주고 확인 후 반영

### Step 3: 중복 제거 및 정리

감사에서 발견된 중복을 제거한다. 원칙: [harness-governance-policy.md](../../../policies/harness-governance-policy.md) §변경 통제 (SoT 유지 / 참조는 링크 교체 / 요약 3줄 이내 / 스킬은 실행 최소 정보만).

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

기준: [policies/skill-authoring-principles.md](../../../policies/skill-authoring-principles.md) 체크리스트 5단계.

1. **사용 통계**: `python3 tools/skill_usage_report.py --days 90` 실행
   - 주의: Claude Code 로그만 집계. Codex(`.codex/skills/*`)·Hermes cron(granola-sync 등) 사용은 안 잡힘 — 0회여도 즉시 삭제 판단 금지, 사용 경로 확인 후 판정
2. **체크리스트 감사**: 각 스킬을 트리거/구조/유도/가지치기 기준으로 점검, 결과를 `docs/skill-audit-baseline.md`에 갱신 (표 형식 유지, 날짜 갱신)
3. **삭제 테스트**: 무동작 문장 후보를 지운 버전으로 해당 스킬 1회 실행해 결과 비교. 같으면 삭제 확정
4. **Codex 패리티 검증** (대전제 — [skill-authoring-principles.md](../../../policies/skill-authoring-principles.md)):
   ```bash
   for f in .claude/commands/ad/*.md; do n=$(basename "$f" .md); [ -d ".codex/skills/ad-$n" ] || echo "MISSING codex alias: ad-$n"; done
   ```
   alias 누락·내용 복제(얇은 alias 위반)·깨진 SoT 참조를 surface한다
5. **판정 보고**: 0회 스킬은 삭제/통합/유지(사유 필수) 중 하나로 사용자에게 제안. 삭제는 사용자 확인 후

## 제약 감사 (제약 모드)

기준: [policies/instruction-precedence-policy.md](../../../policies/instruction-precedence-policy.md)의 4등급·표기 규약.

1. 대상 문서(정책·스킬·템플릿)의 지시문을 invariant / policy / heuristic / example로 분류한다
2. 다음을 후보로 surface한다:
   - "반드시/필수/금지"로 표기된 heuristic (강등 후보)
   - 의도(왜) 미기재 규칙
   - `근거:` 없는 실패-사례성 하드 게이트
   - 캐시(환경이 SoT인 사실의 재기술), 근거 없는 도구·명령·개수·순서 고정
3. 발견별로 위치·원문·추론 의도·권장 조치(유지 / 완화 / 제거 / 도구화 / 근거 부착)·보존되는 불변조건을 제시한다
4. 재제안 방지: [docs/skill-audit-baseline.md](../../../docs/skill-audit-baseline.md)의 기존 판정·기각 기록과 대조한다
5. 적용은 삭제 테스트(재표현 전후 해당 스킬 1회 실행 비교) 후 PR로. 강도 하향·등급 변경은 review-required — 기준·권한: [harness-governance-policy.md](../../../policies/harness-governance-policy.md)

## repo↔vault 드리프트 점검

새 항목이 잘못된 저장소에 들어갔는지 정기 점검한다. 아래 명령들은 예시다 — 목표는 성격이 위치와 어긋난 파일을 surface하는 것이고, 탐색 방법은 상황에 맞게 조정 가능하다.

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
