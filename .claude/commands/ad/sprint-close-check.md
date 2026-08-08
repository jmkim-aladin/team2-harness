---
description: 스프린트 마감 자가점검 — 미종료·SP·5W1H·OKR 누락 후보
---

# 스프린트 마감 자가점검 (D-5 / D-4)

> 문서 위치 결정: harness `policies/knowledge-base-policy.md` (repo↔vault 경계) + vault `wiki/guides/document-placement.md` (vault 내부 트리).

본인 담당 티켓 중 마감 프로세스(`docs/sprint/sprint-closing-process.md`) D-5 / D-4 점검 항목에 걸리는 티켓을 카테고리별로 **목록·링크만** 출력한다. 상태 변경·코멘트 추가·티켓 수정은 **수행하지 않는다**. 처리는 사용자가 YouTrack에서 직접 한다.

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

로스터 SoT: [policies/team-members.md](../../../policies/team-members.md) — 한글 이름 → YouTrack ID 변환은 그 표(dev role 정직원)를 따른다.

## 점검 카테고리

D-5 / D-4 마감 점검 항목을 6개 범주로 압축. 각 항목은 **본인이 직접 판단·처리**해야 하므로 스킬은 후보만 추출한다.

| # | 카테고리 | 검출 조건 | 단계 |
|---|----------|-----------|------|
| 1 | **미종료 티켓** | `tag={tag}` && Assignee=본인 && State ∉ {Done, Fixed, Closed, Verified, Cancelled} | D-5 |
| 2 | **결과물 링크 누락 Done** | `tag={tag}` && Assignee=본인 && State ∈ {Done, Fixed, Closed} && description+comments 텍스트에 `http(s)://` URL 패턴 없음 | D-5 |
| 3 | **SP 미입력 Task** | `tag={tag}` && Assignee=본인 && Type=Task && Story points 값 비어 있음 | D-4 |
| 4 | **5W1H 누락 Feature** | `tag={tag}` && Assignee=본인 && Type=Feature && description 휴리스틱 검사 실패 (아래 참조) | D-4 |
| 5 | **OKR 연결 누락 의심** | `tag={tag}` && Assignee=본인 && (태그에 OKR/KR/`okr:` 키워드 없음 && description에 `REF-A-` 링크 없음) | D-4 |
| 6 | **단계·환경 분리 판정 누락 Feature** | `tag={tag}` && Assignee=본인 && Type=Feature && **개발 Feature**(제목에 단계 구분자 없음) && 검증(테스트·QA) 또는 배포·운영 반영 단계의 **형제 Feature**가 없고 "해당 없음" 사유도 없음 (아래 참조) | D-4 |

> **휴리스틱일 뿐**, 최종 판단은 사용자가 한다. 결과는 "후보 목록"으로 제시한다.

### 5W1H 휴리스틱

Feature description이 5W1H 여섯 항목(What/무엇, Why/왜, Who/누가/사용 주체, When/언제/트리거, Where/어디/적용 위치, How/어떻게)을 **실질적으로** 담는지 내용으로 판단한다. 표기가 달라도 내용이 있으면 통과, 키워드만 있고 내용이 비면 누락이다.

절반 이상이 식별되지 않거나 description이 형식적 한두 줄이면 누락 후보로 분류하고, **어떤 항목이 비었는지**를 사유로 붙인다.

### 단계·환경 분리 판정 휴리스틱

규칙 SoT: `docs/sprint/ticket-guide.md` 2-2항(단계) · 2-3항(환경). 단계는 **Feature 단위로 갈린다** — 검증·배포는 개발 Feature의 하위 Task가 아니라 **별도 Feature**다.

#### 검사 대상 고르기

제목 끝 구분자로 Feature의 단계를 판정한다.

| 제목 패턴 | 단계 | 검사 |
|---|---|---|
| `— 설계` | 설계·분석 | 대상 아님 |
| 구분자 없음 | **개발** | **검사 대상** |
| `— 테스트` / `— QA` | 검증 | 대상 아님 |
| `— 배포·반영 (...)` | 배포 | 대상 아님 |

개발 Feature에 대해 **검증**과 **배포·운영 반영** 두 단계를 각각 판정한다.

#### 정상 판정 조건

한 단계는 아래 둘 중 **하나라도 만족하면 정상**으로 본다.

1. **형제 Feature 존재** — 같은 업무 요약을 공유하고 단계 구분자가 붙은 Feature가 있음. 개발 Feature와 선행·후행으로 링크돼 있거나, 제목의 `[{서비스}] {업무 요약}` 부분이 일치함
   - 검증: 제목에 `— 테스트`, `— QA`, `검증` — **테스트와 QA는 서로 대체 가능**하므로 둘 중 하나만 있어도 통과
   - 배포·운영 반영: 제목에 `배포`, `운영 반영`, `운영반영`, `릴리즈`, `deploy`
2. **해당 없음 사유 기재** — 개발 Feature description에 `검증 해당 없음` / `테스트 해당 없음` / `QA 해당 없음` / `배포·운영 반영 해당 없음` (또는 `반영 해당 없음`) 문자열이 있음

둘 다 없으면 해당 단계를 **판정 누락 후보**로 분류한다. 두 단계 모두 걸리면 한 항목에 함께 표기한다.

#### 추가 검사 두 가지

- **Task 구분자 잔존** — 하위 Task 제목에 `— 설계` / `— 테스트` / `— QA` / `— 배포·반영` 구분자가 있으면 후보다. 구분자는 Feature에만 붙이고 Task에는 붙이지 않는다 (티켓 가이드 2-2항). 부모가 개발 Feature인데 검증·배포 구분자가 붙어 있으면 단계 혼입까지 의심한다
- **환경 누락** — 배포 Feature(제목에 `배포`)에 환경 표기 `(개발)` / `(운영)` / `(스테이징)` 가 없으면 후보로 표시한다. 개발·운영을 한 티켓에 담았을 가능성이 있다. 구분자 없이 `— 배포·운영 반영` 으로만 끝나는 기존 티켓도 여기 걸린다

> 검증은 내부 **테스트**(개발2팀)와 **QA**(시너지팀)로 나뉘고, `테스트만` / `QA만` / `테스트 → QA` 셋 다 정상이다. 이 스킬은 "검증 Feature가 하나라도 있는가"만 판정하며, 테스트만 있는 업무에 QA가 필요한지는 판정하지 않는다.

- 형제 Feature 매칭은 제목 문자열 기반이라 오탐이 난다. 링크(`Subtask`·선행·후행)가 있으면 그쪽을 우선 본다.
- 하위 Task 조회는 아래 API의 `links` 필드를 사용한다 (`Subtask` linkType, `direction=OUTWARD`가 자식).
- Feature 유형에만 적용한다. Task는 검사하지 않는다.
- 개발 단계는 검사하지 않는다 (사실상 항상 존재하고, 없으면 카테고리 1·3에서 이미 잡힌다).

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
  --data-urlencode "fields=idReadable,summary,description,resolved,customFields(name,value(name,login,presentation)),tags(name),comments(text),links(direction,linkType(name),issues(idReadable,summary))" \
  --data-urlencode '$top=50' \
  --data-urlencode '$skip=0' \
  -G "$BASE/api/issues"
```

- 응답 50개를 채우면 `$skip` 50씩 증가시켜 끝까지 페이지네이션
- `customFields`에서 `Type`, `State`, `Assignee`, `Story points` 추출
- `links`에서 `linkType.name == "Subtask"` && `direction == "OUTWARD"` 인 항목의 `issues[].summary`가 하위 Task 제목 (카테고리 6 판정용)
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

## 6. 단계·환경 분리 판정 누락 Feature (D-4)
- [{idReadable}]({BASE}/issue/{idReadable}) — 누락 단계: {검증|배포·운영 반영|검증, 배포·운영 반영} — {summary} ({담당자})
- [{idReadable}]({BASE}/issue/{idReadable}) — Task 구분자 잔존: {구분자} — {summary} ({담당자})
- [{idReadable}]({BASE}/issue/{idReadable}) — 환경 표기 누락: 배포 Feature에 (개발)/(운영) 없음 — {summary} ({담당자})

## 요약
| 카테고리 | 건수 |
|----------|------|
| 미종료 | {n1} |
| 결과물 링크 누락 Done | {n2} |
| SP 미입력 Task | {n3} |
| 5W1H 누락 Feature | {n4} |
| OKR 연결 누락 의심 | {n5} |
| 단계·환경 분리 판정 누락 Feature | {n6} |
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

각 티켓에 대해 6개 조건을 평가하여 다중 카테고리 분류 허용 (예: 미종료 + 5W1H 누락 동시 가능).

- `state_name = customFields["State"].value.name`
- `type_name = customFields["Type"].value.name`
- `sp_value = customFields["Story points"].value` (없으면 미입력)
- `desc_text = description or ""`
- `comments_text = "\n".join(c.text for c in comments)`
- URL 패턴: `re.search(r"https?://", desc_text + comments_text)`
- `subtask_titles = [i.summary for l in links if l.linkType.name == "Subtask" and l.direction == "OUTWARD" for i in l.issues]`
- `linked_titles = [i.summary for l in links for i in l.issues]` (선행·후행 포함 — 형제 Feature 탐색용)
- 카테고리 6은 `type_name == "Feature"` 이고 **제목에 단계 구분자(`— 설계` / `— 테스트` / `— QA` / `— 배포`)가 없을 때만** 평가 (= 개발 Feature)
  - 형제 Feature 후보 = `linked_titles` ∪ 같은 담당자·같은 태그 수집분에서 `[{서비스}] {업무 요약}` 접두가 일치하는 Feature 제목
  - 검증·배포 각각 "형제 Feature 제목 키워드 매칭" 또는 "desc_text에 해당 없음 사유" 중 하나라도 있으면 통과, 둘 다 없으면 해당 단계를 누락으로 기록
  - **Task 구분자 잔존**: `subtask_titles` 중 하나라도 단계 구분자를 포함하면 별도 후보로 기록. 부모가 개발 Feature이고 구분자가 검증·배포 계열이면 단계 혼입으로 표기
  - **환경 표기 누락**: 제목에 `배포·반영` 이 있는데 `(개발)` / `(운영)` / `(스테이징)` 이 없으면 별도 후보로 기록

### 4. 출력 생성

위 출력 형식대로 마크다운 생성. 카테고리별 정렬 기준은 `idReadable` 오름차순.

### 5. 처리 안내

출력 마지막에 한 줄로 안내:

```
> 이 목록은 자가점검용 후보인다. 상태 전환·이월·SP 입력·5W1H 보완은 YouTrack에서 직접 수행하세요.
> 이월 코멘트 양식: docs/sprint/plan-change-process.md
```

## 주의사항

- **티켓 수정 금지**: 본 스킬은 조회만 수행. State 전환, 코멘트 추가, SP 입력, 태그 변경 모두 사용자가 YouTrack에서 직접.
- **MCP 도구 사용 금지**: REST API만 사용 (정책: DB 계열 MCP 외에도 본 스킬은 단순 조회이므로 직접 호출이 단순).
- **휴리스틱 false positive 안내**: 5W1H 누락 / OKR 누락 / 단계·환경 분리 판정 누락 후보는 키워드 기반이므로 본인 확인 후 처리. 특히 단계 분리는 Feature 제목을 컨벤션(`— 설계`, `— 테스트`, `— QA`, `— 배포·반영 (환경)`)대로 쓰지 않으면 오탐이 난다. 형제 Feature 매칭도 제목 문자열 기반이라 업무 요약 표현이 Feature마다 다르면 누락으로 잡힌다.
- **다중 담당자**: 출력에 담당자 표기 포함하여 식별 가능하게 함.
- **페이지네이션**: 50개 초과 시 `$skip`으로 끝까지.
- **태그 변형**: `{YYMM}-planned` 외 다른 컨벤션(예: 2605-sprint)은 인자로 명시.

## frontmatter 표준 (티켓 산출물)

vault `wiki/guides/frontmatter-spec.md` (SoT)의 ticket 스키마를 따른다 — 티켓 노트 작성 시점에 해당 파일을 읽어 최신 스키마 사용.

ARGUMENTS: $ARGUMENTS
