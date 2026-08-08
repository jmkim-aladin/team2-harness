---
description: 주간업무 보고서 작성
---

# 주간업무 보고서 작성

YouTrack KB와 티켓 정보를 기반으로 개인별 주간업무 보고서를 조회·업데이트한다.

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

로스터 SoT: [policies/team-members.md](../../../policies/team-members.md) — 이름·YouTrack ID·역할은 그 표를 따른다 (dev role 정직원 대상).

- 기본 담당자: 김정민(jmkim). 다른 dev 팀원 항목도 김정민 보고서에 포함

## YouTrack KB 구조

```
DEV2-A-692 (주간업무)
└── DEV2-A-693 (2026 1Q/2Q)
    ├── DEV2-A-694 (조윤주)
    ├── DEV2-A-695 (이현민)
    ├── DEV2-A-696 (김정민)     ← 김정민 + 조은흠 + 박민석 + 안혜련 항목 포함
    └── DEV2-A-830 (2026.05.2W) ← 주간 스냅샷

DEV2-A-1351 (주간업무 핵심 목표)   ← parent: DEV2-A-1 (Team). 주간업무 트리와 별도
└── DEV2-A-1352 (2026.07.5W)      ← 주차별 문서. 담당자별 핵심목표 2개 (2026-08-03 주차부터. 도입 주 2026.07.5W는 1~4개)
```

- 핵심목표 트리는 `DEV2-A-692`(주간업무) 하위가 **아니다**. `DEV2-A-1351`의 `childArticles`에서 대상 주차 문서를 직접 찾는다.
- 주차 표기는 해당 월 1일 기준(7/27~31 = `2026.07.5W`)이라 vault 파일명 주차(월 첫 월요일 기준, `2026-07-4W`)와 다를 수 있다. 파일명 규칙은 바꾸지 않고 인용 시 KB 원문 주차를 그대로 적는다.

## 보고서 양식

> 상세 가이드: `docs/sprint/weekly-report-guide.md`
> 라인 포맷의 source of truth는 가이드 **§4-B (2026-07 개편)**. KB `DEV2-A-696`가 신규 포맷으로 이관되기 전까지 초안 작성은 §4-B를 우선한다. §4.1~4.4 레거시 패턴은 기존 KB 원본 조회·호환용.

### 섹션 구조

```
## 이번 주 요약          ← 신규(§4-B.1): 건수 + 담당자별 표 + 하이라이트
## 이번 주 핵심목표      ← 신규(§4-B.1.1): KB DEV2-A-1351 하위 주차 문서 취합
## **백로그 항목**
## **계획 항목**
## **진행중 항목**
## **완료된 항목**
## **이슈사항**
## **기타**
```

- H2 헤더 안에 `**` bold 처리 (KB 원본 패턴). `## 이번 주 요약`·`## 이번 주 핵심목표`만 bold 없이 둔다.
- `## **백로그 항목**`은 KB 양식 호환용 섹션이다. 최종 주간보고 후보 생성 시 Backlog 상태 티켓은 제외하고, 새 항목을 넣지 않는다.

### 항목 형식·예정일 산정

SoT: [docs/sprint/weekly-report-guide.md](../../../docs/sprint/weekly-report-guide.md)

- **보고 포맷 (신규 표준)**: 가이드 §4-B — 이번 주 요약 섹션, 상태 섹션 내 서비스 그룹핑(그룹명 한글: 바자르·나루 등), 라인 단순화(제목 1회 + `DEV2-xxxx` ID만), 하위 Task 날짜는 **(완료)만 표시**
- **이번 주 핵심목표**: 가이드 §4-B.1.1 — `DEV2-A-1351` 하위 주차 문서를 담당자·항목 순서·문구·티켓 ID **원문 그대로** 옮긴다. 상태·일정정보·`티켓 미발행`·출처 인용·제외 사유 각주 같은 **보강은 넣지 않는다**. 핵심목표 섹션과 상태 섹션의 ID 중복은 허용. 운영 원칙(주 2개·산출물 증명·미달성 원인/재발방지 기록)은 [docs/sprint/weekly-goal-policy.md](../../../docs/sprint/weekly-goal-policy.md)
- **항목 표기 레거시** (제목 2회 반복, escape, 일정 형식): 가이드 §4.1~4.4 — 기존 KB 원본 읽을 때만 참조
- **일정정보 방향 고정** (근거: 방향 오기 반복 — 회차 다수): 진행중 = 항상 `~M/D`(완료 경계), 계획 = 항상 `M/D~`(시작 경계). 가이드 §4.4 방향 고정 규칙
- **이월 검토 표시**: 가이드 §4-B.5 — 코멘트에 이월·범위 제외 결정이 있어도 상태가 `Open`이면 본문에서 빼지 않는다. 계획 항목에 두고 제목 끝에 ` - {대상} 이월 검토` 마커 + 일정정보를 `{N}월~`/`{N}분기~`로 바꾼다. 실제 `Backlog` 전환 후부터 제외
- **예정일 선택·fallback**: 가이드 §4.5 — 미착수는 `코멘트 시작예정일 → 착수일 fallback → 미기록`, 진행중은 `코멘트 완료목표 → 대상 월 스프린트 종료일(예: 2026-07 → ~7/31) + 이슈사항에 완료목표 미기재 기록`. 착수일 fallback은 미착수 전용이며 완료 목표로 쓰지 않는다. 예외: `{서비스} N월 운영` umbrella는 운영 기간이라 `M/D~` 유지
- 보고서 작성·동기화 시점에 가이드 해당 절을 읽어 그대로 적용한다. 티켓 조회 시 `comments(text,created,updated)` 필드 포함 (아래 API 참조 #3). 착수일 fallback이 필요하면 `activities?categories=CustomFieldCategory` 로 State 전환시각 조회 (API 참조 #6)

## 기록 대상 필터

원칙 SoT: 가이드 §1 (포함/제외/예외). 실행용 판단 기준:

| 항목 | 포함 여부 |
|------|----------|
| Type=Feature/Epic, 개발자 담당, 대상 월 스프린트 일치 | 포함 |
| Type=Feature/Epic, 기획자/디자이너 담당, 개발자 하위 Task 있음 | 부모는 컨텍스트로 포함, 개발자 Task만 본문 표기 |
| Type=Feature/Epic, 기획자/디자이너 담당, 개발자 하위 Task 없음 | 제외 |
| Type=Feature/Epic, Backlog | 제외 |
| Type=Feature/Epic, 대상 월 스프린트 불일치 | 제외 |
| Type=Feature, 사업부 작성 운영 (예: 멀티캠퍼스 IF) | 개발자 담당 + 대상 월 스프린트 일치 시 검토 후 포함 |
| Type=Task, 사업부 단발 운영 요청 | 제외 |
| Type=Bug, 단발 장애/점검 | 제외 |

### 최종본 중복 제거 규칙

레벨별 ID 중복 제거 원칙은 가이드 §1 "중복 제거" (SoT). 스킬 실행 추가 규칙:

- 중복 점검은 저장 전 `DEV2-*` ID의 레벨별 빈도 기준으로 수행한다.
- 사용자가 "현재 KB가 최종"이라고 하면 YouTrack KB `DEV2-A-696`은 비교 기준이다. 별도 명시 승인 없이는 KB `POST` 업데이트를 하지 않는다.

## 환경변수

> YouTrack 환경변수·인증 셋업은 [youtrack/api-guide.md](../../../youtrack/api-guide.md)를 따른다.

## API 참조

```bash
# BASE·AUTH 셋업: youtrack/api-guide.md

# 1. 분기별 부모 문서 조회 (주간업무 하위)
curl -s -H "$AUTH" \
  "$BASE/api/articles/DEV2-A-692?fields=childArticles(idReadable,summary)"

# 2. 개인 보고서 조회 → KB 상세 (youtrack/api-guide.md)

# 3. 티켓 상태·예정일 코멘트 조회 (동기화용)
curl -s -H "$AUTH" \
  "$BASE/api/issues/{issueId}?fields=idReadable,summary,customFields(name,value(name)),comments(text,created,updated)"

# 4. 담당자별 티켓 검색 (진행중 항목 탐색)
curl -s -H "$AUTH" \
  "$BASE/api/issues?query=project:DEV2+assignee:{ytId}+state:In+Progress&fields=idReadable,summary,customFields(name,value(name))&\$top=50"

# 5. KB 문서 업데이트
curl -s -X POST -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{"content": "..."}' \
  "$BASE/api/articles/{articleId}"

# 6. 착수일 fallback — State가 In Progress로 전환된 시각 (가이드 §4.5)
curl -s -H "$AUTH" \
  "$BASE/api/issues/{issueId}/activities?categories=CustomFieldCategory&fields=timestamp,field(name),added(name)"
# field.name == State, added에 In Progress 포함된 최초 항목의 timestamp 사용. 없으면 created.

# 7. 주간 핵심목표 — 주차 문서 탐색 후 본문 조회 (가이드 §4-B.1.1)
curl -s -H "$AUTH" \
  "$BASE/api/articles/DEV2-A-1351?fields=childArticles(idReadable,summary,updated)"
curl -s -H "$AUTH" \
  "$BASE/api/articles/{weekArticleId}?fields=idReadable,summary,content,updated"
```

**API 응답 주의** (근거: 2026-07-29 실측 — 실패 사례 기반, 완화 대상 아님):

- `customFields`의 `Assignee.value`는 `name`(표시명)과 `login`이 함께 온다. 담당자 필터는 **`login`**으로 비교한다. `name`으로 비교하면 dev 필터가 전부 탈락해 신규 항목 탐색이 빈 결과를 낸다.
- `activities`의 `field.name`은 **로컬라이즈되어 `상태`로 온다**. 착수일 판정은 `field.name in ("State", "상태")` 둘 다 허용해야 한다.
- 신규 항목 탐색은 보고서 본문 ID 목록만 재조회하지 말고 `Sprints:{대상월}` · `tag:{YYMM}-planned` · `State:{In Progress}` · `resolved date:{대상월 범위}` 를 각각 질의해 합집합으로 만든 뒤 본문에 없는 dev Feature/Epic을 찾는다.

## 실행 지침

### 1. 조회 모드 (기본)

사용자가 `/ad:weekly-report` 또는 `/ad:weekly-report {이름}`을 입력하면:

1. **현재 분기 판별**: 오늘 날짜 기준으로 분기 계산
2. **KB 문서 탐색**: DEV2-A-692 하위에서 해당 분기 문서 → 해당 팀원 문서 순으로 탐색
3. **보고서 표시**: YouTrack HTML을 마크다운으로 변환하여 표시
4. 이름 없으면 기본값 김정민

### 2. 업데이트 모드

사용자가 `/ad:weekly-report 업데이트` 또는 `/ad:weekly-report {이름} 업데이트`를 입력하면:

1. **현재 보고서 조회**: KB에서 최신 보고서 가져오기
2. **금주 변동 파악**: 사용자에게 이번 주 완료/진행/신규 항목을 질문
3. **티켓 상태·예정일 확인**: 언급된 티켓ID가 있으면 YouTrack에서 실제 상태와 코멘트를 조회하여 교차 검증
4. **보고서 갱신**: 항목 이동 및 내용 추가
   - 완료된 항목: 진행중 → 완료로 이동, 완료 일자 기재
   - 새로 시작: 계획 → 진행중으로 이동
   - Backlog 상태는 최종 주간보고 후보에서 제외
   - 신규 항목: 해당 섹션에 추가
   - Task 말머리: (예정) → (진행 중) → (완료) 갱신
   - 대상 스프린트의 미착수·미종료 Feature/Task: 가이드 §4.5 예정일 규칙으로 일정정보 갱신
5. **마크다운 출력**: 갱신된 보고서를 마크다운으로 출력
6. **KB 반영 제안**: §최종본 중복 제거 규칙의 KB 게이트를 따른다

### 3. 항목 추가 모드

사용자가 `/ad:weekly-report {이름} 추가 [내용]`을 입력하면:

1. **현재 보고서 조회**
2. **추가할 항목 파악**: 내용에서 티켓ID, 섹션, 상태 추출
3. **티켓 정보 보강**: 티켓ID가 있으면 YouTrack에서 상세 정보와 예정일 코멘트 조회
4. **양식에 맞게 항목 생성**: 보고서 양식에 맞춰 항목 포맷팅
5. **적절한 섹션에 삽입**
6. **마크다운 출력 및 KB 반영 제안**

### 4. 동기화 모드

사용자가 `/ad:weekly-report 동기화`를 입력하면:

1. **현재 보고서 조회**
2. **보고서 내 모든 티켓ID 추출**
3. **YouTrack API로 각 티켓 현재 상태·코멘트 일괄 조회**
4. **상태·일정 불일치 감지**: 보고서 상태와 일정정보를 실제 티켓 상태·예정일 코멘트와 비교
5. **변경 제안**: 상태 불일치와 날짜 fallback/미기록 항목을 표시하고 자동 갱신 제안
6. **사용자 확인 후 반영**

### 5. 전체 조회 모드

사용자가 `/ad:weekly-report 전체`를 입력하면:

1. 현재 분기 부모 문서 하위의 모든 팀원 문서 조회
2. 팀원별로 정리하여 표시

### 6. 초안 모드 (옵시디언)

사용자가 `/ad:weekly-report 초안` 또는 `이번주 초안 작성해줘` 류를 입력하면:

1. **기존 보고서 조회**: KB(DEV2-A-696) 현재 내용 가져오기
1-1. **핵심목표 조회**: `DEV2-A-1351` 하위에서 대상 주차 문서를 찾아 본문을 가져온다 (API 참조 #7). 대상 주차 문서가 없으면 최신 주차를 사용하고 이슈사항에 남긴다. 본문은 담당자·순서·문구·티켓 ID 그대로 `## 이번 주 핵심목표` 섹션에 옮기고 **아무 보강도 하지 않는다** (가이드 §4-B.1.1)
2. **동월 기준본 유지**: 현재 초안의 대상 월이 KB/직전 주차와 같은 월이면 기존 본문 목록을 기준본으로 유지한다. 새 주차 변동분만 요약해 새 본문을 만들지 않는다. 상태 이동(계획→진행중→완료), 하위 본문 보강, 신규 항목 추가, 같은 레벨 중복 제거만 수행한다. 월이 바뀔 때만 해당 월 스프린트/태그 기준으로 목록을 새로 구성한다.
3. **상태·예정일 동기화**: 보고서 내 모든 티켓ID + 담당자별 In Progress + 대상 월 resolved를 조회하고, 미착수·미종료 Feature/Task의 코멘트도 일괄 조회
   - **신규 항목 누락 방지**: §API 응답 주의의 신규 항목 탐색 규칙대로 합집합 질의로 편입한다 (assignee 비교는 `login`)
   - **섹션 재배치**: 기존 본문 섹션 위치보다 현재 top-level Feature/Epic 상태를 우선한다. Open/Reopened→계획, In Progress→진행중, Fixed/Closed/Verified→완료된, Backlog→본문 제외로 이동한다. 하위 Task 상태가 부모와 어긋나면 하위 말머리를 실제 상태로 보정하고 이슈사항에 남긴다.
   - **이월 결정 항목**: 코멘트에 이월·범위 제외 결정이 있어도 상태가 `Open`이면 계획 항목에 유지하고 ` - {대상} 이월 검토` 마커와 `{N}월~`/`{N}분기~` 일정정보를 붙인다 (가이드 §4-B.5). 임의 제외 금지 — 제외 판단은 사용자가 한다.
   - **일정정보 갱신**: 가이드 §4.5 규칙에 따라 자체 코멘트 날짜를 우선하고 Feature↔Task fallback을 한 번만 적용한다. 방향은 상태로 고정한다 — 진행중 `~M/D`, 계획 `M/D~`. 진행중에 완료목표 코멘트가 없으면 대상 월 스프린트 종료일을 `~M/D`로 쓰고 이슈사항에 미기재로 남긴다(착수일로 대체 금지). 미착수는 착수일 fallback, 근거가 없으면 붉은색 `미기록`.
   - **저장 전 자체 점검 (명령)**: `grep -nE '[0-9]{1,2}/[0-9]{1,2}~' {저장경로}` 를 돌려 `진행중 항목` 섹션 범위 안의 히트가 **0**인지 확인한다 (`{서비스} N월 운영` umbrella만 예외). 0이 아니면 방향 오류다.
4. **필터 적용**: Type=Feature/Epic only. 운영성 Task/Bug 제외 (위 "기록 대상 필터" 참조)
   - **월별 계획 스냅샷("N월거만") 작성 시**: YouTrack 태그 `YYMM-planned`(예: 2026년 6월 = `2606-planned`) 또는 `Sprints=YYYY.MM` + 개발자 assignee 로 필터. 디자인/기획 상위 Feature는 기본 제외하되, 하위 Task가 개발자 담당이면 부모 Feature를 컨텍스트로만 포함하고 개발자 Task만 본문 라인으로 롤업. 이전 달 누적 완료분은 태그/스프린트가 대상 월과 맞지 않으면 제외됨. 상태별 섹션 매핑: In Progress→진행중, Open/Reopened→계획, Fixed/Closed/Verified→완료된. **Backlog는 제외.**
   - **개발자 assignee 기준**: [policies/team-members.md](../../../policies/team-members.md)의 dev role 표를 따른다 (YouTrack login 기준).
   - **완료 항목**: 대상 월에 완료된 항목은 유지한다. 최근 7/14일 완료분만 남기지 않는다.
   - **중복 제거**: 저장 전 `DEV2-*` ID의 레벨별 빈도를 점검하고, 같은 레벨의 중복 top-level 또는 본문 라인만 제거한다. top-level과 하위 본문 라인의 반복은 허용한다.
5. **양식 정렬**: 가이드 §4·§5 패턴 그대로 적용
   - **Obsidian 줄바꿈** (스킬 고유): 제목 라인·`: ` 본문 라인 끝에 공백 2칸(markdown hard break) 추가. 미적용 시 `: ` 하위 라인이 bullet lazy-continuation으로 한 단락에 합쳐져 줄바꿈이 사라짐 (KB/YouTrack 렌더와 달리 Obsidian에서 필요)
6. **저장 경로**: 옵시디언 vault — `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/processes/weekly/YYYY-MM-NW-{assignee}.md` (예: `2026-06-1W-jmkim.md`)
   - 파일명은 Tolaria weekly-report 규약(`templates/vault-notes/weekly-report.md`) 준수 — assignee 슬러그 사용, `-draft` 금지. 초안 여부는 frontmatter `status: draft`로 표기
   - 파일명·frontmatter `title`·`canonical_id` 는 동일 키(`YYYY-MM-NW-{assignee}`)로 통일
   - W 번호 = 해당 월 N주차 (월 첫 월요일 시작 기준)
   - 임시본은 vault 외부 작성 금지
7. **frontmatter 포함** (Tolaria weekly-report 규약):
   ```yaml
   ---
   type: weekly-report
   title: YYYY-MM-NW {담당자} 주간업무
   canonical_id: weekly-report:YYYY-MM-NW-{assignee}
   status: draft
   updated_at: YYYY-MM-DD
   assignee: {assignee}
   year: YYYY
   month: M
   week_in_month: N
   sprint: YYYY-MM
   source: YouTrack DEV2-A-696 + N일 상태 동기화 (또는 YYMM-planned 태그)
   filter: Type=Epic/Feature only. 운영대응(Task/Bug) 제외
   note: 옵시디언 임시 저장본. KB 반영은 사용자 수동
   ---
   ```
   - `type`/`year`/`month`/`week_in_month`/`assignee` 는 Tolaria weekly-report 필수 필드(`tools/lint_vault.py`). 본문은 KB(DEV2-A-696) 원본 모양 그대로 — H1·llm-hint 없이 `## **백로그 항목**`부터 시작. 저장 후 `python3 tools/lint_vault.py --vault <vault> --files <경로>` 로 검증
8. **KB 반영**: §최종본 중복 제거 규칙의 KB 게이트를 따른다 — TODO 섹션에 검토 포인트만 남긴다
9. **이슈사항/기타** 섹션에 일정 리스크·합류·제외 사유 등 자유 기록

## 담당자별 항목 구분

김정민 보고서에 조은흠·박민석·안혜련 항목이 혼재되어 있으므로:
- **담당자 식별**: 각 항목의 `(담당자` 부분에서 이름 추출
- **개별 조회 시**: 김정민 보고서에서 해당 팀원 담당 항목만 필터링하여 표시
- **개별 추가 시**: 김정민 보고서의 적절한 섹션에 해당 팀원 담당으로 항목 삽입

## Feature 기간 초과 경고

Feature는 총 기간 1주일 이내가 필수 규칙 (`docs/sprint/ticket-guide.md` 2항).
주간보고 동기화/업데이트 시 아래 검증을 수행:

- **진행중 Feature의 시작일이 7일 이상 경과**: `⚠️ 기간 초과` 경고 표시
- **경고 시 안내**: "Feature `{티켓ID}`가 {N}일째 진행 중이다. 1주일 규칙 초과. 분할 또는 지연 사유 기재가 필요하다."
- **지연 처리**: 보고서에 `- 지연` 표시 + 지연 사유 작성 유도

## 주의사항

- 분기 전환 시 새 분기 문서가 없으면 생성 안내

## frontmatter 표준 (티켓 산출물)

vault `wiki/guides/frontmatter-spec.md` (SoT)의 ticket 스키마를 따른다 — 티켓 노트 작성 시점에 해당 파일을 읽어 최신 스키마 사용.

ARGUMENTS: $ARGUMENTS
