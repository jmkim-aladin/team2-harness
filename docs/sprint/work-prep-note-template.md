# Work Prep 노트 템플릿

`/ad:work-prep`이 vault 티켓/제안 노트를 만들거나 갱신할 때 사용하는 상세 템플릿이다. 실행 절차와 승인 게이트의 source는 `.claude/commands/ad/work-prep.md`이고, 이 문서는 frontmatter, 본문 밀도, 구현 계획·검증 SQL 기록 형식을 담당한다. 강도와 보조 장치 명칭은 [harness-guide.md](../harness-guide.md) §작업 플로우 2. 개발이 SoT다.

## 경로

| 모드 | 경로 |
|------|------|
| 티켓 | `$LOCAL_WIKI_PATH/wiki/processes/tickets/dev2-{NNNN}.md` |
| 서비스 추정 자유글 | `$LOCAL_WIKI_PATH/wiki/services/{서비스ID}/proposals/{kebab-slug}.md` |
| 서비스 미추정 자유글 | `$LOCAL_WIKI_PATH/wiki/processes/tickets/{kebab-slug}.md` |

## 티켓 Frontmatter

```yaml
---
type: ticket
title: DEV2-{NNNN} {YouTrack 제목}
canonical_id: ticket:dev2-{nnnn}
status: draft
updated_at: {YYYY-MM-DD}
ticket_id: DEV2-{NNNN}
ticket_status: in-progress
decision_status: none
assignee: {jmkim 등 id}
service: "[[{서비스ID}]]"
related_services:
  - "[[{서비스ID}]]"
related_tickets: []
related_domains: []
related_meetings: []
related_okrs: []
relation_status: inferred
relation_sources:
  - youtrack
  - harness
sprint: {YYYY-MM}
type_yt: feature
youtrack_state: {YouTrack 상태}
youtrack_synced_at: "{YYYY-MM-DD}"
sources:
  - youtrack: {BASE}/issue/DEV2-{NNNN}
  - harness: $TEAM2_HARNESS_PATH/catalog/{서비스}.yaml
  - repo: {서비스 repo 경로}
---
```

`status`는 문서 신뢰도, `ticket_status`는 작업 흐름, `decision_status`는 Hermes board 노출 조건이다. 사용자 결정/승인/검토가 필요하면 `decision_status: decision-needed | approval-needed | review-needed | blocked` 중 하나를 명시한다.

## 자유글 Frontmatter

서비스 추정 시 `proposal` type을 사용한다.

```yaml
---
type: proposal
title: {사람용 제목}
canonical_id: proposal:{서비스ID}/{kebab-slug}
status: draft
updated_at: {YYYY-MM-DD}
service_id: "[[{서비스ID}]]"
related_services:
  - "[[{서비스ID}]]"
related_tickets: []
related_domains: []
related_meetings: []
related_okrs: []
relation_status: inferred
relation_sources:
  - manual
decision_status: none
---
```

서비스 추정 불가 시 backlog ticket으로 둔다.

```yaml
---
type: ticket
title: {사람용 제목}
canonical_id: ticket:backlog/{kebab-slug}
status: draft
updated_at: {YYYY-MM-DD}
ticket_id: TBD
ticket_status: backlog
decision_status: none
assignee: jmkim
service: unknown
related_services: []
related_tickets: []
related_domains: []
related_meetings: []
related_okrs: []
relation_status: inferred
relation_sources:
  - manual
sprint: {YYYY-MM}
type_yt: task
---
```

## 본문 템플릿

기본: 아래 항목은 필요한 내용을 고르는 틀이다. 첫 화면은 문제·판단 이유·다음 행동이 이어지는 짧은 설명으로 작성하고, 같은 사실은 한 번만 적는다. 현재 상태를 별도 구획에 적을 때는 판단 요약을 반복하는 대신 달라진 상태나 남은 확인을 적는다. 적용할 내용이 없는 구획은 생략할 수 있다. 긴 SQL·로그·이력은 상세 근거로 연결한다. 의도는 새 담당자가 이전 대화 없이 업무를 이해하게 하는 것이다. [설명 작성 기준](../../policies/wiki-document-language-and-title-policy.md#설명의-맥락과-상세-근거)을 따른다.

근거 등급(사실·추론·미확인) — 레거시 설계 의도·과거 결정을 조사할 때 `기술 근거 > 설계 의도`의 주장마다 `[사실]`·`[추론]`·`[미확인]`을 붙인다. 현재 코드는 지금의 동작만 보여 주므로, 등급이 없으면 코드에서 과거 의도를 지어낸 문장이 사실처럼 읽힌다:

- `[사실]` 작성 의도·과거 결정의 확정 근거는 당시 PR·티켓·결정 기록 등 명시적 기록에 연결한다. 현재 코드는 동작의 근거로 사용한다.
- `[추론]` 여러 정황에서 도출한 결론은 추론임을 밝히고, 근거와 결론 사이의 연결을 짧게 적는다.
- `[미확인]` 이유를 못 찾으면 조사한 기록·범위와 남은 질문을 `미확정 질문`에 남긴다. 미검색·접근 불가와 검색했으나 미발견을 구분한다.

중요 주장에만 적용한다. 검색 전문을 첫 화면에 넣거나 `relation_status`를 주장 확신도 용도로 재사용하지 않는다. 근거: 2026-10-21 3팩 비교 검토 — pstack why, [pstack 하네스 도입 검토](../pstack-harness-adoption-review.md) P2 "설계 의도 조사에서 사실·추론·미확인 분리".

````markdown
# {제목}

## 판단 요약

- 문제: {사용자/운영 관점 문제 한 문장}
- 현재 판단: {확정/유력 가설 한 문장}
- 해결 방향: {바꿀 정책/로직/운영 조치 한 문장}
- 다음 행동: {바로 실행할 첫 단계 — 구현 계획이 있으면 `/ad:implement DEV2-{NNNN}` S{n}}

## 현재 상태

- 상태: in-progress
- 결정 상태: none
- 마지막 판단: {요약}
- 다음 행동: {사용자 개입 없이 가능한 다음 단계}
- 확인 필요: {없으면 "없음"}

## 요청 요약

- 보고자/담당자: {보고자} / {담당자}
- 원 요청: {요청을 1-2줄로 압축}
- 제약/주의: {외부 티켓 원문 보존, DB 승인, 운영 영향 등}

## 비즈니스 로직

- 트리거: {언제 문제가 발생하거나 기능이 동작하는지}
- 정책/예외: {허용/제한/제외/정산/노출 등 판단 기준}
- 영향 범위: {사용자, 운영, 데이터, 정산, 노출 등}
- 결정 필요: {오너/보고자 확인이 필요한 정책 판단}

## 기술 근거

- 서비스/repo: {서비스ID} / {repo 경로}
- 진입점: {화면/API/배치/모듈 1-3개}
- 의존성: {핵심 SP/API/Table/외부 호출 1-5개}
- 설계 의도: {레거시 의도를 조사했을 때만 — [사실|추론|미확인] 주장 — 근거 링크}
- 근거 위치: {전수검사/콜그래프 결과가 있으면 링크만}

## 검증

- 목적: {확인하려는 판단}
- 방법: {grep/콜그래프/dev DB 읽기/테스트}
- 결과: {카운트, 패턴, 통과/실패 요약}
- 판단: {이 결과로 확정/기각/보류한 내용}
- 근거 위치: {SQL/Querybook/전수검사 링크. 없으면 생략}

## 구현 계획

- 강도: {가벼움|보통|무거움|위험} — {판정 단서 1줄}
- 완료 조건:
  - AC1 {대상} → {기대값} (확인: 테스트|SQL|화면)
- 검증 명령: `{서비스 repo의 실제 테스트·실행 명령}` — 출처: {카탈로그 verification|repo 스크립트|CI}
- 경계: 그냥 진행 {…} / 먼저 확인 {…} / 손대지 않음 {…}
- 슬라이스:
  - [ ] S1 {무엇} — seam: {테스트 지점} / 확인: AC1
  - [ ] S2 {무엇} — seam: {테스트 지점} / 확인: AC2
- 구현 중 신호:
  - {이 티켓 해당분만 3~5줄}

## 진행 메모

- {YYYY-MM-DD} S1 완료 — {검증 명령 결과 한 줄}
- {YYYY-MM-DD} 범위 밖: {발견 — 후속 후보}

## 검증 SQL

- 목적: {운영/개발 서버에서 확인할 판단}
- 실행 환경: {DB/서버}
- 기대 결과: {사용자가 알려주면 되는 값}

```sql
-- 조회 전용 SQL
```

## 미확정 질문

-

## 결정 패킷

- 현재 없음

## Actions

- [ ] {개발 밖 첫 단계 — 개발 단계는 `구현 계획` 슬라이스가 맡는다}
- [ ] 담당자/오너 컨펌
- [ ] 검증 결과 또는 회귀 테스트 정리
- [ ] PR / 배포 라인업

## 완료 기록

- {YYYY-MM-DD}: 위키 노트 초안 생성 (`ad:work-prep`).
````

본문은 완료 기록과 링크를 제외하고 120줄 이내를 기본 목표로 한다. 첫 50줄 안에 문제, 현재 판단, 해결 방향, 다음 행동이 보여야 한다.

## 구현 계획 기준

`/ad:work-prep` §11.5가 개발 Task(보통 이상)일 때 쓰고, `/ad:implement`가 슬라이스 하나씩 실행하며 체크한다. 검증·배포·분석·데이터 Task와 가벼움은 이 절을 생략하고 `판단 요약`에 생략 사유 한 줄을 남긴다.

- **강도** — 사유에는 판정 단서(시간 축·위험 축)를 적는다. 정의는 [harness-guide.md](../harness-guide.md) §작업 플로우 2. 개발
- **완료 조건**(acceptance criteria) — AC마다 관찰 대상 → 기대값 → 확인 방법. "빠르게"·"정상 동작"은 수치·상태값으로 바꾼다 — 판정할 수 없는 조건은 완료를 주장만 하게 만든다. 원천은 티켓(Task `### 완료 기준`·Feature 5W1H)이다 — 원천이 판정 불가하거나 비어 있으면 work-prep 출력에 **티켓 완료 기준 보완안**을 내고 YouTrack 반영은 사용자 확인 후 한다. 노트만 고치면 spec SoT가 모호한 채로 남는다
- **검증 명령**(verification command) — 카탈로그 `verification`·repo 스크립트(`build.gradle`·`package.json`·`Makefile` 등)·CI 설정에서 찾은 실제 명령을 적는다 — 가정한 명령은 첫 슬라이스에서 깨진다. 빌드·컴파일 통과는 동작의 증거가 아니므로 테스트·실행 결과를 보는 명령을 고른다. 테스트 없는 레거시는 관찰 절차(화면 경로·dev DB 조회·로그)를 적는다
- **경계**(boundaries) — 그냥 진행(이 티켓 범위의 코드·테스트) / 먼저 확인(DB·SP 변경, 공통 서비스 호출 등 이 티켓 해당분) / 손대지 않음(카탈로그 금지 영역·`LEGACY_BOUNDARY.md`)
- **슬라이스**(vertical slice) — 개발 Task 내부의 수직 분할 2~5개(보통은 1~2). 위험이 높은 것 먼저 — 전제가 틀렸으면 일찍 깨져야 되돌리기 싸다. 슬라이스마다 seam(테스트 지점)과 확인할 AC를 단다. 반나절을 넘는 슬라이스는 분할 신호다
- **구현 중 신호**(in-flight signals) — 아래에서 이 티켓 해당분만 3~5줄 고른다
  - 결제·쿠폰·지급 경로 → 멱등키 계약([eng-review 점검표](../eng-review/review-sections.md) §1)
  - 스키마 rename·drop → Expand/Contract
  - 성능 우려 → 성능 판정 규칙(같은 점검표 §4)
  - 범위 밖 문제 → `진행 메모`에 기록만 (범위 밖 기록)
  - 티켓 전제 깨짐 → 멈추고 `/ad:grill` 또는 티켓 갱신
  - 오래 걸리고 중간 조향이 필요한 위임 → `/ad:orchestration`(`HERDR_ENV=1`, 아니면 서브에이전트)
  - PR 직전 → DoD 체크리스트 + `/ad:code-review-self`
- `판단 요약 > 다음 행동`은 다음 미체크 슬라이스를 가리킨다. `Actions`에는 슬라이스를 반복하지 않고 개발 밖 항목(오너 컨펌·QA 요청·배포 라인업)만 둔다 — 같은 할 일이 두 곳에 있으면 한쪽만 체크된다
- 기존 구현 계획을 갱신할 때는 체크된 슬라이스와 `진행 메모`를 보존하고 남은 슬라이스만 고친다
- 근거: 2026-10-21 사용자 결정 — 개발 Task면 work-prep이 구현 계획을 자동 생성하고 implement가 슬라이스 하나씩 실행한다. 형식은 3팩 비교 검토 — Osmani planning·spec(완료 조건·경계 3단·위험 먼저), pstack create-verification(실제 실행 검증 명령)

## 검증 SQL 기준

vault에 들어온 운영 데이터는 통제를 벗어난다 — 조회 결과는 판단만 남기고 원자료는 남기지 않는다.

1. dev/staging 조회와 dev `INSERT/UPDATE/DELETE`는 [로컬 자격증명 정책](../../policies/local-credentials-policy.md)의 사전 동의 범위를 따른다. 개발 DML은 작업당 기본 100행 이하·대상 조건·사전/사후 확인·복구 방법을 확보한다. staging 변경·DDL/SP·범위 밖 변경은 별도 승인 경로로 진행한다 — 검증 데이터 작업과 환경에 영향을 주는 변경을 구분한다.
2. dev/staging 검증은 작은 모수(`TOP 10`~`100`, 특정 1~3개 그룹, 1일~7일, 빈 임시 테이블 등)로 시작한다.
3. 운영 식별자(계정, CID, OID 등)는 SQL 파라미터로 명시할 수 있으나 row dump는 저장하지 않는다.
4. 검증된 SQL은 data-requests-dev2 등록 전에 먼저 티켓 노트 `검증 SQL` 섹션에 저장한다.
5. 결과 기록은 스키마, 카운트, 대표 패턴, 판단만 남긴다. 운영 실데이터, 개인정보, 결제 row, SP 원문, 시크릿은 저장하지 않는다.
6. SQL은 길어도 티켓 노트 본문 마크다운 코드블록에 embed한다. 별도 `.sql` 사이드카 파일(`wiki/processes/tickets/dev2-{NNNN}/*.sql`)은 만들지 않는다 — Obsidian에서 안 열리고 링크가 끊긴다 (2026-07-08 사용자 지시). 이 경우 본문 120줄 목표에서 `검증 SQL` 코드블록은 제외한다. 최종 산출 SQL의 SSOT는 여전히 data-requests-dev2다.

개발 조회·DML의 사전 동의 범위는 [local-credentials-policy.md](../../policies/local-credentials-policy.md)를 따른다. 운영(prod) 조회는 [운영 DB 접근 정책](../../policies/production-db-access-policy.md)의 개통·작업 승인 경로로 진행하고, 데이터 추출은 [data-request-policy.md](../../policies/data-request-policy.md)도 함께 따른다.
