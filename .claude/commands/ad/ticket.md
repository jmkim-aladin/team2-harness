# YouTrack 티켓 생성

사용자 요청을 기반으로 5W1H 형식의 YouTrack 티켓을 생성합니다.

> 문서 위치 결정: harness `policies/knowledge-base-policy.md` (repo↔vault 경계) + vault `wiki/guides/document-placement.md` (vault 내부 트리).

## 검증 순서

[policies/hypothesis-verification-order.md](../../../policies/hypothesis-verification-order.md) 적용 — 티켓 본문에 미확정 사실을 적기 전에 콜그래프/grep + dev DB 읽기 쿼리로 답이 나오는지 먼저 확인. 잔여 항목만 보고자/오너 컨펌 대상으로 남긴다.

## 기본값

- **프로젝트**: DEV2
- **담당자**: 대상 서비스의 owner를 `policies/team-members.md`에서 참조 (없으면 사용자에게 질문)
- **유형**: Task
- **Phase**: Backlog (ToBe)
- **우선순위**: 보통 (Normal)

## 참조 문서 (Source of Truth)

티켓 작성 시 아래 하네스 문서를 **반드시 읽어서** 규칙을 준수합니다.

| 문서 | 경로 | 참조 항목 |
|------|------|-----------|
| **티켓 작성 가이드** | `docs/sprint/ticket-guide.md` | 5W1H 상세 작성법, 스프린트 상태, 티켓 크기 |
| **스토리 포인트 가이드** | `docs/sprint/story-point-guide.md` | SP 산정 기준 (1/2/3/5/8/13) |
| **스프린트 계획 운영** | `docs/sprint/sprint-planning-overview.md` | 운영/계획 업무 분류 |
| **업무 계획 변경 절차** | `docs/sprint/plan-change-process.md` | 긴급 요청·이월 처리 |
| **전사 상태 플로우** | `youtrack/ticket-guide.md` | YouTrack 상태 머신 (ToBe→Closed) |

### 핵심 규칙 요약

- **Feature 총 기간 ≤ 1주 (필수)** — 초과 시 반드시 분할. 시작일~종료일이 7일을 넘으면 생성 차단
- **Task ≤ 1일 (필수)** — 초과 시 분할
- **13점(XXL)은 스프린트 투입 금지** → 8점 이하로 분할 필수
- **예상 시작 일자 필수**
- **전월 마지막 주에 계획 완료**

## 환경변수

| 변수 | 용도 |
|------|------|
| `$YOUTRACK_TOKEN` | YouTrack API 인증 토큰 |
| `$YOUTRACK_BASE_URL` | YouTrack 베이스 URL (기본: `https://aladincommunication.youtrack.cloud`) |

### 토큰 owner 규칙 (필수)

- `$YOUTRACK_TOKEN`은 **티켓을 발행하는 본인 계정의 토큰**이어야 한다.
- YouTrack은 issue 생성 시 reporter(작성자) 필드를 자동으로 토큰 owner로 박는다. 일반 사용자 권한으로는 reporter 필드를 다른 사람으로 변경할 수 없다.
- 다른 사람의 토큰(예: 팀장 토큰)을 그대로 쓰면 모든 티켓이 그 사람 명의로 등록되어 작성자 추적이 어그러진다.
- 검증 방법: `curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" "$YOUTRACK_BASE_URL/api/users/me?fields=login,fullName,email"` 로 본인 계정인지 확인.
- 토큰이 본인 것이 아니면 본인 YouTrack 토큰을 발급받아 `.envrc` 또는 셸 rc 파일에 교체한 뒤 진행한다.

## 참조 정보

### YouTrack API 호출 (curl)

티켓 생성·담당자 변경·KB 조회는 모두 YouTrack REST API를 사용한다. MCP 도구를 호출하지 않는다.

```bash
BASE="${YOUTRACK_BASE_URL:-https://aladincommunication.youtrack.cloud}"
AUTH="Authorization: Bearer $YOUTRACK_TOKEN"

# 1. DEV2 프로젝트 internal id 조회 (create_issue 입력값)
curl -s -H "$AUTH" \
  "$BASE/api/admin/projects?fields=id,shortName&query=DEV2"

# 2. 관련 KB 검색 (티켓 컨텍스트 보강)
curl -s -H "$AUTH" \
  "$BASE/api/articles?\$top=10&fields=id,idReadable,summary,content,parentArticle(summary)&query=project:DEV2"

# 3. 티켓 생성
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{
        "project": {"id": "<DEV2 internal id>"},
        "summary": "[{서비스}] {작업 요약}",
        "description": "{5W1H 본문}"
      }' \
  "$BASE/api/issues?fields=idReadable,summary"

# 4. 담당자 설정 (Assignee 커스텀 필드 갱신)
curl -s -X POST -H "$AUTH" -H "Content-Type: application/json" \
  -d '{
        "customFields": [{
          "name": "Assignee",
          "$type": "SingleUserIssueCustomField",
          "value": {"login": "<YouTrack login>"}
        }]
      }' \
  "$BASE/api/issues/{idReadable}?fields=idReadable,customFields(name,value(login))"
```

**DEV2 KB 구조:**
- `DEV2-A-1` (Team): 팀 운영 (온보딩, 서버접속, 보안, 장애대응, OKR, 스프린트)
- `DEV2-A-21` (Shared): 공유 문서 (만권당, 투비 등 서비스별)
- `DEV2-A-22` (Onboarding): 온보딩
- `DEV2-A-108`: 😺만권당

### 서비스 카탈로그 참조
- 위치: `catalog/` (max, tobe, naru, bazaar, aasm)

### 팀원 정보
- 위치: `policies/team-members.md`
- 서비스별 owner/backup 정보로 담당자 자동 제안

## 실행 지침

사용자가 `/ad:ticket` 또는 `/ad:ticket [설명]`을 입력하면:

0. **토큰 owner 검증 (필수)**: `curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" "$YOUTRACK_BASE_URL/api/users/me?fields=login,fullName,email"` 로 토큰 owner를 확인한다. 토큰 owner가 사용자 본인 계정(`$USER` 또는 git config user.email)과 일치하지 않으면 reporter가 토큰 owner로 박혀 변경할 수 없으므로 **티켓 생성을 중단**하고 사용자에게 본인 토큰 교체를 요청한다.
1. **`docs/sprint/ticket-guide.md`를 읽어** 5W1H 작성법과 최신 규칙을 확인
2. 사용자 입력이 있으면 해당 내용을 기반으로 티켓 작성
3. 사용자 입력이 없으면 어떤 티켓을 만들지 질문
4. **대상 서비스가 명확하면** 서비스 카탈로그(`catalog/*.yaml`)를 읽어 컨텍스트 보강
5. **관련 KB 문서가 있을 수 있으면** YouTrack KB API로 검색하여 참조 (선택적)
6. **담당자 설정 (필수)**: `policies/team-members.md`에서 대상 서비스의 owner를 조회하고, 티켓 생성 후 **반드시** YouTrack REST API(`POST /api/issues/{idReadable}`)로 `Assignee` 커스텀 필드를 갱신한다. owner를 확인할 수 없으면 `jmkim` (김정민)을 기본 담당자로 설정한다. 담당자 미설정 티켓은 허용하지 않는다.
7. **SP 산정**: `docs/sprint/story-point-guide.md` 기준표에 따라 산정 제안
   - **Feature 유형은 SP `0` 고정** (하위 Task SP 합으로 Velocity 자연 집계, 중복 카운트 방지). Feature 생성 시 Story points 필드를 명시적으로 `0`으로 설정한다
   - Task만 1/2/3/5/8/13 중에서 산정
8. **Feature 기간 검증 (필수)**: 유형이 Feature일 때 아래 검증 수행
   - 예상 시작일 ~ 종료일(또는 하위 Task 완료 예상일)이 **7일 초과 시 생성 차단**
   - 사용자에게 분할 방안을 제안하고, 분할 후 재작성
   - 분할 기준: 도메인별 / 단계별(설계→구현→테스트) / 의존성 기준

## 티켓 출력 형식

```
## 티켓 정보
- **제목**: [{서비스}] {작업 요약}
- **담당자**: {서비스 owner} ({이름})
- **유형**: Task
- **Phase**: Backlog (ToBe)
- **우선순위**: 보통 (Normal)
- **스토리 포인트**: {Task: 1|2|3|5|8|13 / Feature: 0 고정} (산정 근거: 복잡도/불확실성/작업량 — Feature는 하위 Task 합산이라 0)
- **예상 시작 일자**: {YYYY-MM-DD}
- **OKR 연계**: {팀 KR 번호} (해당 시, vault wiki/processes/okr/ 참조)

---

(5W1H 본문은 docs/sprint/ticket-guide.md 3항의 형식을 따름)

* ### What (무엇을 할 것인가)
* ### Why (왜 필요한가)
* ### Who (누가 사용할 것인가)
* ### When (언제 수행/발생하는가)
* ### Where (어디에 적용되는가)
* ### How (어떻게 구현할 것인가)
```

## 외부(사업부) 티켓 처리 규칙 (필수)

본인이 직접 생성하지 않은 티켓 — 특히 사업부(기획자·운영팀·CS) 생성 티켓 — 은 **원본을 변경하지 않는다**.

### 식별 기준
- `reporter` 필드가 본인(현재 사용자) 외 다른 사람
- 사업부/기획자/운영팀이 작성한 요청 티켓 (예: `[만권당]` 요청 사항 형식, 본문에 "기능 추가 요청드립니다" 등)
- 본인이 작성한 티켓이라도 다른 팀에 공유된 경우는 외부 취급

### 금지 행위
- Type 변경 (Task → Feature 등)
- Assignee·CC·Service·Platform·Story points 등 필드 변경
- description / summary 수정
- State 임의 전환 (운영 정책상 허용된 전환만 가능)

### 표준 처리 절차
1. 외부 티켓 원본은 **그대로 둔다**
2. 본인이 작업할 단위로 **신규 Feature를 생성**한다
   - 제목 끝에 `(개발)` 같은 구분자 추가 권장
   - 본문 첫 줄에 "## 상위 요청 — 사업부 요청 티켓 {외부 ID} 하위 개발 Feature" 명시
3. 신규 Feature를 외부 티켓의 **Subtask로 링크** (외부 티켓 parent for, 신규 Feature subtask of)
4. 하위 Task 9개는 모두 **신규 Feature 하위**로 생성·링크 (외부 티켓 직접 자식으로 두지 않음)

### YouTrack 링크 API
- linkType id `161-3` (Subtask), suffix `s` = sourceToTarget(parent for)
- 추가: `POST /api/issues/{외부ID}/links/161-3s/issues` body `{"idReadable":"{신규ID}"}`
- 제거 시 child의 **internal id**(`3-XXXXX`) 필요: `DELETE /api/issues/{parent}/links/161-3s/issues/{internal_id}`

### 사례 기록
DEV2-5512 (reporter=박상윤, 사업부): 원본 유지 → 하위에 DEV2-6607 (개발 Feature) 생성 → DEV2-6607 하위 9개 Task

## 본문 작성 규칙 (필수)

DEV2-5512 작업에서 사용자가 확정한 규칙. 모든 신규 티켓에 동일 적용한다.

### 제목
- Feature·Task 동일하게 `[{서비스명}] {업무 요약}` 형식 통일
- 서비스명은 한글 (`[만권당]`, `[투비]`, `[바자르]`)
- 날짜·버전·일정 표기 금지

### 본문
- **비즈니스 로직·정책·트리거·운영 영향 위주**로 작성
- **코드 레벨 디테일 최소화**: 컬럼명·SP명·파일경로·테이블명 나열 금지. 필요 시 도메인 단위(`공급사 계약 도메인`, `정산 처리 로직`)로 표현
- **코드블록 자제**: 본문에 ` ``` ` 사용 금지. 항목은 bullet/표로 표현
- **날짜·기간 본문에 적지 않음**: 시작일/배포일/스프린트 월 표기 금지. YouTrack 필드(`예상 시작일`, `Sprints`)에서만 관리
- **월별 스프린트 배정 표 본문 금지**: 배정은 Sprints 필드로만 관리
- **5W1H 모든 섹션 단순 bullet 1-5개**로 유지. 산문/장문 금지

### SP 분할 선호 규칙
- 사용자 선호: **SP 3 (1 MD) 최대**로 1-2 레벨까지 분할
- SP 5/8 등장 시 → 자동으로 SP 3 단위로 추가 분할 제안
- 한 Feature 하위 Task는 모두 SP 3 균일이 이상적

### 필드 기본값
- **CC**: 비움 (사용자가 명시할 때만 추가)
- **Service**: 대상 서비스 enum 반드시 설정
- **Sprints**: 사용자 명시 시에만 설정 (기본 Backlog)
- **Story points**: Feature=0, Task=3 우선

### Feature 1주 룰 예외
- 단독 진행 + 9 MD 등 1주 초과 명시 결정 시 사용자 결정 존중. 경고만 출력하고 진행

## 후속 작업 안내

티켓 초안 작성 후 사용자에게 안내:
1. 내용 검토 및 수정 요청 여부 확인
2. 확인되면 YouTrack REST API(`POST /api/issues`)로 직접 생성. MCP 도구는 사용하지 않는다.
3. **생성 직후 반드시** `POST /api/issues/{idReadable}`로 `Assignee` 커스텀 필드를 갱신해 담당자 설정 (서비스 owner 기준)
4. KB 참조 문서가 있으면 티켓 설명에 링크 포함

## frontmatter 표준 (티켓 산출물)

```yaml
---
type: ticket
ticket_id: DEV2-XXXX
ticket_status: auto-prep | in-progress | done | backlog
assignee: jmkim
service: "[[max]]"      # 서비스 노트 wikilink (graph 엣지)
sprint: 2026-05
type_yt: feature | task | bug
---
```

상세: vault `wiki/guides/frontmatter-spec.md`.

ARGUMENTS: $ARGUMENTS
