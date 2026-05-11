# 레거시 현대화와 DB 분리 분석 기준

## 목적

이 문서는 Ralph Loop와 운영 지식 위키 산출물을 단순 운영 문서가 아니라 레거시 현대화와 DB 분리 의사결정에 사용할 수 있는 증거 세트로 만들기 위한 기준이다.

운영 대응에 충분한 문서라도 DB 소유권, read/write 경계, 추출 순서, 정합성 검증 기준이 없으면 현대화 계획의 근거로 쓰지 않는다.

## 적용 범위

- 레거시 서비스 전체 분석
- SP 중심 서비스의 Wrap/Extract 후보 판단
- shared DB에서 서비스별 DB 또는 bounded context별 schema로 분리하는 사전 분석
- 신규 서비스가 레거시 DB/SP에 직접 붙지 않도록 adapter 경계를 정하는 작업
- 운영 지식 위키의 domain, contract, querybook, execution record 평가
- IDC DB 운영 안정화와 AWS 전환을 위한 CDC 1차 진단

## 저장 위치

| 산출물 | 저장 위치 |
|---|---|
| 판단 기준, 정책, 템플릿 | 팀 하네스 `docs/`, `policies/`, `templates/` |
| 서비스별 분석 결과 | 로컬 Obsidian 운영 지식 위키 |
| SP/API/Table contract | 로컬 Obsidian 운영 지식 위키 |
| 실행 기록과 평가 결과 | 로컬 Obsidian 운영 지식 위키 `wiki/execution/` |
| 분석 중 필요한 외부 DB script mirror | 대상 db-script repo의 cross-db 영역. 예: `databases/_cross-db/{external-source}/db_script/` |
| YouTrack KB/Issue 반영 | 사용자 승인 후에만 수행 |

## 문서 언어와 제목

레거시 현대화와 DB 분리 분석 산출물은 [wiki-document-language-and-title-policy.md](../policies/wiki-document-language-and-title-policy.md)를 따른다.

- 파일명은 `service_id` 접두어와 `kebab-case.md`를 유지한다.
- H1 제목과 `title` frontmatter는 한글 서비스 표시명으로 시작한다.
- 폴더 구조만으로 서비스가 구분된다고 가정하지 않는다. Obsidian 검색 결과, Graph view, Related Links, PDF/외부 공유 화면에서는 제목만 보일 수 있다.
- 영어 기술 용어는 필요한 경우 제목에 포함할 수 있지만, 제목 전체가 영어만으로 구성되면 안 된다.

## 외부 DB Script Mirror

레거시 서비스 분석 중 해당 서비스 DB script에는 없지만 cross DB 호출로 연결되는 외부 SP가 발견되면, 원본 repo를 직접 수정하지 않고 대상 db-script repo의 cross-db 영역에 분석용 mirror를 둔다.

원칙:

- 원본 DB 폴더 구조를 유지한다. 예: `databases/_cross-db/aladin-infra/db_script/webcatalog/StoredProcedures/{sp}.sql`.
- 필요한 SP부터 선별 복사한다. 전체 DB script를 무조건 복사하지 않는다.
- mirror 문서에는 원본 path, mirror path, caller, hash, review state를 남긴다.
- mirror는 분석 reference이며 운영 변경 근거가 아니다.
- 원본 최신화와 재복사 주기는 별도 action으로 남긴다.

## DB Migration / CDC Assessment

현대화/DB 분리 분석이 DB 이관과 연결되는 경우 [db-migration-cdc-assessment-guide.md](./db-migration-cdc-assessment-guide.md)를 함께 적용한다.

도메인, SP, table, batch 문서는 필요 시 아래 정보를 추가로 추출한다.

- 전체 UPDATE 여부
- rename/swap 여부
- TRUNCATE/DROP/CREATE 여부
- SELECT INTO 여부
- 파생/집계/랭킹/전시/추천/임시 table 여부
- lock wait, blocking, 장애 연관 가능성
- CDC 등급 A~F
- 권장 조치: CDC 후보 유지, CDC 제외, chunk update, version pointer, AWS 재생성, full refresh, 추가 분석

## Readiness Level

각 도메인 문서는 아래 단계 중 하나로 분류한다.

| Level | 이름 | 의미 | 다음 단계 |
|---:|---|---|---|
| L0 | Inventory | source, SP, table 목록만 있음 | graph/caller/read-write 연결 |
| L1 | Operational | 장애 대응과 증상별 확인 순서가 있음 | contract와 owner 보강 |
| L2 | Contract | API/SP/Table 계약과 read/write가 확인됨 | 데이터 소유권 결정 |
| L3 | Ownership | 원장 table, writer, reader, shared owner가 구분됨 | 추출 후보와 경계 설계 |
| L4 | Extraction Plan | Wrap/Extract 순서, adapter, rollback, reconciliation이 있음 | 사람 승인 후 티켓화 |
| L5 | Migration-Ready | migration test, dual-run/shadow-read, cutover/rollback 기준이 있음 | 구현 착수 가능 |

`L1`은 운영 문서로 쓸 수 있지만 현대화 계획의 근거로는 부족하다. 현대화/DB 분리 티켓의 시작 기준은 최소 `L3`, 구현 착수 기준은 최소 `L4`다.

## 필수 섹션

현대화 또는 DB 분리 판단에 쓰는 도메인 문서는 아래 섹션을 포함해야 한다.

- `Modernization Readiness`: Observe/Wrap/Extract/Freeze 후보와 이유
- `DB Separation Readiness`: DB 분리 단계, blockers, shared DB coupling
- `Data Ownership`: 원장 table, write owner, read consumers, shared owner
- `Contract Surface`: API, batch, SP, table read/write, 외부 연동
- `Extraction Candidates`: 먼저 감쌀 것, 나중에 뺄 것, 절대 바로 옮기면 안 되는 것
- `Migration Verification`: reconciliation query, shadow-read, backfill, rollback 기준
- `Failure Modes`: stale data, double write, partial failure, batch lag, amount mismatch
- `Approval Required`: DB/SP 변경, 프로덕션 배포, 레거시 경계 변경, YouTrack write

## Controller/API Boundary Guardrails

Controller나 API 산출물은 겉으로 보이는 action 이름만으로 DB 영향 여부를 단정하지 않는다. 아래 유형은 반드시 별도 경계로 분리해 기록한다.

| 유형 | 필수 분리 기준 |
|---|---|
| React-backed MVC page shell | controller action이 view만 반환해도 downstream React API, owner-check SP, export/download side effect를 분리한다. |
| Payment bridge page shell | external payment URL, auth/return-url, payment/card identifier masking, delete/check retry, legacy response-code mapping을 분리한다. |
| Test/sample upload page | view만 반환해도 upload API, FTP/object storage side effect, CDN script, runtime exposure/auth/retire 결정을 분리한다. |
| Sample CRUD/test controller | sample/demo table, hard-coded customer, unauthenticated CRUD, WebCatalog PII join, anti-forgery/retire decision, source-level parameter drift를 분리한다. |
| App bridge/test route | DB 호출이 없어도 app deep link, native bridge command, device cookie mutation, external URL fallback, auth/exposure/retire 결정을 분리한다. |
| UX display/admin controller | public display read, admin CRUD, soft delete, active window/timezone, image/link URL policy, operator audit, source-gap SP/table을 분리한다. |
| Creator certification admin controller | event-scoped applicant review, quarter/unapproved decision, applicant PII/profile/note evidence, Excel export, dynamic SQL filter, operator audit, bulk AJAX partial-success를 분리한다. |
| External search/API proxy | provider key/SLA/timeout, request/response schema, query privacy, downstream product DB fallback을 분리한다. |
| Customer FAQ/help API | WebCatalog FAQ owner, category/content read, BEST rank, search engine/API toggle, Diquest fallback, search log/custkey, HTML answer rendering을 분리한다. |
| Search API | external search engine toggle, query logging/redaction, rank/score drift, stop-word policy, recent-keyword UID/Prokey merge write, N+1 hydrate를 분리한다. |
| MyPage/account/order API | point ledger, order/payment/refund/bank/receipt, marketing consent, IAP, runtime app setting, membership history privacy를 분리한다. |
| Account security API | login-required account profile, TOBE service start, sleep extension, password validation/change, session refresh, mail queue, cross-DB customer state를 분리한다. |
| Login/SNS/OAuth API | external provider, session mutation, captcha/fail-count, safe return URL, WebCatalog account SP, PII/log retention을 분리한다. |
| Logout/session boundary | login session invalidation, auth/adult cookie reset, partner token/cookie delete, saved-password cookie clearing, safe return URL, external AppBlock DB side effect를 분리한다. |
| Account join/registration API | account create, temporary agreement, under-14 guardian auth, SNS setup, TOBE service start, consent/mail/push side effects, rollback/reconciliation 기준을 분리한다. |
| Public note engagement API | note detail access rule, read/view-count/statistics side effect, like/scrap/sticker ledger, paywall/membership grant, profile hydrate N+1, buyer/supporter privacy를 분리한다. |
| Public tobelog read API | public profile/about/subscription, note/series/membership list paging, filter-age/adult masking, item-view hydrate N+1, membership access hints를 분리한다. |
| Notification center API | notification list/read model, badge count, read queue compensation, hide/delete command, profile/content hydrate, safe redirect URL을 분리한다. |
| Intra settlement admin controller | admin auth, Excel export/download audit, dynamic SQL/report filter, bulk command partial-success, operator audit, cross-DB customer/ticket reads, settlement exclusion history를 분리한다. |
| Studio settlement/refund API | creator settlement read, tax report read model, refund account command, bank/account masking, file upload, fraud check, cross-DB refund ledger를 분리한다. |
| Error/logging controller | request/referrer URL, user/server IP, UID/Custkey/Prokey, stack/html error, external webhook, log retention/PII scrub 경계를 분리한다. |
| Operations diagnostics controller | process/request telemetry, IP/user-agent/request URL PII, intranet/operator auth, refresh interval, temp/codegen file inspection, HTML/JS escaping을 분리한다. |
| Studio content/series API | owner/access rule, adult auth, note visibility/adult propagation, tag linkage fan-out, trigger/change queue, item-view hydrate N+1, bulk partial-success 정책을 분리한다. |
| Studio profile/tobelog API | profile/tobelog ledger, social link, favorite category replace, search-index queue, destructive delete workflow, trigger/change queue를 분리한다. |
| Studio dashboard/read model API | dashboard summary, stale read-model freshness, statistics batch dependency, WebCatalog balance read, dynamic chart query, profile masking을 분리한다. |
| Membership/subscription API | owner/access rule, join password/hint masking, subscriber privacy, item/profile hydrate N+1, bulk partial-success 정책을 분리한다. |
| Bulk command API | 여러 ID나 sort move를 loop 처리하면 per-item result, retry, idempotency, reconciliation 기준 없이는 Extract 후보로 승격하지 않는다. |

이 유형들은 owner 승인 전에는 `Extract` 또는 `Migration-Ready`로 승격하지 않고 `needs-review` 상태를 유지한다.

## 평가 Rubric

각 항목은 0~3점으로 평가한다. 2점 미만 항목이 있으면 현대화/DB 분리 계획의 근거로 쓰지 않고 `needs-review`에 둔다.

| 기준 | 0점 | 1점 | 2점 | 3점 |
|---|---|---|---|---|
| Operational Readiness | 운영 루틴 없음 | 점검 항목만 있음 | 증상별 확인 순서 있음 | Querybook, 판단 분기, 다음 액션까지 있음 |
| Contract Completeness | 호출/계약 없음 | API 또는 SP 일부만 있음 | API/SP/Table 중 2계층 이상 연결 | Controller→Service→Repository→SP→Table read/write 확인 |
| Data Ownership | 원장 불명 | 핵심 table만 나열 | write owner와 주요 reader 구분 | 원장, writer, reader, shared owner, conflict rule 명시 |
| DB Separation Readiness | 분리 불가/불명 | shared DB 결합만 언급 | read/write split 후보 있음 | owner/backfill/reconciliation/rollback 기준 있음 |
| Modernization Path | 트랙 없음 | Observe/Wrap/Extract 추정 | 트랙과 이유 있음 | 단계별 티켓화 가능한 실행 순서 있음 |
| LLM Safety | 추론 구분 없음 | 주의사항 일부 | Confirmed/Inferred/Needs Review 구분 | source hash, confidence, 금지 추론, unresolved queue 연결 |

## Plan-Eng-Review 적용 기준

현대화/DB 분리 문서를 평가할 때는 다음 순서로 본다.

1. Scope Challenge: 전체 분석 완료로 단정하지 않는다. inventory, P0 seed, migration-ready를 구분한다.
2. Architecture Review: bounded context, adapter 경계, DB owner, shared dependency를 확인한다.
3. Code/Knowledge Quality Review: 문서가 contract 단위로 재사용 가능한지 확인한다.
4. Test/Verification Review: lint뿐 아니라 reconciliation, shadow-read, rollback 검증 기준이 있는지 확인한다.
5. Performance/Data Review: high-write SP, batch lag, hot table, lock/NOLOCK 위험을 확인한다.
6. Parallelization: contract 분석, ownership matrix, querybook/reconciliation을 분리 가능한 lane으로 나눈다.

## 완료 기준

도메인을 현대화/DB 분리 계획의 근거로 쓰려면 다음을 만족해야 한다.

- Readiness Level `L3` 이상
- Operational Readiness, Contract Completeness, Data Ownership, DB Separation Readiness가 모두 2점 이상
- 핵심 SP별 contract 문서가 있다
- 원장 table과 write owner가 명시되어 있다
- read path 분리 후보와 write path 보류 영역이 구분되어 있다
- reconciliation query 또는 검증 절차가 있다
- `python3 scripts/lint_wiki.py`가 error 0이다
- 사람 검토 전에는 `review_state: needs-review`를 유지한다

## Unresolved Evidence Gate

전체 분석 goal을 완료로 판단하기 전에 unresolved queue와 coverage registry가 서로 맞는지 검증한다.

원칙:

- `missing-sp-source`는 source가 없더라도 caller/boundary/evidence request pack이 있어야 하며, source 확보 전에는 canonical contract로 승격하지 않는다.
- `batch-schedule-unknown`은 SQL Agent job/step/schedule/run history 또는 owner-confirmed no-run evidence 없이는 완료로 보지 않는다.
- `dirty-source`는 owner decision, clean baseline, accepted dirty caveat 중 하나가 있어야 상태 전환할 수 있다.
- evidence template은 header, enum, redaction 기준을 통과해야 한다.
- coverage registry는 현재 unresolved queue와 1:1로 맞아야 하며 stale/missing 항목이 있으면 goal 완료로 표시하지 않는다.

로컬 Obsidian 위키에서는 아래 검증을 `run_all.py`에 포함한다.

```bash
python3 scripts/validate_unresolved_evidence_imports.py
python3 scripts/validate_unresolved_coverage.py
```

## 금지 표현

| 금지 표현 | 이유 | 대체 표현 |
|---|---|---|
| "전체 분석 완료" | inventory와 migration-ready를 혼동함 | "inventory 완료", "P0 seed 완료", "L3 ownership 분석 완료" |
| "DB 분리 가능" | owner/rollback 없이 위험함 | "read path 분리 후보", "write path는 owner 검토 필요" |
| "SP 대체 가능" | 계약/부작용 누락 가능 | "adapter로 감싼 뒤 shadow-read 검증 필요" |
| "canonical" | 사람 검토 전 과신 | "canonical 후보", "analyzed", "needs-review" |
