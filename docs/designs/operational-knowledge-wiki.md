# DEV2 운영 지식 위키 설계

## 목적

DEV2 운영 지식 위키는 각 서비스의 소스, DB 스크립트, YouTrack 이슈, YouTrack Knowledge Base, 팀 하네스를 연결하여 서비스 분석, 도메인 지식, 티켓 처리 이력, 스프린트/주간업무/OKR 운영, 개선 후보 관리를 하나의 원칙으로 관리하기 위한 체계다.

이 문서는 Codex와 Claude Code가 같은 기준으로 위키를 읽고 갱신하도록 하기 위한 설계 기준이다.

Obsidian vault 경로는 `/Users/user/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2`로 둔다.

## 기본 원칙

- 서비스 레포에는 실행 소스만 둔다.
- DB/SP 원문은 각 DB script repo를 source of truth로 둔다.
- YouTrack Issue는 공식 업무 상태의 source of truth다.
- YouTrack Knowledge Base는 전사/팀 공통 정책과 컨벤션의 source of truth다.
- team2 레포는 팀 하네스, 정책, 카탈로그, 템플릿의 source of truth다.
- 운영 지식 위키는 분석, 해석, 도메인 맥락, 과거 처리 패턴, 실행 이력, 개선 후보의 단일 지식원천으로 둔다.
- 기존 `docs`, `claudedocs`는 장기적으로 위키로 흡수하고, 서비스 폴더에는 신규 분석 문서를 만들지 않는다.
- source 없는 주장은 canonical 지식으로 승격하지 않는다.
- generated 영역만 자동 갱신하고, human notes는 자동화가 덮어쓰지 않는다.
- DB/SP 변경, 프로덕션 배포, 레거시 경계 변경은 항상 별도 승인 대상으로 표시한다.
- YouTrack 티켓/Task 생성, 티켓 상태/필드 변경, 커밋/푸시/머지는 AI 도구가 임의로 수행하지 않고 사용자 확인 후 실행한다.

## 운영 모델 요약

운영 지식 위키는 티켓 분석만으로 구축하지 않는다. 티켓은 업무 맥락을 잘 설명하지만, 레거시 서비스의 전체 API/SP/Table 의존성, 도메인 용어, 암묵적 비즈니스 규칙은 티켓에 남아 있지 않을 수 있다.

따라서 위키는 두 개의 루프를 병렬로 운영한다.

```text
System Discovery Loop
서비스 repo + DB script repo + 기존 docs/claudedocs
→ API/SP/Table 전체 inventory
→ 호출 그래프
→ 도메인/용어 후보
→ 레거시 계약 지도
→ 변경 영향도 지도

Ticket Execution Loop
YouTrack Issue
→ System Discovery 결과 조회
→ 과거 처리 연결
→ 현재 Feature/Task 판단
→ 스프린트/주간업무/OKR 반영
→ 실행/완료 기록

Feedback Loop
티켓 분석 중 발견한 누락
→ discovery queue 등록
→ System Discovery 보강
→ 관련 ticket/domain/contract 문서 stale 표시 또는 갱신
```

System Discovery Loop는 팀의 기억을 사전에 구축하는 루프이고, Ticket Execution Loop는 실제 업무를 빠르게 판단하고 실행하는 루프다. 두 루프는 같은 graph와 wiki를 사용해야 한다.

## 지식 원천 역할

| 원천 | 역할 | 권위 |
|------|------|------|
| 서비스 repo | API, 애플리케이션 로직, 테스트, 배포 코드 | 실행 소스 |
| DB script repo | SP, Function, View, Table 상태, migration | DB 객체 원문 |
| YouTrack Issue | Feature/Task, 담당자, 상태, 스프린트, Story points, 댓글 이력 | 공식 업무 상태 |
| YouTrack KB | 전사/팀 공통 정책, 컨벤션, 트러블슈팅, 온보딩 | 공통 지식 |
| team2 repo | 팀 정책, 서비스 카탈로그, 스킬, 템플릿 | 팀 하네스 |
| 운영 지식 위키 | 분석, 도메인 모델, 계약 지도, 과거 처리 패턴, 실행 기록, 개선 후보 | 분석 지식 |

## Authority Matrix

원천 간 내용이 충돌하면 아래 기준을 따른다.

| 판단 대상 | 우선 원천 | 위키의 역할 |
|-----------|-----------|-------------|
| 실제 코드 동작 | 서비스 repo | 분석/요약/영향도 연결 |
| SP/DB 객체 원문 | DB script repo | 계약, 호출 관계, 변경 영향 정리 |
| 티켓 상태/담당자/스프린트/SP | YouTrack Issue | 과거 처리 맥락과 실행 기록 연결 |
| 전사/팀 공통 컨벤션 | YouTrack KB | 관련 KB 연결과 적용 판단 요약 |
| 팀 하네스 정책/템플릿 | team2 repo | 정책 적용 결과와 예외 사유 기록 |
| 도메인 의미/용어/비즈니스 규칙 | 운영 지식 위키 | source 기반 canonical 분석 지식 |
| 개선 후보/대기 업무 | 운영 지식 위키 | proposal 상태 관리, 티켓 승격 후보 정리 |

위키가 단일 지식원천이라는 말은 "분석과 운영 맥락의 단일 지식원천"을 뜻한다. 실행 사실과 공식 상태는 각 원천의 권위를 유지한다.

## 티켓 상태 동기화 정책

운영 지식 위키의 `status`는 위키 문서의 성숙도를 나타내며, YouTrack Issue의 업무 상태를 대체하지 않는다.

- `status`: `analyzed`, `reviewed`, `canonical`, `archived` 등 위키 문서 성숙도에만 사용한다.
- `youtrack_state`: `Open`, `In Progress`, `Fixed`, `Closed` 등 마지막으로 확인한 YouTrack 상태 스냅샷을 기록한다.
- `youtrack_resolved_at`: YouTrack의 해결 시각이 있을 때만 기록한다.
- `youtrack_synced_at`: 위키가 YouTrack 상태를 마지막으로 확인한 날짜를 기록한다.
- `execution_state`: 로컬 실행 기록의 상태를 `planned`, `running`, `completed`, `blocked` 등으로 기록한다.

티켓이 완료되면 위키에는 append-only 방식으로 `완료 기록` 섹션을 남긴다. 이 섹션에는 실행 결과의 위치, 검증 기준, redaction 여부, 후속 재사용 지식 후보만 기록한다. 개인정보 원문, 운영 실데이터 원문, 결과 엑셀 원문은 위키에 저장하지 않는다.

반복 가능한 처리 기준은 티켓 문서에만 묶어두지 않고 `patterns/`, `guides/`, `contracts/` 등 재사용 문서로 분리한다. 사람 검토 전에는 `analyzed`로 두고, source와 검토 근거가 충분할 때만 `canonical`로 승격한다.

## 보안 및 저장 금지 기준

위키는 장기적으로 많은 source를 연결하므로 저장 가능한 정보와 저장하면 안 되는 정보를 분리한다.

저장 가능:

- source path, commit hash, object hash
- API/SP/Table 이름과 계약
- 도메인/용어/비즈니스 규칙 요약
- YouTrack 이슈 ID와 공개 가능한 처리 맥락
- KB ID와 정책 적용 결과
- redaction된 샘플 구조

저장 금지:

- DB 접속 정보, 비밀번호, API key, token
- 운영 실데이터 원문
- 개인정보 원문
- 결제/인증/보안 민감값
- 외부 LLM 또는 외부 research 도구로 보내면 안 되는 내부 코드/데이터
- 승인되지 않은 프로덕션 운영 절차 세부값

민감 정보가 포함된 source는 redaction 후 요약만 위키에 기록한다. redaction 여부는 frontmatter에 남긴다.

```yaml
redaction:
  required: true
  type: pii-and-secret
  source_contains_sensitive_data: true
```

## 권장 저장 구조

```text
/Users/user/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/
  AGENTS.md
  CLAUDE.md

  registry/
    services/
      max.yaml
      tobe.yaml
      naru.yaml
      bazaar.yaml
    source-types.yaml
    taxonomy.yaml

  graph/
    contract-graph.json
    work-graph.json
    glossary-graph.json
    discovery-queue.json
    proposal-queue.json
    unresolved-queue.json

  wiki/
    _index.md
    _log.md
    services/
    domains/
    contracts/
      apis/
      stored-procedures/
      tables/
    tickets/
    projects/
    execution/
    proposals/
    tasks/
      discovery-queue.md
      action-register.md
    decisions/
    patterns/
    glossary/
    archive/

  scripts/
    scan_sources.py
    analyze_ticket.py
    build_graph.py
    generate_wiki.py
    lint_wiki.py
```

## 서비스 추가 추상화

서비스는 언제든 추가 가능해야 하며, 서비스별 차이는 코드가 아니라 registry 설정으로 표현한다.

예시:

```yaml
id: tobe
name: 투비컨티뉴드
type: legacy
status: active

repos:
  app:
    path: /Users/user/Documents/workspace/tobe-project/Tobe
    language: csharp
  db:
    path: /Users/user/Documents/workspace/tobe-project/tobe-db-script
    kind: mssql-db-script

scan:
  api_patterns:
    - "**/Controllers/**/*.cs"
    - "**/Bll/**/*.cs"
    - "**/Dal/**/*.cs"
  sp_patterns:
    - "databases/**/StoredProcedures/*.sql"
  table_patterns:
    - "databases/**/Tables/*.sql"

wiki:
  namespace: tobe
  service_page: wiki/services/tobe.md

youtrack:
  service_name: 투비
```

## 그래프 모델

위키는 마크다운으로 사람이 읽는 계층이고, 실제 변경 영향도와 자동화는 그래프를 기준으로 동작한다.

노드:

- Service
- Repository
- API Endpoint
- Controller/Action
- Service Method
- Repository Method
- Stored Procedure
- Function/View
- Table
- Domain
- Business Rule
- Glossary Term
- YouTrack Issue
- YouTrack KB Article
- Project
- Proposal
- Execution Record
- Decision
- Discovery Item

엣지:

- API `calls` Controller/Service/Repository
- Repository `calls` Stored Procedure
- Stored Procedure `calls` Stored Procedure
- Stored Procedure `reads` Table
- Stored Procedure `writes` Table
- API/SP `implements` Business Rule
- Business Rule `belongs_to` Domain
- Issue `changes` API/SP/Table
- Issue `relates_to` KB Article
- Proposal `promotes_to` Issue
- Execution Record `documents` Issue
- Domain `uses_term` Glossary Term
- Discovery Item `blocks` Domain/API/SP/Table
- Discovery Item `discovered_from` Issue/Document/Source

## 문서 상태

모든 주요 위키 문서는 상태를 가진다.

```yaml
knowledge_status:
  discovered: 발견됨
  imported: 기존 docs/claudedocs에서 가져옴
  analyzed: LLM 분석 완료
  reviewed: 사람 검토 완료
  canonical: 공식 위키 지식
  stale: 원본 변경으로 재검토 필요
  superseded: 더 최신 문서로 대체됨
  archived: 보관만 함
```

전체 로직 분석 대상은 discovery 상태를 별도로 가진다.

```yaml
discovery_status:
  not-scanned: 아직 분석 안 됨
  indexed: 목록 수집됨
  linked: API/SP/Table 관계 연결됨
  domain-candidate: 도메인 후보 분류됨
  reviewed: 사람 검토됨
  canonical: 공식 위키 지식
  stale: 원본 변경으로 재분석 필요
  blocked: 분석에 필요한 소스/권한/정책 확인이 막힘
```

업무/제안 상태는 별도로 관리한다.

```yaml
work_status:
  discovered: 자동 발견
  needs-triage: 사람 검토 필요
  accepted: 진행 승인
  rejected: 폐기
  ticket-needed: YouTrack 티켓 필요
  ticket-created: 티켓 생성됨
  assigned-to-agent: 에이전트 작업 대기
  in-progress: 진행 중
  implemented: 코드/SP 변경 완료
  verified: 검증 완료
  documented: 위키 반영 완료
  done: 완료
  archived: 보관
```

queue는 목적별로 나눈다.

| Queue | 파일 | 역할 |
|-------|------|------|
| Discovery Queue | `graph/discovery-queue.json`, `wiki/tasks/discovery-queue.md` | 전체 로직 분석 중 미해결 API/SP/Table/도메인 후보 |
| Proposal Queue | `graph/proposal-queue.json`, `wiki/proposals/` | 개선안, 리팩터링, 문서화, 티켓 후보 |
| Action Register | `wiki/tasks/action-register.md` | 사람이 검토하거나 실행해야 하는 현재 대기 작업 |
| Unresolved Queue | `graph/unresolved-queue.json` | 충돌, source 불명, low-confidence 판단 |

YouTrack 상태와 위키 상태는 다음 기준으로 매핑한다.

| YouTrack State | Wiki work status |
|----------------|------------------|
| Backlog | backlog |
| Open | open |
| In Progress | in-progress |
| Fixed | verified |
| Closed | done |

## 마크다운 파일명 규칙

마크다운 기반 위키에서 파일명은 stable id와 링크 계약이다.

- 파일명은 영문 kebab-case를 사용한다.
- 한글 제목은 `title` frontmatter와 H1에만 사용한다.
- 파일명은 불필요하게 변경하지 않는다.
- 외부 ID가 있는 문서는 ID를 파일명에 포함한다.
- 날짜는 proposal, execution, log, snapshot 계열에만 사용한다.
- 충돌 가능성이 있는 문서는 서비스 namespace를 경로로 분리한다.
- YouTrack 티켓 문서는 예외 없이 `wiki/tickets/{ticket-id-lowercase}.md` flat 구조를 사용한다. 예: `wiki/tickets/dev2-6006.md`
- 티켓 문서에는 프로젝트별 하위 폴더(`wiki/tickets/DEV2/`)를 만들지 않는다.
- 티켓 문서 frontmatter는 `type: ticket`, `ticket: DEV2-0000`, `canonical_id: ticket:dev2-0000`, `sources:` 배열을 사용한다. `type: ticket-analysis`, `issue_id`, 단수 `source:`는 사용하지 않는다.

예시:

```text
wiki/services/tobe.md
wiki/domains/user-context.md
wiki/contracts/apis/tobe/get-user-context.md
wiki/contracts/stored-procedures/tobe/tobe-dbo-tobe-user-get-context-info.md
wiki/contracts/tables/max/webcatalog-goods.md
wiki/tickets/dev2-5572.md
wiki/projects/tobe-nextjs-kotlin-migration.md
wiki/proposals/prop-20260507-001-wrap-user-context-sp.md
wiki/decisions/adr-0001-use-wiki-as-analysis-ssot.md
wiki/glossary/member.md
```

주요 문서는 `canonical_id`를 가진다.

```yaml
canonical_id: ticket:dev2-5572
canonical_id: domain:user-context
canonical_id: service:tobe
canonical_id: sp:tobe:tobe:dbo:tobeuser_getcontextinfo
canonical_id: proposal:20260507-001
```

문서 생성 전에는 `canonical_id`, `title`, `aliases`로 기존 문서를 검색하고, 없을 때만 새 문서를 생성한다.

## Obsidian 링크와 인덱스

위키 링크는 별도 Obsidian 플러그인에 의존하지 않고 plain wikilink를 기본으로 한다.

- 링크 기준 ID는 frontmatter의 `canonical_id`다.
- `scripts/generate_wiki.py`가 `canonical_id -> wiki path`를 해석해 `[[services/tobe|투비컨티뉴드]]` 형식의 vault-root 상대 링크를 생성한다.
- 자동 링크 산출물은 `wiki/indexes/services.md`, `wiki/indexes/domains.md`, `wiki/indexes/graphify.md`와 각 주요 문서의 `Related Links` generated block에만 쓴다.
- 사람이 작성한 본문 링크는 유지하고, 자동 갱신 영역은 generated block으로 격리한다.
- `scripts/lint_wiki.py`는 깨진 wikilink, 누락된 navigation index, 누락된 `related-links` block을 warning으로 보고한다.

Dataview, Breadcrumbs 같은 Obsidian 플러그인은 선택 사항이다. 팀 하네스의 유지 계약은 Markdown 파일, frontmatter, generated block, lint로 충분히 동작해야 한다.

## 위키 문서 공통 형식

주요 문서는 다음 구조를 따른다.

```markdown
---
type: domain
title: 사용자 컨텍스트
canonical_id: domain:user-context
status: canonical
sources:
  - repo: /Users/user/Documents/workspace/tobe-project/Tobe
  - kb: DEV2-A-892
review_state: reviewed
updated_at: 2026-05-07
---

# 사용자 컨텍스트

<!-- GENERATED:START -->
자동 생성 영역. 소스 경로, commit, hash, 그래프에서 계산한 관계를 기록한다.
<!-- GENERATED:END -->

## Confirmed

원본 소스, DB script, YouTrack, KB로 확인된 사실.

## Inferred

근거 기반 추론. 단정하지 않는다.

## Needs Review

사람 검토가 필요한 도메인명, 용어, 정책 판단.

## Actions

티켓화, 분석, 구현, 검증, 문서화 후보.

## History

언제 어떤 원본 변경으로 갱신됐는지 기록한다.
```

## System Discovery Loop

System Discovery Loop는 티켓과 무관하게 서비스 전체 구조를 계속 분석한다. 목적은 티켓 분석 시 매번 전체 소스를 다시 읽지 않도록 사전 지식 기반을 만드는 것이다.

분석 대상:

- 서비스 repo의 API, Controller, Service, Repository, DTO, 테스트
- DB script repo의 SP, Function, View, Table, Type, Index, migration
- 기존 `docs`, `claudedocs`, 설계 문서, 운영 메모
- YouTrack KB의 정책/컨벤션/트러블슈팅 문서
- YouTrack Issue 중 완료된 주요 처리 사례

분석 흐름:

```text
1. service registry에서 대상 서비스 목록을 읽는다.
2. 각 서비스 repo와 DB script repo의 현재 commit, dirty 상태, scan pattern을 기록한다.
3. API/SP/Table/Function/View 전체 inventory를 만든다.
4. API → Controller → Service → Repository → SP 호출 후보를 추출한다.
5. SP → SP, SP → Table read/write 관계를 추출한다.
6. 기존 docs/claudedocs를 ticket/domain/project/execution/pattern/glossary 후보로 분류한다.
7. 이름, 호출 군집, 테이블 의존성, 과거 티켓을 기준으로 도메인 후보를 만든다.
8. confidence와 evidence를 기록한다.
9. low-confidence, dynamic SQL, orphan SP/API, source 불명 항목은 discovery queue에 등록한다.
10. graph와 generated wiki block을 갱신한다.
```

분석 깊이는 두 단계로 나눈다.

| 단계 | 목적 | 범위 |
|------|------|------|
| Wide inventory | 누락 없는 목록과 1차 관계 확보 | 모든 서비스의 API/SP/Table |
| Deep analysis | 실제 비즈니스 규칙과 변경 영향 파악 | 변경 빈도 높거나 장애 영향 큰 도메인 |

deep analysis 우선순위:

1. 현재 스프린트 티켓과 연결된 도메인
2. 최근 30일 변경된 API/SP/Table
3. 호출 위치가 많은 SP
4. 공유 DB/Table을 사용하는 로직
5. 장애/운영 이력이 있는 기능
6. 신규 서비스로 Wrap/Extract 후보가 되는 영역

Discovery Queue 예시:

```markdown
# Discovery Queue

## High Priority
- [ ] tobe: `TobeUser_GetContextInfo` 호출 API 확정
- [ ] tobe: `IsAuth19` 관련 SP/Table 전체 연결
- [ ] max: 정산 관련 SP 군집 분류

## Medium Priority
- [ ] tobe: 광고/리워드 용어 사전 정리
- [ ] max: 구매이용권 도메인 후보 검토
```

## Ticket Execution Loop

어떤 티켓을 분석하면 다음 흐름을 따른다.

```text
1. YouTrack Issue 조회
2. 관련 YouTrack KB 문서 조회
3. team2 하네스 정책 확인
4. System Discovery 결과에서 관련 API/SP/Table/도메인을 먼저 조회
5. 기존 위키에서 유사 티켓, 도메인, 패턴 검색
6. 부족한 관계만 추가 소스 분석
7. 과거 처리 방식 요약
8. 현재 판단 기준 생성
9. Feature/Task 분해안 생성
10. 스프린트, 주간업무, OKR 반영안 생성
11. proposal/action queue 갱신
12. 사람 승인 후 실행
13. 결과를 YouTrack, 위키, 그래프에 반영
14. 티켓 분석 중 발견한 누락은 discovery queue로 되돌림
```

티켓 분석 문서는 다음 항목을 포함한다.

- 요청 요약
- 기존 유사 처리
- 연결된 API/SP/Table/문서/KB
- 판단 기준
- Feature/Task 분해
- 스프린트 반영
- 주간업무 반영
- OKR 연결
- 승인 필요 항목
- Actions

티켓 분석 문서는 `wiki/tickets/{ticket-id-lowercase}.md`에 등록한다. H1은 `DEV2-0000 ...`처럼 원래 티켓 ID 대문자를 유지하되, 파일명과 `canonical_id`는 소문자를 사용한다.

## Feedback Loop

Ticket Execution Loop와 System Discovery Loop는 서로를 보강해야 한다.

```text
System Discovery가 Ticket Execution을 빠르게 만든다.
Ticket Execution이 System Discovery의 누락을 찾아낸다.
```

Feedback 등록 기준:

- 티켓 분석 중 graph에 없는 API/SP/Table이 발견됨
- 과거 처리 문서가 있지만 domain/ticket/project에 흡수되지 않음
- 같은 용어가 서비스마다 다르게 쓰임
- SP는 발견됐지만 호출 API가 불명확함
- API는 발견됐지만 담당 도메인 후보가 low-confidence임
- YouTrack KB 또는 팀 하네스 정책과 위키 판단이 충돌함
- 완료된 티켓이 있는데 execution record가 없음

Feedback 처리 결과:

- graph 갱신
- 관련 wiki 문서 `stale` 표시 또는 generated block 갱신
- discovery queue 항목 close
- 필요한 경우 proposal queue 또는 YouTrack 티켓 후보 생성

## 스프린트, 주간업무, OKR 연결

스프린트 운영은 `docs/sprint/sprint-workflow-execution.md`와 `docs/sprint/ticket-guide.md`를 따른다.

- Feature는 1주 이내 단위로 분해한다.
- Task는 1일 이내 단위로 분해한다.
- 최하위 Task에 Story points를 부여한다.
- 상위 Feature는 Story points 0을 기본으로 한다.
- Open 상태 티켓에는 예상 시작 일자를 둔다.
- Done/Closed 처리 시 결과물 링크를 남긴다.
- 이월 시 사유와 재확인 조건을 YouTrack 댓글로 남긴다.

주간업무 보고는 YouTrack 상태를 기준으로 분류한다.

| 분류 | 기준 |
|------|------|
| 백로그 | Backlog |
| 미진행 항목 | Open |
| 진행 중 항목 | In Progress |
| 완료된 항목 | Fixed 또는 Closed |

OKR은 위키의 티켓/프로젝트 문서에 연결하고, YouTrack 티켓에는 관련 OKR 또는 KR 근거를 남긴다.

## 기존 docs/claudedocs 흡수

기존 서비스 폴더의 `docs`, `claudedocs`는 migration 대상으로 본다.

```text
1. 문서 inventory 생성
2. ticket / domain / project / execution / pattern / glossary로 분류
3. 위키 canonical 문서로 흡수
4. 원문 경로와 commit/path를 source로 기록
5. 중복/오래된 문서는 archive 또는 superseded 상태로 표시
6. 이후 신규 분석 문서는 위키에만 작성
```

흡수 후 서비스 repo에는 소스, 테스트, 배포 관련 실행 파일만 남기는 것을 목표로 한다.

흡수 우선순위:

1. 완료된 티켓과 직접 연결된 분석 문서
2. 현재 스프린트 또는 다음 스프린트 후보와 연결된 문서
3. SP/API/Table 영향도 분석 문서
4. 도메인 용어 사전 또는 정책 판단 문서
5. 운영/장애/배포 회고 문서
6. 중복되거나 오래된 개인 메모

흡수 후 원문 문서는 다음 중 하나로 처리한다.

| 상태 | 처리 |
|------|------|
| canonical 승격 완료 | 위키 문서에서 source path로만 참조 |
| 일부만 유효 | 위키에 유효 범위를 명시하고 원문은 superseded 처리 |
| 검증 불가 | archive 상태로 보관하고 canonical 판단에 사용하지 않음 |
| 민감 정보 포함 | redaction 후 요약만 위키화, 원문은 저장하지 않음 |

## 자동화 모드

Codex skill과 Claude Code command는 같은 registry, scripts, wiki, graph를 사용한다.

권장 모드:

| 모드 | 역할 |
|------|------|
| `scan` | workspace source inventory, 변경 감지 |
| `ingest` | docs/claudedocs/YouTrack/KB/DB script 수집 |
| `discovery` | API/SP/Table 전체 inventory와 의존성 그래프 갱신 |
| `ticket` | 티켓 분석, 과거 처리 연결, 판단 기준 생성 |
| `contract-map` | API/SP/Table 의존성 그래프 생성 |
| `domain-map` | 도메인/용어 후보 분류 |
| `propose` | 개선안, 문서화, 리팩터링, 티켓 후보 생성 |
| `triage` | proposal queue를 사람 검토용으로 정리 |
| `plan` | Feature/Task/스프린트/OKR 반영안 생성 |
| `execute` | 승인된 티켓 기준으로 에이전트 작업 실행 |
| `review` | diff, 테스트, 정책 위반, 문서 누락 검토 |
| `sync` | 위키, 그래프, YouTrack 링크 반영 |
| `lint` | stale 문서, orphan graph, low-confidence 항목 탐지 |

모드 간 기본 실행 순서:

```text
scan
→ discovery
→ ingest
→ ticket
→ plan
→ triage
→ execute
→ review
→ sync
→ lint
```

단일 티켓 분석 시에는 `ticket`이 먼저 System Discovery 결과를 조회하고, 부족한 부분만 `discovery`에 보강 요청을 넣는다.

## Runner Strategy

운영 지식 위키의 자동화 runner는 무거운 상시 에이전트보다 가벼운 반복 분석 루프를 우선한다.

| Runner | 역할 | 도입 우선순위 | 판단 |
|--------|------|---------------|------|
| Ralph Loop | 내부 소스, DB script, 기존 문서를 정해진 pass 단위로 분석 | 1순위 | System Discovery Loop의 기본 runner |
| Graphify sidecar | 코드/문서/PDF/이미지를 별도 knowledge graph로 분석하고 god node, surprise edge, query 후보를 만든다 | 1.5순위 | DEV2 graph의 source of truth가 아니라 discovery accelerator |
| Auto Research | 외부 자료, 오픈소스, 일반 패턴, 정책 비교 조사 | 2순위 | 내부 소스 분석이 아니라 보조 research runner |
| Hermes Agent | 장기 실행 agent platform, cron, memory, gateway, subagent orchestration | 보류 | 추후 운영자가 필요할 때 파일럿 |

### Ralph Loop

Ralph Loop는 PRD story와 quality gate를 가진 반복 분석 방식으로 사용한다. 이미 `max-msa`에서 사용한 table pass, SP pass, domain pass, completeness pass 패턴을 운영 지식 위키의 System Discovery Loop에 맞게 일반화한다.

권장 pass:

| Pass | 목적 |
|------|------|
| `source-inventory-pass` | 서비스 repo, DB script repo, docs/claudedocs 목록화 |
| `table-pass` | Table 목록, fan-out, 관련 SP, 후보 도메인 정리 |
| `sp-pass` | SP 계약, caller, read/write table, 위험도 정리 |
| `api-pass` | API endpoint, controller/service/repository, 호출 SP 연결 |
| `domain-pass` | API/SP/Table 군집 기반 도메인 후보 분류 |
| `ticket-pass` | 완료/진행/후보 티켓과 도메인/계약 연결 |
| `completeness-pass` | orphan, low-confidence, missing source, stale 문서 탐지 |
| `wiki-sync-pass` | generated block, graph, discovery queue 갱신 |

Ralph Loop quality gate:

```text
- 서비스 repo 원본은 수정하지 않는다.
- DB/SP 원문은 위키로 복사하지 않고 source path와 hash만 기록한다.
- source 없는 판단은 canonical로 승격하지 않는다.
- 민감 정보는 redaction 후 요약만 기록한다.
- generated 영역만 자동 갱신한다.
- 선택한 story 범위만 다룬다.
- 분석 결과는 graph, wiki generated block, discovery queue 중 하나에 남긴다.
```

PRD story 예시:

```json
{
  "version": 1,
  "project": "dev2-operational-wiki-discovery-pass",
  "qualityGates": [
    "서비스 repo 원본은 수정하지 않는다.",
    "DB/SP 원문은 복사하지 않고 source path와 hash만 기록한다.",
    "source 없는 판단은 canonical로 승격하지 않는다.",
    "민감 정보는 redaction 후 요약만 기록한다.",
    "generated 영역만 자동 갱신한다."
  ],
  "stories": [
    {
      "id": "DISCOVERY-010",
      "title": "tobe SP inventory를 갱신한다",
      "status": "open",
      "acceptanceCriteria": [
        "SP 목록이 graph에 등록된다.",
        "각 SP가 source_path와 source_hash를 가진다.",
        "분석 불가 항목은 discovery queue에 남는다."
      ]
    }
  ]
}
```

### Graphify sidecar

Graphify는 운영 지식 위키의 canonical graph를 대체하지 않는다. 별도 sidecar 산출물로 실행하고, 결과는 후보 지식으로만 사용한다.

사용 대상:

- 신규 서비스나 낯선 서비스의 god node, 중심 모듈, 예상치 못한 연결을 빠르게 파악
- 기존 docs/claudedocs, 설계 문서, 이미지, PDF를 함께 읽어 도메인 후보를 찾기
- Ralph Loop deep analysis 전에 질문 후보와 우선순위를 좁히기
- `GRAPH_REPORT.md`의 surprise edge를 discovery queue 후보로 전환하기

저장 위치:

```text
graph/generated/graphify/{service_id}/{run_id}/
  graph.json
  GRAPH_REPORT.md
  graph.html
  metadata.json
```

반영 흐름:

```text
trigger event
  -> graphify trigger queue
  -> policy gate
  -> Graphify sidecar
  -> graphify-out/graph.json + GRAPH_REPORT.md
  -> DEV2 adapter
  -> redaction + schema validation
  -> discovery/proposal/unresolved queue 후보
  -> human review
  -> canonical graph/wiki promotion
```

Graphify는 사람이 직접 실행하는 운영 루틴이 아니라 trigger 기반으로 후보 실행을 만든다. 단, trigger가 곧바로 canonical graph를 수정하지 않는다.

트리거 후보:

| Trigger | 발생 조건 | 기본 동작 |
|---------|-----------|-----------|
| service registry 추가 | `registry/services/{service_id}.yaml` 신규 등록 | 해당 서비스 `graphify-sidecar-pass` 후보 등록 |
| source commit/hash 변경 | `scan_sources.py`가 서비스 repo 또는 DB script repo의 commit/hash 변화를 감지 | code/sql AST 중심 sidecar 후보 등록 |
| docs/claudedocs 변경 | 기존 문서 inventory가 증가하거나 hash가 바뀜 | docs sidecar 후보 등록. semantic extraction은 gate 필요 |
| unresolved 급증 | `unresolved-queue.json`의 low-confidence 항목이 임계치 이상 | god node/surprise edge 탐색 후보 등록 |
| ticket 분석 중 graph 누락 | 관련 API/SP/Table/도메인이 graph에 없음 | 해당 범위만 sidecar 후보 등록 |
| 주기 실행 | launchd/cron/CI가 `run_all.py` 또는 전용 runner 실행 | 큐에 쌓인 eligible 항목만 실행 |

실행 정책:

- git hook은 Graphify를 직접 실행하지 않고 queue item만 추가한다.
- `run_all.py` 이후 단계에서 `plan_graphify_runs.py`가 후보를 만들고, `run_graphify_queue.py`가 policy gate를 통과한 항목만 실행한다.
- code/sql AST 로컬 추출은 자동 실행 가능하다.
- docs/images/PDF semantic extraction은 redaction, 파일 크기, 모델 전송 정책을 통과해야 한다.
- 같은 service/source hash 조합은 24시간 안에 중복 실행하지 않는다.
- Graphify 실패는 pipeline 실패로 보지 않고 sidecar run 실패 이벤트로 기록한다.

Graphify 결과를 DEV2 graph에 직접 merge하지 않는다. adapter는 다음 항목을 반드시 보강해야 한다.

- DEV2 `canonical_id`
- source path, commit, source hash
- `confidence`와 `review_state`
- `EXTRACTED`, `INFERRED`, `AMBIGUOUS` 같은 원천 태그
- 민감 정보 탐지 결과
- generated artifact 경로

Graphify 실행 제한:

- 내부 코드/SP/YouTrack 비공개 원문을 외부 LLM semantic extraction에 보내지 않는다.
- code/sql AST 로컬 추출만으로 충분한 파일럿부터 시작한다.
- docs/images/PDF semantic extraction은 redaction policy와 사용 모델 확인 후 허용한다.
- `graphify codex install`처럼 AGENTS.md/CLAUDE.md를 자동 수정하는 설치 명령은 팀 하네스 리뷰 없이 실행하지 않는다.
- 최신 버전 적용은 파일럿 branch 또는 별도 run directory에서 먼저 검증한다.

### Auto Research

Auto Research는 내부 소스 분석의 대체물이 아니다. 외부 문서, 오픈소스 도구, 일반 아키텍처 패턴, 보안/LLM 운영 리스크를 조사하여 decision/proposal 문서의 참고자료를 만든다.

사용 대상:

- 지식 그래프, GraphRAG, agent workflow 패턴 조사
- 오픈소스 도구 비교
- LLM memory, skill, agent runner 보안 리스크 조사
- YouTrack KB 또는 팀 하네스와 외부 best practice 비교
- 새로운 runner 또는 분석 도구 도입 검토

금지 대상:

- 내부 코드 원문 업로드
- SP/DB 원문 업로드
- YouTrack 비공개 댓글 원문 업로드
- 운영 실데이터, 개인정보, 시크릿 전달

### Hermes Agent

Hermes Agent는 지금 단계에서는 도입하지 않는다. 장기 실행 agent platform, messaging gateway, memory, cron, subagent orchestration이 필요해지는 시점에 별도 파일럿으로 검토한다.

도입을 재검토할 조건:

- Ralph Loop가 안정적으로 돌아가고도 주기적 실행/알림 운영 부담이 크다.
- discovery queue와 proposal queue가 충분히 정제되어 자동 스케줄링 가치가 생긴다.
- Docker 또는 별도 VM 기반 read-only sandbox 운영이 준비된다.
- Hermes memory가 canonical source가 되지 않도록 wiki/graph 쓰기 규칙이 확정된다.

파일럿 시 제한:

- read-only workspace mount로 시작한다.
- gateway는 비활성화한다.
- local backend 대신 container backend를 우선한다.
- service repo, DB script repo, YouTrack, KB 수정 권한을 주지 않는다.
- 결과는 proposal queue 또는 generated block 초안에만 남긴다.

## Codex와 Claude Code 공용화

두 도구는 같은 상태 파일과 스크립트를 사용해야 한다.

```text
AGENTS.md
  Codex용 운영 규칙

CLAUDE.md
  Claude Code용 운영 규칙

skills/dev2-operational-wiki-ko/
  Codex skill

.claude/commands/ad/wiki-*.md
  Claude Code command

scripts/
  두 도구가 공통으로 호출하는 구현
```

공통 규칙:

- 작업은 가능한 한 YouTrack 티켓에서 시작한다.
- 승인된 YouTrack 티켓이 없는 코드 변경은 분석/초안 단계에 머문다.
- 브랜치명은 `feature/{이슈ID}`를 사용한다.
- 커밋 메시지는 `[{이슈ID}] 작업 내용`을 사용한다.
- 작업 결과는 YouTrack, 위키, 그래프에 연결한다.
- subagent는 승인된 proposal 또는 ticket 단위로만 실행한다.

## 자동화 레벨

```text
Level 0. 수동 분석
사람이 요청하면 특정 서비스/SP/API/티켓을 분석한다.

Level 1. 자동 수집
workspace 전체에서 변경, 문서, 티켓, SP/API 의존성을 inventory로 만든다.

Level 2. 자동 후보 생성
미분류 도메인, stale 문서, orphan SP, 반복 이슈, 개선 후보를 queue에 등록한다.

Level 3. 사람 승인 후 실행
승인된 후보만 YouTrack 티켓/브랜치/작업 단위로 에이전트에게 위임한다.

Level 4. 제한적 자동 실행
문서 generated block 갱신, wiki lint, graph 재생성 같은 저위험 작업은 자동 실행할 수 있다.

Level 5. 고위험 작업 승인제
DB/SP 변경, 프로덕션 배포, 레거시 경계 변경은 항상 사람 승인을 요구한다.
```

자동화별 허용 범위:

| 자동화 | 사람 승인 필요 여부 | 비고 |
|--------|--------------------|------|
| inventory 생성 | 불필요 | read-only |
| graph 재생성 | 불필요 | generated artifact |
| generated block 갱신 | 원칙적으로 불필요 | human notes 보호 필수 |
| canonical 승격 | 필요 | 도메인/정책 판단 포함 |
| proposal 생성 | 불필요 | 실행 아님 |
| YouTrack 티켓 생성 | 초안은 불필요, 생성은 필요 | 5W1H 확인 후 생성 |
| 코드 변경 | 필요 | YouTrack 티켓 기준 |
| DB/SP 변경 | 필요 | 별도 승인 대상 |
| 배포 | 필요 | 프로덕션 배포 승인 |

## Subagent 역할

| 역할 | 책임 |
|------|------|
| Explorer | 특정 서비스/API/SP 관계 탐색, 변경 영향도 조사 |
| Domain analyst | 도메인 후보, 용어, 비즈니스 규칙 정리 |
| Ticket writer | 5W1H 기준 Feature/Task 초안 생성 |
| Implementation worker | 승인된 YouTrack 티켓 기준 코드 변경 |
| Review agent | diff 리뷰, 정책 위반, 테스트 누락 확인 |
| Wiki maintainer | generated block, `_log.md`, action register 갱신 |

Subagent는 서로 다른 write set을 가져야 하며, 같은 문서를 동시에 수정하지 않는다.

## Engineering Review 결정

`plan-eng-review` 기준으로 이 설계는 단일 위키를 만드는 방향은 맞지만, MVP 전에는 신뢰 경계와 생성물 경계를 먼저 고정해야 한다.

### Scope Challenge

전체 서비스를 한 번에 완전 분석하는 것은 목표 상태이지 MVP 범위가 아니다. MVP는 `tobe` 1개 서비스로 `API -> Repository -> SP -> Table` 경로가 실제로 갱신 가능한지 검증한다. `max`는 기존 Ralph Loop 산출물이 있어 재사용 가치는 높지만, 컴포넌트와 SP 수가 많아 첫 검증 대상으로는 크다.

### Architecture Decisions

| 결정 | 내용 |
|------|------|
| Vault 경계 | 운영 지식 위키는 `/Users/user/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2` Obsidian vault를 기준으로 둔다. `team2` git repo는 하네스 정책과 설계의 source of truth로 유지한다. |
| MVP 대상 | 첫 서비스는 `tobe`로 한다. DB script repo가 git 기반으로 관리되고, 서비스 단위 검증 범위가 `max`보다 작다. |
| 원본 보존 | 서비스 repo와 DB script repo는 read-only source로만 읽는다. 위키가 SP 원문이나 코드 원문을 복제하지 않는다. |
| 생성물 포맷 | `registry/*.yaml`은 사람이 관리하고, `graph/*.json`은 결정적 snapshot, `events/*.jsonl`은 append-only 실행 이력, `wiki/**/*.md`는 사람이 읽는 계층으로 둔다. |
| 자동 갱신 | 자동화는 `<!-- GENERATED:START -->`와 `<!-- GENERATED:END -->` 사이만 수정한다. human notes, Confirmed/Inferred/Needs Review는 덮어쓰지 않는다. |
| stale 판정 | source commit, source hash, scanner version, graph schema version이 바뀌면 관련 문서를 `stale` 후보로 표시한다. |
| 외부 research | Auto Research에는 내부 코드/SP/YouTrack 비공개 원문을 보내지 않는다. 외부 도구는 일반 패턴과 도구 비교에만 사용한다. |
| Graphify 적용 | Graphify는 sidecar discovery 도구로만 쓴다. `graphify-out` 결과는 adapter와 lint를 거친 후보 지식이며, DEV2 canonical graph에 직접 merge하지 않는다. |
| 실행 권한 | Ralph Loop와 Codex/Claude command는 기본 read-only이며, YouTrack 생성/코드 변경/DB 변경/배포는 승인 단계 이후에만 가능하다. |

### Data Flow

```text
service registry
  -> source scanners
  -> inventory records
  -> graph builder
  -> generated wiki blocks
  -> wiki lint/stale detector

YouTrack Issue + YouTrack KB
  -> ticket ingester
  -> work graph
  -> ticket/project/execution wiki pages
  -> sprint/weekly/OKR reflection

Ralph Loop PRD
  -> bounded analysis pass
  -> graph/wiki/queue draft
  -> human review
  -> canonical promotion or discovery queue

Graphify sidecar
  -> trigger queue
  -> policy gate
  -> graphify-out/graph.json + GRAPH_REPORT.md
  -> adapter/redaction/lint
  -> discovery/proposal/unresolved queue 후보
  -> human review
```

### Failure Modes

| 실패 모드 | 처리 기준 |
|-----------|-----------|
| service repo 또는 DB script repo 경로 없음 | service discovery를 `blocked`로 기록하고 queue에 남긴다. |
| 원본 repo dirty 상태 | commit과 dirty flag를 함께 기록하고 canonical 승격을 막는다. |
| dynamic SQL 또는 reflection 호출 | confidence를 낮추고 `unresolved-queue`에 남긴다. |
| generated block 밖 변경 시도 | lint 실패로 처리하고 자동화 결과를 폐기한다. |
| 민감 정보 탐지 | wiki write를 차단하고 redaction-required 상태로 남긴다. |
| YouTrack MCP 장애 | ticket sync를 skip하고 로컬 graph/wiki만 갱신한다. |
| graph schema 변경 | schema version을 올리고 migration note를 `wiki/_log.md`에 남긴다. |
| 동일 canonical_id 중복 | 새 문서 생성을 중단하고 merge 후보로 queue에 남긴다. |
| trigger가 너무 자주 발생 | service/source hash 기준 debounce를 적용하고 queue item을 병합한다. |
| git hook에서 무거운 실행 발생 | hook은 enqueue만 허용하고 Graphify 실행은 runner에서만 처리한다. |
| Graphify inferred edge를 사실로 오인 | `review_state: needs-review`와 원천 태그를 유지하고 canonical 승격을 막는다. |
| Graphify output schema 변경 | adapter 변환을 실패 처리하고 sidecar 산출물만 보관한다. |
| Graphify semantic extraction에 민감 원문 포함 | 실행 전 redaction gate에서 차단하고 `unresolved-queue`에 승인 필요 항목으로 남긴다. |

### Test Plan

MVP 구현 전 최소 검증 항목은 다음과 같다.

- canonical_id 생성 규칙 테스트
- source path, commit, hash 정규화 테스트
- generated block updater가 human notes를 보존하는지 테스트
- secret/PII 패턴 탐지 시 wiki write가 막히는지 테스트
- `tobe` fixture 기준 SP inventory 생성 테스트
- `API -> Repository -> SP` 후보 edge 생성 테스트
- `SP -> Table` read/write 후보 edge 생성 테스트
- dirty source repo가 canonical 승격되지 않는지 테스트
- YouTrack 티켓 입력이 `wiki/tickets/{ticket-id}.md`와 work graph로 연결되는지 테스트
- Graphify trigger가 queue item만 만들고 canonical graph를 수정하지 않는지 테스트
- 같은 source hash의 Graphify trigger가 debounce되는지 테스트
- Graphify sidecar 결과가 DEV2 graph에 직접 merge되지 않는지 테스트
- Graphify adapter가 `canonical_id`, source path/hash, confidence, review_state를 채우는지 테스트
- Graphify `INFERRED`/`AMBIGUOUS` edge가 `needs-review` 후보로만 남는지 테스트
- Graphify 산출물이 generated 경로 밖 human notes를 수정하지 않는지 테스트
- docs/images/PDF semantic extraction 전에 redaction gate가 동작하는지 테스트

### NOT in Scope

MVP에서는 다음을 하지 않는다.

- 모든 서비스 완전 분석
- Hermes Agent 운영 도입
- 자동 YouTrack 정식 티켓 생성
- 코드 변경 또는 DB/SP 변경
- 서비스 repo의 `docs/claudedocs` 삭제
- canonical 도메인 지식 자동 승격
- Graphify 결과의 canonical graph 직접 merge
- Graphify hook/installer가 AGENTS.md 또는 CLAUDE.md를 자동 수정하는 방식
- git hook에서 Graphify full pipeline을 직접 실행하는 방식

### What Already Exists

- `team2`의 정책, 서비스 카탈로그, 스프린트/주간업무/OKR 하네스
- `tobe-db-script`, `max-db-script`의 DB object git 관리 구조
- `max-msa`의 Ralph Loop table/SP/domain/completeness pass 패턴
- YouTrack Issue와 YouTrack KB
- Graphify CLI 설치본. 다만 sidecar 파일럿 전 최신 버전과 출력 schema를 별도 run directory에서 검증해야 한다.

### Engineering Score

현재 설계 점수는 8/10이다. 방향은 맞지만, 구현 전 `dev2-knowledge` skeleton, graph schema, generated block updater, redaction gate가 없으면 운영 중 신뢰도가 빠르게 떨어질 수 있다. 이 4가지를 MVP 1차 작업으로 고정한다.

### A안 확정: AI 분석 레이어와 사람 이해 레이어 분리

MVP 다음 단계는 분석 범위를 넓히기 전에 구조를 먼저 고정한다. 목표는 AI가 안정적으로 읽고 갱신할 수 있는 엄격한 데이터 계층과, 사람이 30초 안에 맥락을 파악할 수 있는 마크다운 계층을 분리하는 것이다.

```text
                    ┌──────────────────────────────┐
                    │ registry/*.yaml              │
                    │ 사람이 관리하는 입력 계약     │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
┌──────────────────┐      ┌──────────────────────────────┐
│ service/db repos │ ───▶ │ graph/*.json                 │
│ read-only source │      │ AI가 읽는 정규화된 사실 계층  │
└──────────────────┘      └──────────────┬───────────────┘
                                          │
                                          ▼
                                 ┌──────────────────┐
                                 │ wiki/**/*.md     │
                                 │ 사람이 읽는 해석 │
                                 └──────────────────┘
```

#### Layer 1. AI Analysis Layer

AI가 우선 읽는 계층이다. 이 계층은 모호한 문장보다 정규화된 필드를 우선한다.

| 위치 | 역할 | 규칙 |
|------|------|------|
| `registry/*.yaml` | 서비스, source, scan pattern 입력 | 사람 편집 가능, 자동화는 읽기 우선 |
| `registry/schemas/*.schema.json` | graph/frontmatter/generated block 계약 | 자동화와 lint의 기준 |
| `graph/*.json` | 정규화된 node/edge snapshot | 자동 생성, 사람이 직접 편집하지 않음 |
| `graph/events/*.jsonl` | 실행 이력, scan event | append-only |
| `wiki/**/*.md` frontmatter | graph와 사람 문서 연결 | `canonical_id` 필수 |

AI layer 필수 필드:

```yaml
canonical_id: sp:tobe:tobe:dbo:tobeuser_getcontextinfo
type: stored-procedure-contract
status: analyzed
review_state: needs-review
sources:
  - repo: /path/to/source
    path: databases/tobe/StoredProcedures/TobeUser_GetContextInfo.sql
    commit: 2a7d661
    dirty: true
    source_hash: sha256...
```

#### Layer 2. Human Wiki Layer

사람이 우선 읽는 계층이다. 파일명과 H1, 첫 화면 요약, 관계 링크가 중요하다.

문서는 항상 아래 순서를 따른다.

```markdown
---
type: stored-procedure-contract
title: dbo.TobeUser_GetContextInfo
canonical_id: sp:tobe:tobe:dbo:tobeuser_getcontextinfo
status: analyzed
review_state: needs-review
---

# dbo.TobeUser_GetContextInfo

## Summary

30초 안에 읽는 요약. 이 문서가 무엇이고, 왜 중요한지 설명한다.

## Quick Links

- Service:
- Domain:
- Ticket:
- Source:

<!-- GENERATED:START id=contract-summary schema=generated-block/v1 -->
자동 생성된 관계, source hash, caller/callee, stale 상태.
<!-- GENERATED:END -->

## Confirmed

source로 확인된 사실만 쓴다.

## Inferred

근거 기반 추론을 쓴다. 단정하지 않는다.

## Needs Review

사람 판단이 필요한 내용을 쓴다.

## Actions

티켓화, 추가 분석, 검증 후보를 쓴다.
```

#### 공통 연결 규칙

- AI는 `canonical_id`를 기준으로 graph node와 wiki page를 연결한다.
- 사람은 `Summary`, `Quick Links`, `Confirmed`, `Needs Review`, `Actions`를 기준으로 읽는다.
- generated block은 graph의 projection일 뿐이고, canonical 판단은 `review_state`와 human section에서 한다.
- source가 dirty이면 graph node는 생성할 수 있지만 `review_state: needs-review`를 유지한다.
- 같은 `canonical_id`가 2개 이상 발견되면 새 문서를 만들지 않고 `unresolved-queue`에 merge 후보를 등록한다.

#### MVP에서 먼저 고정할 산출물

| 산출물 | 목적 |
|--------|------|
| `registry/schemas/graph.schema.json` | graph node/edge 최소 계약 |
| `registry/schemas/wiki-frontmatter.schema.json` | wiki 문서 frontmatter 최소 계약 |
| `registry/schemas/generated-block.schema.json` | generated block metadata 계약 |
| `registry/schemas/lint-report.schema.json` | lint 결과물 계약 |
| `wiki/guides/ai-human-readable-structure.md` | 사람/AI가 같은 문서를 다르게 읽는 기준 |
| `wiki/guides/generated-block-policy.md` | 자동 갱신 가능 영역과 금지 영역 |
| `wiki/guides/lint-wiki-spec.md` | lint_wiki.py 검사 항목, severity, exit code 명세 |
| `wiki/guides/projection-policy.md` | graph를 markdown generated block으로 투영하는 기준 |
| `wiki/decisions/adr-0002-ai-human-layered-wiki.md` | 구조 결정 기록 |

## MVP 범위

MVP는 전체 자동화 플랫폼이 아니라 `System Discovery Seed + Ticket Execution MVP`를 검증하는 범위로 제한한다.

1. `registry/services/*.yaml`로 서비스 등록 구조를 만든다.
2. `registry/taxonomy.yaml`에 문서 유형, 상태, naming rule을 정의한다.
3. `graph/discovery-queue.json`, `graph/proposal-queue.json`, `wiki/tasks/discovery-queue.md`, `wiki/tasks/action-register.md`를 만든다.
4. `tobe`를 첫 대상 서비스로 선택한다.
5. 선택한 서비스의 API/SP/Table wide inventory를 생성한다.
6. API → SP, SP → Table 1차 관계를 만든다.
7. 기존 `docs`, `claudedocs` inventory를 생성하고 완료 티켓/도메인/프로젝트 후보로 분류한다.
8. 완료된 티켓 1개, 진행 중 티켓 1개, 신규 후보 티켓 1개를 기준으로 `wiki/tickets/{ticket-id}.md` 분석 문서를 만든다.
9. 관련 API/SP/Table/KB/과거 문서를 연결한다.
10. 스프린트/주간업무/OKR 반영안을 생성한다.
11. 티켓 분석 중 발견한 누락을 discovery queue로 되돌린다.
12. 사람 검토 후 proposal을 YouTrack 티켓 또는 실행 작업으로 승격한다.

## 완료 기준

- 서비스 추가가 registry 설정 추가로 가능하다.
- 선택한 첫 서비스의 API/SP/Table inventory가 생성된다.
- 최소 1개 도메인에서 API → SP → Table 관계가 위키와 graph에 연결된다.
- 티켓 분석 시 과거 처리 사례, 관련 KB, API/SP/Table, 도메인이 연결된다.
- 위키 문서가 source path, source commit 또는 KB ID를 가진다.
- generated 영역과 human 영역이 분리된다.
- 스프린트/주간업무/OKR 반영 기준이 하네스 정책과 일치한다.
- Codex와 Claude Code가 같은 registry, graph, scripts를 사용한다.
- discovery queue와 proposal queue가 구분된다.
- proposal queue가 사람 검토 가능한 형태로 유지된다.

## 성공 지표

MVP가 성공했는지는 산출물 개수가 아니라 실제 운영 시간이 줄어드는지로 판단한다.

| 지표 | 목표 |
|------|------|
| 티켓 1개 초기 분석 시간 | 30분 이상 단축 |
| 유사 과거 티켓/문서 탐색 | 티켓당 2개 이상 후보 제시 |
| API/SP/Table 연결 정확도 | 사람 검토 기준 핵심 관계 누락 없음 |
| 주간업무 반영 문구 | 수정 후 바로 사용 가능 |
| discovery queue 품질 | 실행 가능한 항목 비율 70% 이상 |
| proposal 채택률 | 초기에는 낮아도 되며, 노이즈가 관리 가능한 수준이어야 함 |
| stale 문서 감지 | 원본 변경 시 관련 wiki 문서 stale 표시 가능 |
