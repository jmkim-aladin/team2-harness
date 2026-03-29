# 하네스 최적화 (업데이트·최신화·중복제거)

하네스 문서의 최신화, 중복 제거, YouTrack KB 동기화를 수행합니다.

## 사용법

```
/ad:harness-optimize                    # 전체 최적화 (감사 → 동기화 → 정리)
/ad:harness-optimize 감사               # 중복·불일치 감사만 수행
/ad:harness-optimize 동기화             # YouTrack KB 최신 데이터로 업데이트
/ad:harness-optimize 스프린트            # 스프린트 관련 문서만 최적화
/ad:harness-optimize okr               # OKR 문서만 최적화
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
| **OKR (팀/개인)** | `docs/okr/` | `.claude/commands/ad/okr.md` |
| **서비스 프로파일** | `catalog/*.yaml` | `.claude/commands/ad/ticket.md` |
| **팀원 정보** | `policies/team-members.md` | `.claude/commands/ad/ticket.md`, `.claude/commands/ad/okr.md` |

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
├── docs/okr/*.md                        (OKR 문서들)
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

ARGUMENTS: $ARGUMENTS
