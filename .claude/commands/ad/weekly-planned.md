# 주간 계획 스냅샷 작성

YouTrack `{YYMM}-planned` 태그 + 담당자 조건으로 Epic→Feature→Task 트리를 만들고, 옵시디언 운영 위키 `wiki/meetings/YYYY-MM-DD-wWW.md`에 주간 진행 현황 스냅샷을 저장합니다.

## 사용법

```
/ad:weekly-planned                                # 기본: 이번 달 태그, 김정민 + 조은흠
/ad:weekly-planned 김정민                           # 김정민만
/ad:weekly-planned 조은흠                           # 조은흠만
/ad:weekly-planned 김정민 조은흠                    # 다중 담당자
/ad:weekly-planned 2605-planned                    # 태그 직접 지정
/ad:weekly-planned 2605-planned 조은흠              # 태그 + 담당자
```

인자 파싱 규칙:
- `NNNN-planned` 패턴 → `tag` 값
- 그 외 한글/영문 → 담당자 이름(팀원 매핑 적용)
- 인자 미지정 시 오늘 날짜 기준 `{YY}{MM}-planned` 태그와 기본 담당자(김정민, 조은흠) 사용

## 팀원 매핑

| 이름 | YouTrack ID |
|------|-------------|
| 김정민 | jmkim |
| 조은흠 | heum2 |

> 신규 팀원은 이 테이블에 추가한다.

## 저장 위치

- 옵시디언 운영 위키 절대 경로: `/Users/user/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2`
- 파일 경로: `wiki/meetings/YYYY-MM-DD-wWW.md` (예: `wiki/meetings/2026-05-12-w20.md`)
- 날짜: 오늘(`date +%Y-%m-%d`), 주차: ISO week number (`date +%V`)
- 이미 파일이 있으면 본문만 갱신, frontmatter는 유지 (`updated_at`만 갱신)

## 보고서 양식

### Frontmatter

```yaml
---
type: meeting-note
title: YYYY-MM-DD WNN 주간 진행 현황 ({담당자들} {tag})
canonical_id: meeting:YYYY-MM-DD-wNN
status: active
updated_at: YYYY-MM-DD
sources:
  - youtrack-query: "tag: {tag} Assignee: {ytId1}"
  - youtrack-query: "tag: {tag} Assignee: {ytId2}"
---
```

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

Feature 라인:

```
- **{Feature 요약} ({일정}, {담당자}** {티켓ID}: {YouTrack 자동 링크용 티켓제목} **{표시용 제목})**
```

Task 라인(Feature 바로 아래, `:` 기호 prefix):

```
  : ({상태}) {Task 요약} ({일정}, {담당자} {티켓ID}: {YouTrack 자동 링크용 티켓제목} {표시용 제목})
```

**상태 말머리**: `(완료)`, `(진행 중)`, `(예정)`, `(보류)`, `(취소)`, `(재오픈)`

**일정 형식** (기존 weekly-report 가이드 §일정 형식과 동일):
- 백로그: 일정 없음
- 미진행/계획: `시작 예상 일자~`
- 진행중: `시작일~` 또는 `~목표일`
- 완료: `완료 일자`
- 지연: `~~기존목표~~ ~수정목표` + Feature 제목 뒤 `- 지연` + 지연 사유 줄

**섹션 배치 규칙**:
- 완료된 항목 → `## 완료된 항목`
- 진행 중 Task가 1개 이상 있으면 Feature → `## 진행중 항목`
- 모든 Task가 예정/Open이면 Feature → `## 계획 항목`
- Feature 자체가 Backlog/장기 보류 상태면 → `## 백로그 항목`

## 환경변수

| 변수 | 용도 |
|------|------|
| `$YOUTRACK_TOKEN` | YouTrack API 인증 토큰 |
| `$YOUTRACK_BASE_URL` | YouTrack 베이스 URL (기본: `https://aladincommunication.youtrack.cloud`) |

## 실행 지침

### 1. 인자 파싱

1. 현재 날짜로 `{YY}{MM}-planned` 기본 태그 계산 (예: 2026-05 → `2605-planned`)
2. 입력 인자에서 `\d{4}-planned` 패턴 매칭 → 태그 덮어쓰기
3. 남은 인자에서 팀원 매핑 테이블의 한글 이름 매칭 → 담당자 YouTrack ID 목록 구성
4. 담당자 미지정 시 기본값 `[jmkim, heum2]`

### 2. 티켓 수집

각 담당자에 대해 다음 쿼리를 YouTrack REST API로 실행한다. MCP 도구는 사용하지 않는다.

쿼리 식: `tag: {tag} Assignee: {ytId}`

```bash
BASE="${YOUTRACK_BASE_URL:-https://aladincommunication.youtrack.cloud}"
AUTH="Authorization: Bearer $YOUTRACK_TOKEN"

# 담당자별 티켓 검색 (페이지당 20개)
curl -s -H "$AUTH" \
  --data-urlencode "query=tag: {tag} Assignee: {ytId}" \
  --data-urlencode "fields=idReadable,summary,resolved,customFields(name,value(name,login))" \
  --data-urlencode '$top=20' \
  --data-urlencode '$skip=0' \
  -G "$BASE/api/issues"
```

- 응답 필드: `Type`, `State`, `Assignee`, `Sprints` (모두 `customFields`로 노출)
- 결과가 20개를 채우면 `$skip` 값을 20씩 증가시켜 끝까지 페이지네이션

### 3. 부모 해석

각 티켓의 `parentIssue`를 REST API로 조회하여 Epic→Feature→Task 트리 구성:
- Type=Task → parentIssue가 Feature/Epic이면 부모로 매핑
- Type=Feature → parentIssue가 Epic이면 부모로 매핑
- 태그 미보유 부모 Feature/Epic은 트리 유지를 위해 "참조 부모"로 표기

```bash
curl -s -H "$AUTH" \
  "$BASE/api/issues/{idReadable}?fields=idReadable,summary,customFields(name,value(name,login)),parentIssue(idReadable,summary,customFields(name,value(name)))"
```

### 4. 일정 추출

YouTrack 검색 API는 Due Date/Start date 커스텀 필드를 일관되게 반환하지 않으므로 다음 우선순위로 추출:
1. 티켓 코멘트의 "예상 시작 일자" / "시작일 변경" 텍스트
2. `resolvedAt` (완료 항목)
3. 추출 실패 시 일정 비워둠

### 5. 마크다운 생성

- 위 양식대로 항목 생성
- 섹션 배치 규칙에 따라 Feature 트리를 4개 섹션에 배치
- 이슈사항/기타 섹션은 사용자 입력이 없으면 `N/A`로 둠

### 6. 파일 저장

1. 옵시디언 위키 경로 계산: `/Users/user/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/meetings/{date}-w{week}.md`
2. 파일 존재 여부 확인
   - 존재 → frontmatter는 보존하고 본문만 덮어씀, `updated_at`만 오늘 날짜로 갱신
   - 미존재 → frontmatter 포함 신규 생성
3. 저장 후 파일 경로와 섹션별 항목 수 요약 출력

### 7. YouTrack 미반영

이 스킬은 로컬 위키 저장만 수행한다. YouTrack 티켓·KB 업데이트는 하지 않는다.

## 담당자별 항목 구분

- 다중 담당자 지정 시 본문은 담당자 구분 없이 하나의 4섹션 트리로 통합
- 각 항목의 `(담당자` 표기로 식별
- 김정민 보고서와 달리 별도 담당자 섹션은 만들지 않는다(이슈 트리 자체가 담당자 혼재)

## Feature 기간 초과 경고

기존 `ad:weekly-report` 와 동일 정책:
- 진행중 Feature 시작일이 7일 이상 경과 → `⚠️ 기간 초과` 표기
- 사용자에게 분할 또는 `- 지연` + 지연 사유 작성 안내

## 주의사항

- 옵시디언 위키 파일은 로컬 동기화 대상이므로 직접 Write로 저장한다 (별도 PR/커밋 없음).
- 이미 동일 파일이 있으면 본문만 갱신한다 (frontmatter `canonical_id` 보존).
- 검색 결과가 20개를 넘으면 offset 페이지네이션으로 끝까지 수집한다.
- 부모 해석 단계에서 같은 부모를 여러 번 호출하지 않도록 캐시한다.
- 사용자 확인 없이 파일을 저장하지 않는다 (저장 직전 경로·섹션 요약 후 확인 요청).

ARGUMENTS: $ARGUMENTS
