---
description: 작업 종료 (Work Close)
disable-model-invocation: true
---

# 작업 종료 (Work Close)

Feature/Task를 팀 규칙에 맞게 YouTrack에서 종료한다: 상태 정렬 → 완료 코멘트 → 소요시간(work item) 입력 → **Fixed**.

`/ad:work-prep`(작업 준비)의 종료 페어. 이 스킬은 **YouTrack 티켓 자체**만 다룬다 — 로컬 위키 노트의 종료 반영(`ticket_status: done` 등)은 `/ad:work-prep`의 종료 플로우가 담당한다.

## 사용법

```
/ad:work-close DEV2-1234                  # 단건 (Task 또는 Feature)
/ad:work-close DEV2-1234 DEV2-5678        # 복수
/ad:work-close                            # 대상 티켓 질문
```

- Feature ID를 주면 하위 Task 전수를 함께 판정한다
- 질문 규율: 한 번에 하나씩, 추천안과 함께. 조회로 해소되는 사실은 직접 확인하고 **결정만** 질문한다

## 환경변수

| 변수 | 용도 |
|------|------|
| `$YOUTRACK_TOKEN` | YouTrack API 인증 토큰 |
| `$YOUTRACK_BASE_URL` | 기본 `https://aladincommunication.youtrack.cloud` |

## 실행 지침

### 0. 토큰 owner 검증 (필수)

`GET /api/users/me?fields=login,fullName,email`로 토큰이 본인 계정인지 확인한다. 코멘트·work item author가 토큰 owner로 기록되므로, 불일치하면 **실행을 중단**하고 본인 토큰 교체를 요청한다. (근거: `ad:ticket` 0단계와 동일 — reporter/author 명의 어그러짐)

완료 기준: 토큰 owner 본인 확인, 또는 중단.

### 1. 티켓 조회

대상 ID 각각:

```bash
BASE="${YOUTRACK_BASE_URL:-https://aladincommunication.youtrack.cloud}"
AUTH="Authorization: Bearer $YOUTRACK_TOKEN"

curl -s -H "$AUTH" \
  "$BASE/api/issues/{idReadable}?fields=idReadable,summary,description,resolved,reporter(login),customFields(name,value(name,login)),links(direction,linkType(name),issues(idReadable,summary,resolved,customFields(name,value(name)))),comments(text)"
```

- `customFields`에서 `Type`, `State`, `Story points`, `Assignee` 추출
- 하위 Task = `links` 중 `linkType.name == "Subtask"` && `direction == "OUTWARD"` 의 `issues[]`

완료 기준: 대상(하위 Task 포함) 전체의 Type/State/SP/resolved 확보.

### 2. 대상 확정

| 판정 | 처리 |
|------|------|
| `resolved != null` | 이미 종료 — skip, 결과 보고에만 표기 |
| `reporter` ≠ 본인 (외부·사업부 티켓) | 대상 제외·보고 — State 임의 전환 금지 (`ad:ticket` 외부 티켓 처리 규칙) |
| Type=Task | 종료 대상 |
| Type=Feature | 하위 Task 전수 판정 (아래) |

**Feature 판정** — 미종료 하위 Task 목록을 제시하고, Task별로 "실제 완료됐는가?"를 **하나씩** 확인한다.

- 완료 확인된 Task → 종료 대상에 포함 (Task 플로우로 함께 종료)
- 미완료 Task가 하나라도 남으면 → **Feature 종료는 중단**하고 사유 보고. 완료 확인된 Task까지는 종료를 진행한다
- 하위 Task 전부 종료(기존 + 이번 실행분)가 확인된 Feature만 상태 전환 대상이 된다

Feature 자체에는 코멘트·work item을 넣지 않는다 — 소요시간·SP는 YouTrack이 하위 Task에서 합산한다. Feature는 상태 전환만 수행한다. (사용자 확정 2026-08-06)

완료 기준: 티켓별 처리 분류(종료 대상 / skip / 제외 / Feature 중단) 확정.

### 3. 공통 질문 (실행당 1회)

종료 대상 Task가 있으면 **한 번만** 질문한다:

> SP당 몇 시간, 작업 시작일은 언제로 입력할까? (참고: SP 3 ≈ 1 MD)

- 답변은 이번 실행의 모든 대상 Task에 공통 적용한다
- SP 미입력 Task가 있으면 그 Task의 SP도 함께 질문한다 (등록 상한 3 — `docs/sprint/story-point-guide.md` §4). Story points 필드 입력을 실행 계획에 포함한다

완료 기준: SP당 시간·시작일 확보 + 대상 Task 전체 SP 값 확정.

### 4. 실행 계획 제시 → 승인 게이트 (필수)

실행 전에 전체 계획을 한 번에 제시하고 승인을 받는다. (근거: CLAUDE.md AI 정책 — 티켓 상태 변경 전 사용자 확인)

티켓별로 출력:

```markdown
## 종료 실행 계획

### [DEV2-1234](…) {summary} — Task, SP 3
- 상태: Open → In Progress → Fixed
- work items: 2026-08-04 4h / 2026-08-05 4h / 2026-08-06 4h
- 코멘트 초안:
  > {전문}

### [DEV2-1200](…) {summary} — Feature
- 하위 Task: DEV2-1234(이번 종료), DEV2-1235(기존 Fixed) — 전부 종료 확인
- 상태: In Progress → Fixed (코멘트·work item 없음)
```

승인 후 실행한다. 개별 수정 요청이 오면 반영 후 재제시한다.

완료 기준: 사용자 승인 1회 확보.

### 5. 실행 (승인 후)

**Task별** 순서 고정:

1. State ≠ In Progress → `In Progress` 전환 (이미 In Progress면 생략)
2. SP 미입력이면 Story points 입력
3. 코멘트 등록 (아래 "코멘트 규칙")
4. work item 등록 — **SP 1개 = work item 1개**, SP당 시간, 시작일부터 **영업일(주말 제외) 순차 분산**
5. State → `Fixed`

**Feature**: 하위 Task 실행이 전부 끝난 뒤 State ≠ In Progress면 `In Progress` 경유 후 `Fixed`.

전환·등록 실패(워크플로 제약, 권한)가 나면 그 티켓만 중단하고 응답 본문을 결과에 기록한다. 나머지 티켓은 계속 진행한다.

완료 기준: 대상 전체가 Fixed 또는 실패 사유 기록.

### 6. 결과 보고

```markdown
| 티켓 | 처리 | 상태 | work items |
|------|------|------|-----------|
| DEV2-1234 | 종료 | Fixed | 3건 (8/4~8/6, 12h) |
| DEV2-1200 | 종료 (Feature) | Fixed | — (하위 합산) |
| DEV2-1300 | skip | 이미 Closed | — |
```

위키 노트 종료 반영이 필요하면 `/ad:work-prep` 종료 플로우를 안내한다.

## 코멘트 규칙 (Task)

완료 내역을 **비즈니스 로직·도메인 중심**으로 간략히 쓴다. 초안은 티켓 본문(수행 내용·완료 기준)과 대화 컨텍스트에서 도출한다.

- bullet 3~6개 — 무엇이 어떻게 동작하게 됐는지, 정책·트리거·운영 영향 위주
- **결과물 링크 포함** — 커밋/PR/KB 등 외부 접근 가능 URL (`docs/sprint/sprint-closing-process.md`: 링크 없는 종료는 산출물 부재로 간주). 링크를 못 찾으면 사용자에게 요청한다
- 로컬 파일 경로 금지 (근거: `policies/ai-usage-policy.md` — 외부 접근 불가 정보 티켓 등록 금지)
- 코드블록·파일경로·컬럼명·SP명 나열 금지 — 도메인 단위로 표현 (근거: `ad:ticket` 본문 작성 규칙, DEV2-5512 사용자 확정)

## work item 계산

답변 "SP당 H시간, 시작일 D" → Task SP가 N이면 work item N건. i번째 일자는 D부터 i번째 영업일(주말 제외), duration은 `H × 60`분.

예: SP 3, SP당 4h, 시작일 2026-08-04(화) → 8/4 4h, 8/5 4h, 8/6 4h.

## API 참조

```bash
# 상태 전환 (In Progress / Fixed)
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"customFields":[{"name":"State","$type":"StateIssueCustomField","value":{"name":"In Progress"}}]}' \
  "$BASE/api/issues/{idReadable}?fields=idReadable,customFields(name,value(name))"

# Story points 입력
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"customFields":[{"name":"Story points","$type":"SimpleIssueCustomField","value":3}]}' \
  "$BASE/api/issues/{idReadable}?fields=idReadable"

# 코멘트 등록
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"text":"{코멘트 본문}"}' \
  "$BASE/api/issues/{idReadable}/comments?fields=id"

# work item 등록 (date: 해당 일자 00:00 epoch ms, duration: 분)
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"date":{epochMs},"duration":{"minutes":240}}' \
  "$BASE/api/issues/{idReadable}/timeTracking/workItems?fields=id,date,duration(minutes)"
```

- epoch ms 계산 (macOS, 자정 고정): `echo $(($(date -j -f "%Y-%m-%d %H:%M:%S" "2026-08-04 00:00:00" "+%s") * 1000))`
- MCP 도구 사용 금지 — REST API만 (기존 `ad:*` 패턴)

## 주의사항

- 이미 종료된 티켓(resolved)은 다시 열지 않는다 — skip 보고만
- Won't fix·Obsolete 등 "미처리 종료" 상태도 resolved로 잡힌다 — 재오픈하지 않는다
- 승인 없이 상태 전환·코멘트·work item을 실행하지 않는다 (4단계 게이트가 유일한 승인 지점)
- 전사 상태 머신(`youtrack/ticket-guide.md`): In Progress → Fixed가 표준 경로. Fixed 이후 QA·Closed 처리는 이 스킬 범위 밖

ARGUMENTS: $ARGUMENTS
