# Ralph Loop 도메인 지식 고도화 요청 가이드

## 목적

도메인 지식 고도화 작업을 단순 분석 리포트가 아니라 운영 지식 위키에 재사용 가능한 canonical 후보로 만들기 위한 요청 기준이다.

이 산출물은 운영 대응뿐 아니라 레거시 현대화와 DB 분리 판단의 입력으로도 사용한다. 따라서 운영 루틴만 충분한 문서는 완성으로 보지 않고, DB 소유권, read/write 경계, 추출 순서, 정합성 검증 기준까지 확인해야 한다. 세부 기준은 [legacy-modernization-db-separation-analysis-guide.md](./legacy-modernization-db-separation-analysis-guide.md)를 따른다.

## 저장 위치 원칙

| 산출물 종류 | 저장 위치 |
|---|---|
| 팀 공통 정책 | `team2/policies/` |
| 팀 공통 가이드 | `team2/docs/` |
| 팀 공통 스킬/명령 | `team2/.claude/commands/`, Codex skill |
| 서비스 카탈로그 | `team2/catalog/` |
| 분석 결과, 도메인 지식, Querybook, 실행 기록 | 로컬 Obsidian 운영 지식 위키 |
| graph/generated snapshot | 로컬 Obsidian 운영 지식 위키 |

로컬 Obsidian vault:

```text
/Users/user/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2
```

## 문서 언어와 제목

Ralph Loop 산출물은 [wiki-document-language-and-title-policy.md](../policies/wiki-document-language-and-title-policy.md)를 따른다.

- 파일명은 vault `wiki/domains/tobe-{domain}.md`, vault `wiki/inventory/web-aladin-{topic}.md`처럼 `service_id` 접두어와 `kebab-case.md`를 유지한다.
- H1 제목과 `title` frontmatter는 `투비 ...`, `알라딘 웹 ...`처럼 한글 서비스 표시명으로 시작한다.
- `Tobe SP Inventory`, `Web-Aladin Raw SQL Write Boundary`처럼 영어만 있는 제목은 새 산출물에 사용하지 않는다.
- 공통 Queue/Register/Index도 `운영 위키 발견 큐`, `운영 위키 조치 등록부`처럼 한국어 범위 접두어를 둔다.

## 기본 요청 템플릿

```text
Ralph Loop를 사용해서 {서비스}의 {도메인명} 도메인 지식을 고도화해줘.

목표:
- 단순 설명 문서가 아니라 로컬 Obsidian 운영 지식 위키의 canonical 후보로 만들기
- LLM이 다음 티켓/장애 대응 때 바로 검색해서 쓸 수 있게 만들기

범위:
- 서비스: {service_id}
- 읽기 source: 서비스 app repo, DB script repo, 기존 Obsidian wiki, 기존 claudedocs
- pass: source-inventory-pass, api-pass, sp-pass, table-pass, domain-pass, completeness-pass, wiki-sync-pass
- 외부 write: 금지. YouTrack KB/티켓/상태 변경은 내 승인 전 금지

품질 기준:
- Controller → Service → Repository → SP → Table 경로가 확인된 항목만 Confirmed에 둔다
- 근거 기반 추론은 Inferred에 둔다
- source 불명/동적 SQL/dirty source/확신 낮은 판단은 Needs Review 또는 Discovery Queue에 남긴다
- 운영 대응과 현대화/DB 분리 판단을 구분해서 평가한다
- 핵심 table의 write owner, read consumer, shared DB coupling을 기록한다
- read path 분리 후보와 write path 보류 영역을 구분한다
- migration verification, reconciliation, rollback 기준이 없으면 migration-ready로 부르지 않는다
- DB 이관/CDC 진단이 필요한 경우 전체 UPDATE, rename/swap, TRUNCATE/DROP/CREATE, SELECT INTO, 파생/집계/랭킹 table, Lock 이력 후보, CDC 등급 A~F, 권장 조치를 함께 추출한다
- 원문 SQL/C#은 복사하지 말고 source path, hash, 요약만 남긴다
- 장애 Querybook과 운영 판단 기준까지 포함한다

산출물:
- 로컬 Obsidian wiki/domains/{service}-{domain}.md
- 필요 시 로컬 Obsidian wiki/guides/{service}-{domain}-querybook.md
- 필요 시 로컬 Obsidian wiki/execution/{date}-{service}-modernization-db-separation-review.md
- graph/generated 또는 discovery/action queue 갱신
- 마지막에 lint 결과와 남은 미해결 큐 보고
```

## 투비 전체 도메인 지식 고도화 요청 템플릿

```text
Ralph Loop로 투비 전체 도메인 지식을 System Discovery Loop 기준으로 고도화해줘.

단계:
1. 기존 inventory와 contract graph를 최신화한다.
2. API/SP/Table/Batch를 도메인 후보로 군집화한다.
3. 도메인별로 P0/P1 우선순위를 정한다.
4. P0 도메인부터 canonical 후보 문서를 만든다.
5. 각 도메인 문서는 Summary, Confirmed, Inferred, Business Rules, State Machine, Source Anchors, Incident Routine, Query Templates, Modernization Readiness, DB Separation Readiness, Data Ownership, Migration Verification, Needs Review, Actions를 포함한다.
6. orphan SP, missing source, low-confidence domain, dirty source는 discovery queue로 남긴다.
7. 로컬 Obsidian 운영 지식 위키만 수정한다.

완료 기준:
- P0 도메인 각각에 도메인 문서가 있다.
- 각 문서는 최소 5개 이상 source anchor를 가진다.
- Controller → Repository → SP 또는 SP → Table 중 하나 이상의 경로가 graph와 문서에 연결된다.
- 장애 대응 Querybook이 도메인별로 최소 3개 증상 이상을 포함한다.
- `python3 scripts/lint_wiki.py`가 통과한다.
```

## 단일 도메인 요청 템플릿

```text
Ralph Loop로 투비 {도메인명}을 deep analysis 해줘.

분석 질문:
- 이 도메인의 핵심 원장은 무엇인가?
- 어떤 API/SP/Table/Batch가 상태를 바꾸는가?
- 사용자가 보는 화면 값과 원장 값은 어디서 갈라지는가?
- 장애가 났을 때 어느 순서로 확인해야 하는가?
- LLM이 절대 단정하면 안 되는 추론은 무엇인가?
- DB 분리를 위해 먼저 감쌀 read path와 나중에 분리할 write path는 무엇인가?
- 핵심 table의 write owner와 read consumer는 누구인가?
- 추출 전 반드시 필요한 reconciliation 기준은 무엇인가?

pass:
- api-pass
- sp-pass
- table-pass
- domain-pass
- completeness-pass
- wiki-sync-pass

산출:
- 로컬 Obsidian `wiki/domains/tobe-{domain}.md`
- 필요한 경우 `wiki/guides/tobe-{domain}-querybook.md`
- Needs Review와 Action Register 갱신
```

## 판단 기준 Rubric

각 문서는 아래 기준으로 0~3점을 매긴다. 2점 미만 항목이 있으면 canonical 후보가 아니라 analyzed 상태로 둔다.

| 기준 | 0점 | 1점 | 2점 | 3점 |
|---|---|---|---|---|
| Source Coverage | 출처 없음 | 일부 파일만 확인 | API/SP/Table 중 2계층 이상 확인 | API→Service→Repository→SP→Table 또는 SP→Table read/write까지 확인 |
| Business Rule | 설명 없음 | 일반 설명 | SP/코드 근거 있는 규칙 | 상태값/예외/하드코딩/배치 조건까지 포함 |
| Operational Usefulness | 읽기용 요약 | 일부 점검 포인트 | 증상별 확인 순서 있음 | Querybook, 판단 분기, 실패 시 다음 액션까지 있음 |
| Modernization Readiness | 트랙 없음 | Observe/Wrap/Extract 추정 | 트랙과 근거 있음 | 단계별 티켓화 가능한 실행 순서 있음 |
| DB Separation Readiness | 기준 없음 | shared DB 결합 언급 | read/write split 후보 있음 | owner/backfill/reconciliation/rollback 기준 있음 |
| LLM Safety | 추론 금지 없음 | 주의점 일부 | Inferred/Needs Review 구분 | 금지 추론, confidence, unresolved queue 연결 |
| Wiki Integration | 독립 문서 | 링크 일부 | index/service/domain 링크 연결 | graph/generated/queue/action register와 연결 |
| Maintainability | 긴 리포트 | 섹션만 있음 | source anchor 있음 | generated 영역, history, stale 조건까지 있음 |

Canonical 후보 최소 기준:

- Source Coverage ≥ 2
- Business Rule ≥ 2
- Operational Usefulness ≥ 2
- Modernization Readiness ≥ 2
- DB Separation Readiness ≥ 2
- LLM Safety ≥ 2
- lint 통과
- Needs Review가 명시되어 있음

Canonical 승격 기준:

- 사람 검토 완료
- dirty source 없음
- 핵심 source path/hash 기록
- source 없는 판단 없음
- 운영자가 실제 장애/티켓에서 재사용 가능하다고 판단

## Ralph Loop Pass별 산출물

| Pass | 산출 |
|---|---|
| `source-inventory-pass` | source inventory, dirty source, scan count |
| `graphify-sidecar-pass` | Graphify god node, surprise edge, suggested question 후보. DEV2 graph에는 직접 merge하지 않고 discovery/proposal 후보로만 사용 |
| `table-pass` | table list, fan-out, writer/reader 후보 |
| `sp-pass` | SP contract 후보, caller, read/write table, 위험도 |
| `api-pass` | endpoint, controller action, service/repository 연결 |
| `domain-pass` | 도메인 후보, 핵심 원장, business rule |
| `ownership-pass` | table owner, write owner, read consumer, shared DB coupling |
| `migration-readiness-pass` | Wrap/Extract 후보, read/write split, reconciliation, rollback 기준 |
| `cdc-assessment-pass` | 전체 UPDATE, rename/swap, TRUNCATE/DROP/CREATE, SELECT INTO, 파생 table, lock 후보, CDC 등급, 권장 조치 |
| `ticket-pass` | 기존 티켓/장애/운영 메모와 도메인 연결 |
| `completeness-pass` | orphan, low-confidence, missing source, stale |
| `wiki-sync-pass` | Obsidian wiki, generated block, queue 갱신 |

## Graphify sidecar 사용 기준

Graphify는 Ralph Loop를 대체하지 않는다. 낯선 서비스나 큰 문서 묶음을 먼저 훑어 god node, surprise edge, 질문 후보를 찾는 sidecar discovery 도구로만 쓴다.

권장 요청:

```text
Graphify sidecar를 참고해서 {서비스}의 분석 우선순위를 잡아줘.

제한:
- Graphify 결과는 로컬 Obsidian 운영 지식 위키의 canonical graph에 직접 merge하지 않는다.
- 내부 코드/SP/YouTrack 비공개 원문을 외부 semantic extraction에 보내지 않는다.
- 결과는 graph/generated/graphify/{service}/{run_id}/에 보관하고, discovery/proposal/unresolved queue 후보로만 전환한다.
- canonical 승격은 source path/hash와 사람 검토 후에만 한다.

산출:
- Graphify god node와 surprise edge 요약
- Ralph Loop에서 먼저 돌릴 pass와 도메인 후보
- discovery queue 후보
- 민감 정보 또는 low-confidence 판단 목록
```

사용하면 좋은 경우:

- 서비스 구조를 처음 보는 상황
- docs/claudedocs, 설계 문서, 이미지, PDF가 섞여 있는 상황
- Ralph Loop deep analysis 전에 P0 도메인 후보를 좁혀야 하는 상황
- 기존 graph의 unresolved 항목이 많아 질문 후보를 재정렬해야 하는 상황

사용하지 말아야 하는 경우:

- DB/SP 원문이나 운영 실데이터가 redaction 없이 포함된 상황
- YouTrack 비공개 댓글 원문을 분석 입력으로 넣어야 하는 상황
- canonical graph를 갱신하는 것이 목적이고 adapter/lint가 준비되지 않은 상황
- 단일 티켓의 좁은 코드 변경처럼 `rg`, 기존 graph, 소스 직접 조회가 더 빠른 상황

## 다음 서비스로 확장할 때

서비스 단위 온보딩과 PRD 작성은 [ralph-loop-service-expansion-guide.md](./ralph-loop-service-expansion-guide.md)를 따른다.

기본 순서:

1. `catalog/{service_id}.yaml` 확인
2. 로컬 Obsidian `registry/services/{service_id}.yaml` 준비
3. `templates/ralph-loop-service-prd.json`을 `registry/ralph/prd-{service_id}-full-resource-analysis.json`로 복사해 service id 치환
4. `source-inventory-pass` 실행
5. P0 도메인 선정
6. P0 도메인부터 canonical 후보 문서 작성

다음 서비스 기본 후보:

| 순서 | 서비스 | 이유 |
|---:|---|---|
| 1 | `max` | 투비와 유사한 레거시/SP 중심 서비스라 Ralph Loop 재사용성이 가장 높음 |
| 2 | `naru` | 인증/계정 기반 신규 서비스로 계약 지식 가치가 큼 |
| 3 | `bazaar` | DDD/Kotlin/batch/event 구조를 위키 모델에 반영하기 좋음 |
| 4 | `aasm` | 설정/시크릿/배포 운영 지식 축적에 적합 |

## 피해야 할 표현

| 피할 표현 | 이유 | 대체 표현 |
|---|---|---|
| “완벽하게 분석해줘” | 완료 기준이 없음 | “P0 도메인 canonical 후보 기준으로 분석해줘” |
| “문서 고도화해줘” | 산출물 구조가 불명확 | “Summary/Confirmed/Inferred/Querybook/Needs Review 구조로 작성해줘” |
| “전체 다 봐줘” | 비용과 범위 폭발 | “inventory는 전체, deep analysis는 P0 3개 도메인부터” |
| “위키에 올려줘” | YouTrack KB인지 Obsidian인지 모호 | “로컬 Obsidian 운영 지식 위키에만 반영해줘” |
| “이슈도 정리해줘” | YouTrack write 가능성 발생 | “YouTrack write는 승인 전 금지하고 Action Register에 후보만 남겨줘” |
| “Graphify 결과를 위키에 합쳐줘” | 후보 edge가 canonical 사실처럼 보일 수 있음 | “Graphify sidecar 결과를 discovery/proposal 후보로만 반영해줘” |
