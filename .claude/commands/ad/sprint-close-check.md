# 스프린트 마감 자가점검 (D-5 / D-4)

본인 담당 티켓 중 마감 프로세스(`docs/sprint/sprint-closing-process.md`) D-5 / D-4 점검 항목에 걸리는 티켓을 카테고리별로 **목록·링크만** 출력합니다. 상태 변경·코멘트 추가·티켓 수정은 **수행하지 않습니다**. 처리는 사용자가 YouTrack에서 직접 합니다.

## 사용법

```
/ad:sprint-close-check                       # 기본: 김정민, 이번 달 태그
/ad:sprint-close-check 조은흠                  # 다른 팀원
/ad:sprint-close-check 김정민 조은흠           # 다중 담당자
/ad:sprint-close-check 2605-planned           # 태그 직접 지정
/ad:sprint-close-check 2605-planned 조은흠    # 태그 + 담당자
```

인자 파싱:
- `NNNN-planned` 패턴 → `tag`
- 한글/영문 → 담당자 이름 (팀원 매핑)
- 인자 없으면 오늘 기준 `{YY}{MM}-planned` + 김정민

## 팀원 매핑

| 이름 | YouTrack ID |
|------|-------------|
| 김정민 | jmkim |
| 조은흠 | heum2 |
| 박민석 | pms0905 |
| 안혜련 | hyeryun |

> 신규 팀원은 이 테이블에 추가한다. `ad:weekly-report` / `ad:weekly-planned` 와 동기화 유지.

## 점검 카테고리

D-5 / D-4 마감 점검 항목을 5개 범주로 압축. 각 항목은 **본인이 직접 판단·처리**해야 하므로 스킬은 후보만 추출한다.

| # | 카테고리 | 검출 조건 | 단계 |
|---|----------|-----------|------|
| 1 | **미종료 티켓** | `tag={tag}` && Assignee=본인 && State ∉ {Done, Fixed, Closed, Verified, Cancelled} | D-5 |
| 2 | **결과물 링크 누락 Done** | `tag={tag}` && Assignee=본인 && State ∈ {Done, Fixed, Closed} && description+comments 텍스트에 `http(s)://` URL 패턴 없음 | D-5 |
| 3 | **SP 미입력 Task** | `tag={tag}` && Assignee=본인 && Type=Task && Story points 값 비어 있음 | D-4 |
| 4 | **5W1H 누락 Feature** | `tag={tag}` && Assignee=본인 && Type=Feature && description 휴리스틱 검사 실패 (아래 참조) | D-4 |
| 5 | **OKR 연결 누락 의심** | `tag={tag}` && Assignee=본인 && (태그에 OKR/KR/`okr:` 키워드 없음 && description에 `REF-A-` 링크 없음) | D-4 |

> **휴리스틱일 뿐**, 최종 판단은 사용자가 한다. 결과는 "후보 목록"으로 제시한다.

### 5W1H 휴리스틱

Feature description을 lower-case로 정규화한 뒤 다음 키워드 셋 중 매칭 개수를 센다:

- `what` 또는 `무엇`
- `why` 또는 `왜`
- `who` 또는 `누가` 또는 `사용 주체`
- `when` 또는 `언제` 또는 `트리거`
- `where` 또는 `어디` 또는 `적용 위치`
- `how` 또는 `어떻게`

6개 중 **3개 미만** 매칭 시 누락 후보로 분류. description 길이가 100자 미만이면 무조건 후보.

## 환경변수

| 변수 | 용도 |
|------|------|
| `$YOUTRACK_TOKEN` | YouTrack API 인증 토큰 |
| `$YOUTRACK_BASE_URL` | 기본 `https://aladincommunication.youtrack.cloud` |

## API 호출

```bash
BASE="${YOUTRACK_BASE_URL:-https://aladincommunication.youtrack.cloud}"
AUTH="Authorization: Bearer $YOUTRACK_TOKEN"

# 담당자 + 태그 + 본문/코멘트 포함 검색 (페이지당 50)
curl -s -H "$AUTH" \
  --data-urlencode "query=tag: {tag} Assignee: {ytId}" \
  --data-urlencode "fields=idReadable,summary,description,resolved,customFields(name,value(name,login,presentation)),tags(name),comments(text)" \
  --data-urlencode '$top=50' \
  --data-urlencode '$skip=0' \
  -G "$BASE/api/issues"
```

- 응답 50개를 채우면 `$skip` 50씩 증가시켜 끝까지 페이지네이션
- `customFields`에서 `Type`, `State`, `Assignee`, `Story points` 추출
- 다른 MCP 도구 사용 금지 (REST API만)

## 출력 형식

각 카테고리를 별도 섹션으로 출력. 항목 없으면 `없음` 표기. **상태 변경 액션은 출력하지 않는다** — 항목 + 링크 + (필요 시) 최소 메타데이터만.

```markdown
# 스프린트 마감 자가점검 — {담당자들} / {tag}

> 마감 프로세스 D-5/D-4 점검. 처리는 YouTrack에서 직접 수행.
> 참조: docs/sprint/sprint-closing-process.md

## 1. 미종료 티켓 (D-5)
- [{idReadable}]({BASE}/issue/{idReadable}) — {State} — {summary} ({담당자})

## 2. 결과물 링크 누락 Done (D-5)
- [{idReadable}]({BASE}/issue/{idReadable}) — {summary} ({담당자})

## 3. SP 미입력 Task (D-4)
- [{idReadable}]({BASE}/issue/{idReadable}) — {summary} ({담당자})

## 4. 5W1H 누락 Feature (D-4)
- [{idReadable}]({BASE}/issue/{idReadable}) — 매칭 {N}/6 — {summary} ({담당자})

## 5. OKR 연결 누락 의심 (D-4)
- [{idReadable}]({BASE}/issue/{idReadable}) — {summary} ({담당자})

## 요약
| 카테고리 | 건수 |
|----------|------|
| 미종료 | {n1} |
| 결과물 링크 누락 Done | {n2} |
| SP 미입력 Task | {n3} |
| 5W1H 누락 Feature | {n4} |
| OKR 연결 누락 의심 | {n5} |
```

링크 형식: `{BASE}/issue/{idReadable}` (예: `https://aladincommunication.youtrack.cloud/issue/DEV2-1234`).

## 실행 지침

### 1. 인자 파싱

1. 현재 날짜로 기본 태그 `{YY}{MM}-planned` 계산 (예: 2026-05 → `2605-planned`)
2. 인자에서 `\d{4}-planned` 패턴 매칭 → 태그 덮어쓰기
3. 남은 인자에서 팀원 이름 매칭 → YouTrack ID 목록
4. 담당자 미지정 시 `[jmkim]`

### 2. 티켓 수집

각 담당자에 대해 API 호출. 결과를 메모리에 적재. description / comments 필드까지 모두 가져온다 (다음 단계에서 텍스트 검사 필요).

### 3. 카테고리 분류

각 티켓에 대해 5개 조건을 평가하여 다중 카테고리 분류 허용 (예: 미종료 + 5W1H 누락 동시 가능).

- `state_name = customFields["State"].value.name`
- `type_name = customFields["Type"].value.name`
- `sp_value = customFields["Story points"].value` (없으면 미입력)
- `desc_text = description or ""`
- `comments_text = "\n".join(c.text for c in comments)`
- URL 패턴: `re.search(r"https?://", desc_text + comments_text)`

### 4. 출력 생성

위 출력 형식대로 마크다운 생성. 카테고리별 정렬 기준은 `idReadable` 오름차순.

### 5. 처리 안내

출력 마지막에 한 줄로 안내:

```
> 이 목록은 자가점검용 후보입니다. 상태 전환·이월·SP 입력·5W1H 보완은 YouTrack에서 직접 수행하세요.
> 이월 코멘트 양식: docs/sprint/plan-change-process.md
```

## 주의사항

- **티켓 수정 금지**: 본 스킬은 조회만 수행. State 전환, 코멘트 추가, SP 입력, 태그 변경 모두 사용자가 YouTrack에서 직접.
- **MCP 도구 사용 금지**: REST API만 사용 (정책: DB 계열 MCP 외에도 본 스킬은 단순 조회이므로 직접 호출이 단순).
- **휴리스틱 false positive 안내**: 5W1H 누락 / OKR 누락 후보는 키워드 기반이므로 본인 확인 후 처리.
- **다중 담당자**: 출력에 담당자 표기 포함하여 식별 가능하게 함.
- **페이지네이션**: 50개 초과 시 `$skip`으로 끝까지.
- **태그 변형**: `{YYMM}-planned` 외 다른 컨벤션(예: 2605-sprint)은 인자로 명시.

ARGUMENTS: $ARGUMENTS
