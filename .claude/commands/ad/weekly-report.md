# 주간업무 보고서 작성

YouTrack KB와 티켓 정보를 기반으로 개인별 주간업무 보고서를 조회·업데이트합니다.

## 사용법

```
/ad:weekly-report                          # 내(김정민) 보고서 조회
/ad:weekly-report 조은흠                    # 조은흠 보고서 조회
/ad:weekly-report 업데이트                  # 내 보고서 금주 한일 업데이트
/ad:weekly-report 조은흠 업데이트            # 조은흠 보고서 업데이트
/ad:weekly-report 조은흠 추가 [내용]         # 조은흠 항목 추가
/ad:weekly-report 전체                      # 전체 팀원 보고서 조회
/ad:weekly-report 동기화                    # YouTrack 티켓 상태 기반 자동 동기화
```

## 팀원 매핑

| 이름 | 이니셜 | YouTrack ID | 역할 | 비고 |
|------|--------|-------------|------|------|
| 김정민 | KJM | jmkim | 백엔드 (메인) | 기본값 |
| 조은흠 | JEH | heum2 | 프론트엔드 (서브) | 김정민 보고서에 항목 포함 |

> 팀원 추가 시 이 테이블에 행을 추가하면 됩니다.

## YouTrack KB 구조

```
DEV2-A-692 (주간업무)
├── DEV2-A-693 (2026 1Q)
│   ├── DEV2-A-694 (조윤주)
│   ├── DEV2-A-695 (이현민)
│   ├── DEV2-A-696 (김정민)     ← 김정민 + 조은흠 항목 포함
│   └── DEV2-A-830 (2026.03.5W) ← 주간 스냅샷
└── (2026 2Q) ← 분기 시작 시 생성
```

## 보고서 양식

> 상세 가이드: `docs/sprint/weekly-report-guide.md`

### 섹션 구조

```
## 백로그 항목
## 계획 항목
## 진행중 항목
## 완료된 항목
## 이슈사항
## 기타
```

### 항목 형식

```markdown
- **{제목} ({일정정보}, {담당자}** {티켓ID} **{티켓명})**
  - ({상태}) {내용} ({일자}, {담당자} {하위티켓ID} {하위티켓명})
```

**상태 말머리**: `(완료)`, `(진행 중)`, `(예정)`, `(보류)`

**일정 형식**:
- 백로그: 일정 없음
- 미진행/계획: 시작 예상 일자~
- 진행중: 시작일~, ~목표일
- 완료: 완료 일자
- 지연: ~~기존목표~~ ~수정목표, 제목 뒤 `- 지연`, 지연 사유 기재

## 환경변수

| 변수 | 용도 |
|------|------|
| `$YOUTRACK_TOKEN` | YouTrack API 인증 토큰 |
| `$YOUTRACK_BASE_URL` | YouTrack 베이스 URL (기본: `https://aladincommunication.youtrack.cloud`) |

## API 참조

```bash
BASE="${YOUTRACK_BASE_URL:-https://aladincommunication.youtrack.cloud}"

# 1. 분기별 부모 문서 조회 (주간업무 하위)
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" \
  "$BASE/api/articles/DEV2-A-692?fields=childArticles(idReadable,summary)"

# 2. 개인 보고서 조회
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" \
  "$BASE/api/articles/{articleId}?fields=id,idReadable,summary,content,updated"

# 3. 티켓 상태 조회 (동기화용)
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" \
  "$BASE/api/issues/{issueId}?fields=idReadable,summary,customFields(name,value(name))"

# 4. 담당자별 티켓 검색 (진행중 항목 탐색)
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" \
  "$BASE/api/issues?query=project:DEV2+assignee:{ytId}+state:In+Progress&fields=idReadable,summary,customFields(name,value(name))&\$top=50"

# 5. KB 문서 업데이트
curl -s -X POST -H "Authorization: Bearer $YOUTRACK_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "..."}' \
  "$BASE/api/articles/{articleId}"
```

## 실행 지침

### 1. 조회 모드 (기본)

사용자가 `/ad:weekly-report` 또는 `/ad:weekly-report {이름}`을 입력하면:

1. **현재 분기 판별**: 오늘 날짜 기준으로 분기 계산 (1~3월: 1Q, 4~6월: 2Q, ...)
2. **KB 문서 탐색**: DEV2-A-692 하위에서 해당 분기 문서 → 해당 팀원 문서 순으로 탐색
3. **보고서 표시**: YouTrack HTML을 마크다운으로 변환하여 표시
4. 이름 없으면 기본값 김정민

### 2. 업데이트 모드

사용자가 `/ad:weekly-report 업데이트` 또는 `/ad:weekly-report {이름} 업데이트`를 입력하면:

1. **현재 보고서 조회**: KB에서 최신 보고서 가져오기
2. **금주 변동 파악**: 사용자에게 이번 주 완료/진행/신규 항목을 질문
3. **티켓 상태 확인**: 언급된 티켓ID가 있으면 YouTrack에서 실제 상태 조회하여 교차 검증
4. **보고서 갱신**: 항목 이동 및 내용 추가
   - 완료된 항목: 진행중 → 완료로 이동, 완료 일자 기재
   - 새로 시작: 계획/백로그 → 진행중으로 이동
   - 신규 항목: 해당 섹션에 추가
   - Task 말머리: (예정) → (진행 중) → (완료) 갱신
5. **마크다운 출력**: 갱신된 보고서를 마크다운으로 출력
6. **KB 반영 제안**: 사용자 확인 후 YouTrack KB API로 업데이트 (확인 필수)

### 3. 항목 추가 모드

사용자가 `/ad:weekly-report {이름} 추가 [내용]`을 입력하면:

1. **현재 보고서 조회**
2. **추가할 항목 파악**: 내용에서 티켓ID, 섹션, 상태 추출
3. **티켓 정보 보강**: 티켓ID가 있으면 YouTrack에서 상세 정보 조회
4. **양식에 맞게 항목 생성**: 보고서 양식에 맞춰 항목 포맷팅
5. **적절한 섹션에 삽입**
6. **마크다운 출력 및 KB 반영 제안**

### 4. 동기화 모드

사용자가 `/ad:weekly-report 동기화`를 입력하면:

1. **현재 보고서 조회**
2. **보고서 내 모든 티켓ID 추출**
3. **YouTrack API로 각 티켓 현재 상태 일괄 조회**
4. **상태 불일치 감지**: 보고서 상태 vs 실제 티켓 상태 비교
5. **변경 제안**: 불일치 항목 목록 표시, 자동 갱신 제안
6. **사용자 확인 후 반영**

### 5. 전체 조회 모드

사용자가 `/ad:weekly-report 전체`를 입력하면:

1. 현재 분기 부모 문서 하위의 모든 팀원 문서 조회
2. 팀원별로 정리하여 표시

## 담당자별 항목 구분

김정민 보고서에 조은흠 항목이 혼재되어 있으므로:
- **담당자 식별**: 각 항목의 `(담당자` 부분에서 이름 추출
- **조은흠 조회 시**: 김정민 보고서에서 조은흠 담당 항목만 필터링하여 표시
- **조은흠 추가 시**: 김정민 보고서의 적절한 섹션에 조은흠 담당으로 항목 삽입

## Feature 기간 초과 경고

Feature는 총 기간 1주일 이내가 필수 규칙 (`docs/sprint/ticket-guide.md` 2항).
주간보고 동기화/업데이트 시 아래 검증을 수행:

- **진행중 Feature의 시작일이 7일 이상 경과**: `⚠️ 기간 초과` 경고 표시
- **경고 시 안내**: "Feature `{티켓ID}`가 {N}일째 진행 중입니다. 1주일 규칙 초과. 분할 또는 지연 사유 기재가 필요합니다."
- **지연 처리**: 보고서에 `- 지연` 표시 + 지연 사유 작성 유도

## 주의사항

- KB 업데이트는 반드시 사용자 확인 후 실행 (자동 반영 금지)
- 보고서 양식은 `docs/sprint/weekly-report-guide.md` 기준 준수
- 티켓 링크 형식: `{담당자} {티켓ID} {티켓명}` (YouTrack 자동 링크)
- 지연 항목은 반드시 지연 사유 포함
- 분기 전환 시 새 분기 문서가 없으면 생성 안내

ARGUMENTS: $ARGUMENTS
