# 주간업무 보고서 작성

YouTrack KB와 티켓 정보를 기반으로 개인별 주간업무 보고서를 조회·업데이트합니다.

> 문서 위치 결정: harness `policies/knowledge-base-policy.md` (repo↔vault 경계) + vault `wiki/guides/document-placement.md` (vault 내부 트리).

## 사용법

```
/ad:weekly-report                          # 내(김정민) 보고서 조회
/ad:weekly-report 조은흠                    # 조은흠 보고서 조회
/ad:weekly-report 업데이트                  # 내 보고서 금주 한일 업데이트
/ad:weekly-report 조은흠 업데이트            # 조은흠 보고서 업데이트
/ad:weekly-report 조은흠 추가 [내용]         # 조은흠 항목 추가
/ad:weekly-report 전체                      # 전체 팀원 보고서 조회
/ad:weekly-report 동기화                    # YouTrack 티켓 상태 기반 자동 동기화
/ad:weekly-report 초안                      # 옵시디언 vault에 이번주 초안 작성 (KB 미반영)
/ad:weekly-report 이번주 초안 작성해줘        # 위와 동일 (자연어)
```

## 팀원 매핑

| 이름 | 이니셜 | YouTrack ID | 역할 | 비고 |
|------|--------|-------------|------|------|
| 김정민 | KJM | jmkim | 백엔드 (메인) | 기본값 |
| 조은흠 | JEH | heum2 | 프론트엔드 (서브) | 김정민 보고서에 항목 포함 |
| 박민석 | PMS | pms0905 | 백엔드/프론트엔드 | 김정민 보고서에 항목 포함, 2026-05-14 합류 |
| 안혜련 | AHR | hyeryun | 백엔드 (storefront) | 김정민 보고서에 항목 포함 |

> 팀원 추가 시 이 테이블에 행을 추가하면 됩니다.

## YouTrack KB 구조

```
DEV2-A-692 (주간업무)
└── DEV2-A-693 (2026 1Q/2Q)
    ├── DEV2-A-694 (조윤주)
    ├── DEV2-A-695 (이현민)
    ├── DEV2-A-696 (김정민)     ← 김정민 + 조은흠 + 박민석 + 안혜련 항목 포함
    └── DEV2-A-830 (2026.05.2W) ← 주간 스냅샷
```

## 보고서 양식

> 상세 가이드: `docs/sprint/weekly-report-guide.md`
> 양식의 source of truth는 YouTrack KB `DEV2-A-696` 원본. 가이드 §5 템플릿과 KB 원본이 다르면 KB 원본을 따른다.

### 섹션 구조

```
## **백로그 항목**
## **계획 항목**
## **진행중 항목**
## **완료된 항목**
## **이슈사항**
## **기타**
```

- H2 헤더 안에 `**` bold 처리 (KB 원본 패턴)

### 항목 형식 (KB 원본 패턴)

**제목 라인** (top-level):

```
* **{제목} ({일정정보}, {담당자}** DEV2-xxxx **\[원문제목\])**
```

- 불릿 `*` (하이픈 `-` 아님)
- `**` 짝 2개로 `(담당자**` ... **`\[원문제목\])` 감싼다
- 원문제목의 대괄호는 `\[` `\]` escape (KB 마크다운 렌더링 호환)

**본문 라인** (sub-task 또는 단일 본문):

```
  : ({상태}) {간략 설명} ({일정정보}, {담당자} DEV2-yyyy [원문제목])
```

- 2-space indent + `:` + space (불릿 아님)
- 본문 라인 대괄호는 **escape 없이** `[원문제목]` 그대로 (KB 자동 링크 동작)

**Feature 하위가 없거나 단일 Task인 경우**:

- 본문 라인은 **반드시 작성**
- 본문 라인의 티켓 정보(`DEV2-xxxx [원문제목]`)는 **제목과 동일**하게 반복

예시 (단일 본문):

```
* **만권당 5월 이벤트 (5월의 책) (5/13, 조은흠** DEV2-5259 **\[만권당\]\[개발\] 5월 이벤트 (5월의 책))**
  : (완료) 5월의 책 디자인/개발 일정 (5/13, 조은흠 DEV2-5259 [만권당][개발] 5월 이벤트 (5월의 책))
```

예시 (다중 sub-task):

```
* **\[AASM\] IAM Access Key → Node Role + Self-Assume 마이그레이션 (5/15, 김정민** DEV2-6223 **\[AASM\] IAM Access Key → Node Role + Self-Assume 마이그레이션)**
  : (완료) S3 클라이언트 빌더 신설 + 진입점 제한 (5/15, 김정민 DEV2-6225 [AASM] S3 클라이언트 빌더 신설 + 진입점 제한)
  : (완료) S3 연산 모듈 시그니처 일괄 변경 (5/15, 김정민 DEV2-6226 [AASM] S3 연산 모듈 시그니처 일괄 변경)
```

**표기 규칙**:

- 앞 간략 설명은 보고서 흐름상 짧게 요약 (Task 본질만)
- 티켓번호(`DEV2-xxxx`) 뒤에는 YouTrack 티켓 제목을 **수정 없이 그대로** 기재 (대괄호 prefix `[서비스][직군]` 포함). YouTrack 자동 링크와 원본 맥락 보존 목적

**상태 말머리**: `(완료)`, `(진행 중)`, `(예정)`, `(보류)`

**일정 형식**:

- 백로그: 일정 없음 (보류 메모만 필요 시 추가)
- 계획(예정): 시작 예상 일자~
- 진행중: ~완료 예상 일자
- 완료: 완료 일자
- 지연: ~~기존목표~~ ~수정목표, 제목 뒤 `- 지연`, 지연 사유 기재

## 기록 대상 필터

가이드 `docs/sprint/weekly-report-guide.md` §1 원칙 강화:

**포함**:

- 팀 구성원 작성 Feature/Epic 중심
- Type=Feature 또는 Epic
- 하위 Task는 부모 Feature 컨텍스트로만 본문 라인에 표기

**제외**:

- 사업부 작성 운영성 단발 Task/Bug (통계요청·점검요청·팀장승인·앱푸시 발송 리스트 등)
- 단발 운영 대응 (DB 정산 오류 확인, 사용자 개별 문의 등)
- 가이드 §1 "예외적으로 포함"은 **이슈 규모가 크거나 팀 차원 공유가 필요한 운영성 업무**로만 한정

판단 기준:

| 항목 | 포함 여부 |
|------|----------|
| Type=Feature/Epic, 팀 구성원 작성 | 포함 |
| Type=Feature, 사업부 작성 운영 (예: 멀티캠퍼스 IF) | 검토 후 결정 (계획 업무 성격이면 포함) |
| Type=Task, 사업부 단발 운영 요청 | 제외 |
| Type=Bug, 단발 장애/점검 | 제외 |

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

### 6. 초안 모드 (옵시디언)

사용자가 `/ad:weekly-report 초안` 또는 `이번주 초안 작성해줘` 류를 입력하면:

1. **기존 보고서 조회**: KB(DEV2-A-696) 현재 내용 가져오기
2. **상태 동기화**: 보고서 내 모든 티켓ID + 담당자별 In Progress + 최근 14일 resolved 일괄 조회
3. **필터 적용**: Type=Feature/Epic only. 운영성 Task/Bug 제외 (위 "기록 대상 필터" 참조)
4. **양식 정렬**: 위 "항목 형식" 패턴 그대로 적용
   - 제목 라인: `*` + 이중 `**` 분할 + 원문제목 `\[`/`\]` escape
   - 본문 라인: `  : ` + 본문 + `(일정정보, 담당자 DEV2-xxxx [원문제목])`
   - Feature 하위 없거나 단일 Task인 경우 본문에 동일 티켓 정보 반복
5. **저장 경로**: 옵시디언 vault — `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/processes/weekly/YYYY-MM-NW-draft.md`
   - W 번호 = 해당 월 N주차 (월 첫 월요일 시작 기준)
   - 임시본은 vault 외부 작성 금지 (CLAUDE.md "도메인 분석 결과는 로컬 Obsidian 운영 지식 위키" 정책)
6. **frontmatter 포함**:
   ```yaml
   ---
   title: YYYY-MM-NW 주간업무 초안
   date: YYYY-MM-DD
   status: draft
   source: YouTrack DEV2-A-696 + N일 상태 동기화
   filter: Type=Epic/Feature only. 운영대응(Task/Bug) 제외
   note: 옵시디언 임시 저장본. KB 반영은 사용자 수동
   ---
   ```
7. **KB 자동 반영 금지** — TODO 섹션에 검토 포인트 명시 후 사용자가 수동으로 합침
8. **이슈사항/기타** 섹션에 일정 리스크·합류·제외 사유 등 자유 기록

## 담당자별 항목 구분

김정민 보고서에 조은흠·박민석·안혜련 항목이 혼재되어 있으므로:
- **담당자 식별**: 각 항목의 `(담당자` 부분에서 이름 추출
- **개별 조회 시**: 김정민 보고서에서 해당 팀원 담당 항목만 필터링하여 표시
- **개별 추가 시**: 김정민 보고서의 적절한 섹션에 해당 팀원 담당으로 항목 삽입

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

## frontmatter 표준 (티켓 산출물)

```yaml
---
type: ticket
ticket_id: DEV2-XXXX
ticket_status: auto-prep | in-progress | done | backlog
assignee: jmkim
service: max
sprint: 2026-05
type_yt: feature | task | bug
---
```

상세: vault `wiki/guides/frontmatter-spec.md`.

ARGUMENTS: $ARGUMENTS
