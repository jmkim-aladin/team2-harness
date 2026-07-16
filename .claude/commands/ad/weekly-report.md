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
- `## **백로그 항목**`은 KB 양식 호환용 섹션이다. 최종 주간보고 후보 생성 시 Backlog 상태 티켓은 제외하고, 새 항목을 넣지 않는다.

### 항목 형식·예정일 산정

SoT: [docs/sprint/weekly-report-guide.md](../../../docs/sprint/weekly-report-guide.md)

- **항목 표기** (제목/본문 라인, escape, 단일 Task 반복, 일정 형식): 가이드 §4.1~4.4
- **예정일 선택·fallback** (코멘트 의미 추출, Feature↔Task 상속 표, `미기록` 처리): 가이드 §4.5
- 보고서 작성·동기화 시점에 가이드 해당 절을 읽어 그대로 적용한다. 티켓 조회 시 `comments(text,created,updated)` 필드 포함 (아래 API 참조 #3)

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

# 3. 티켓 상태·예정일 코멘트 조회 (동기화용)
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" \
  "$BASE/api/issues/{issueId}?fields=idReadable,summary,customFields(name,value(name)),comments(text,created,updated)"

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
3. **티켓 상태·예정일 확인**: 언급된 티켓ID가 있으면 YouTrack에서 실제 상태와 코멘트를 조회하여 교차 검증
4. **보고서 갱신**: 항목 이동 및 내용 추가
   - 완료된 항목: 진행중 → 완료로 이동, 완료 일자 기재
   - 새로 시작: 계획 → 진행중으로 이동
   - Backlog 상태는 최종 주간보고 후보에서 제외
   - 신규 항목: 해당 섹션에 추가
   - Task 말머리: (예정) → (진행 중) → (완료) 갱신
   - 대상 스프린트의 미착수·미종료 Feature/Task: 가이드 §4.5 예정일 규칙으로 일정정보 갱신
5. **마크다운 출력**: 갱신된 보고서를 마크다운으로 출력
6. **KB 반영 제안**: 사용자 확인 후 YouTrack KB API로 업데이트 (확인 필수)

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
2. **동월 기준본 유지**: 현재 초안의 대상 월이 KB/직전 주차와 같은 월이면 기존 본문 목록을 기준본으로 유지한다. 새 주차 변동분만 요약해 새 본문을 만들지 않는다. 상태 이동(계획→진행중→완료), 하위 본문 보강, 신규 항목 추가, 같은 레벨 중복 제거만 수행한다. 월이 바뀔 때만 해당 월 스프린트/태그 기준으로 목록을 새로 구성한다.
3. **상태·예정일 동기화**: 보고서 내 모든 티켓ID + 담당자별 In Progress + 대상 월 resolved를 조회하고, 미착수·미종료 Feature/Task의 코멘트도 일괄 조회
   - **섹션 재배치**: 기존 본문 섹션 위치보다 현재 top-level Feature/Epic 상태를 우선한다. Open/Reopened→계획, In Progress→진행중, Fixed/Closed/Verified→완료된, Backlog→본문 제외로 이동한다. 하위 Task 상태가 부모와 어긋나면 하위 말머리를 실제 상태로 보정하고 이슈사항에 남긴다.
   - **일정정보 갱신**: 가이드 §4.5 규칙에 따라 자체 코멘트 날짜를 우선하고 Feature↔Task fallback을 한 번만 적용한다. 근거가 없으면 붉은색 `미기록`으로 남긴다.
4. **필터 적용**: Type=Feature/Epic only. 운영성 Task/Bug 제외 (위 "기록 대상 필터" 참조)
   - **월별 계획 스냅샷("N월거만") 작성 시**: YouTrack 태그 `YYMM-planned`(예: 2026년 6월 = `2606-planned`) 또는 `Sprints=YYYY.MM` + 개발자 assignee 로 필터. 디자인/기획 상위 Feature는 기본 제외하되, 하위 Task가 개발자 담당이면 부모 Feature를 컨텍스트로만 포함하고 개발자 Task만 본문 라인으로 롤업. 이전 달 누적 완료분은 태그/스프린트가 대상 월과 맞지 않으면 제외됨. 상태별 섹션 매핑: In Progress→진행중, Open/Reopened→계획, Fixed/Closed/Verified→완료된. **Backlog는 제외.**
   - **개발자 assignee 기준**: 김정민(jmkim), 조은흠(heum2), 박민석(pms0905), 안혜련(hyeryun), 박희수(heesoo), 조주영(jjy), 강인용(iyk; YouTrack 검색 가능 시). 팀원 변동 시 `policies/team-members.md`를 우선한다.
   - **완료 항목**: 대상 월에 완료된 항목은 유지한다. 최근 7/14일 완료분만 남기지 않는다.
   - **중복 제거**: 저장 전 `DEV2-*` ID의 레벨별 빈도를 점검하고, 같은 레벨의 중복 top-level 또는 본문 라인만 제거한다. top-level과 하위 본문 라인의 반복은 허용한다.
5. **양식 정렬**: 가이드 §4·§5 패턴 그대로 적용
   - **Obsidian 줄바꿈** (스킬 고유): 제목 라인·`: ` 본문 라인 끝에 공백 2칸(markdown hard break) 추가. 미적용 시 `: ` 하위 라인이 bullet lazy-continuation으로 한 단락에 합쳐져 줄바꿈이 사라짐 (KB/YouTrack 렌더와 달리 Obsidian에서 필요)
6. **저장 경로**: 옵시디언 vault — `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/wiki/processes/weekly/YYYY-MM-NW-{assignee}.md` (예: `2026-06-1W-jmkim.md`)
   - 파일명은 Tolaria weekly-report 규약(`templates/vault-notes/weekly-report.md`) 준수 — assignee 슬러그 사용, `-draft` 금지. 초안 여부는 frontmatter `status: draft`로 표기
   - 파일명·frontmatter `title`·`canonical_id` 는 동일 키(`YYYY-MM-NW-{assignee}`)로 통일
   - W 번호 = 해당 월 N주차 (월 첫 월요일 시작 기준)
   - 임시본은 vault 외부 작성 금지 (CLAUDE.md "도메인 분석 결과는 로컬 Obsidian 운영 지식 위키" 정책)
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
8. **KB 자동 반영 금지** — TODO 섹션에 검토 포인트 명시 후 사용자가 수동으로 합침
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
- **경고 시 안내**: "Feature `{티켓ID}`가 {N}일째 진행 중입니다. 1주일 규칙 초과. 분할 또는 지연 사유 기재가 필요합니다."
- **지연 처리**: 보고서에 `- 지연` 표시 + 지연 사유 작성 유도

## 주의사항

- KB 업데이트는 반드시 사용자 확인 후 실행 (자동 반영 금지)
- 보고서 양식은 `docs/sprint/weekly-report-guide.md` 기준 준수
- 티켓 링크 형식: `{담당자} {티켓ID} {티켓명}` (YouTrack 자동 링크)
- 지연 항목은 반드시 지연 사유 포함
- 분기 전환 시 새 분기 문서가 없으면 생성 안내

## frontmatter 표준 (티켓 산출물)

vault `wiki/guides/frontmatter-spec.md` (SoT)의 ticket 스키마를 따른다 — 티켓 노트 작성 시점에 해당 파일을 읽어 최신 스키마 사용.

ARGUMENTS: $ARGUMENTS
