# Ralph Loop 서비스 확장 가이드

## 목적

투비에서 만든 운영 지식 위키 분석 방식을 다음 서비스에도 반복 적용하기 위한 서비스 온보딩 기준이다.

이 문서는 팀 하네스의 가이드다. 실제 분석 결과물은 로컬 Obsidian 운영 지식 위키에 저장한다.

## 기본 원칙

| 원칙 | 설명 |
|---|---|
| 하네스는 기준만 가진다 | 정책, 템플릿, 판단 기준은 `team2`에 둔다 |
| 결과물은 로컬 위키에 둔다 | 도메인 문서, Querybook, execution record, graph는 Obsidian vault에 둔다 |
| 서비스 repo는 read-only | Ralph Loop는 소스와 DB script를 분석만 한다 |
| 외부 write 금지 | YouTrack KB/티켓/상태, 커밋/푸시는 명시 승인 전 금지 |
| Wide → Deep | 전체 inventory를 먼저 만들고 P0 도메인만 deep analysis한다 |
| Graphify는 sidecar | Graphify 결과는 분석 우선순위 후보이며 canonical graph에 직접 merge하지 않는다 |

## 대상 서비스 우선순위

기본 우선순위는 서비스 위험도와 운영 지식 부족도를 함께 본다.

| 우선순위 | 서비스 | 이유 | 첫 pass |
|---:|---|---|---|
| P0 | `max` | 레거시, SP/write 집중, 투비와 유사한 운영 위험 | wide inventory + 주문/정산/회원/콘텐츠 P0 |
| P1 | `naru` | 신규 인증/계정 기반 서비스, 향후 공통 인증 영향 | API/domain/contract 중심 |
| P1 | `bazaar` | 신규 Kotlin/DDD/batch, 오픈마켓 연동 영향 | aggregate/event/batch 중심 |
| P2 | `aasm` | 내부 관리성 신규 서비스, 독립 DB/S3 | config/secret/deploy 중심 |
| P2 | `storefront` | 설계 중, 실행 코드보다 설계/도메인 결정 연결 중요 | design/ticket/domain decision 중심 |

우선순위는 현재 스프린트, 장애, 티켓, 사용자 지시에 따라 바뀔 수 있다.

## 서비스별 Ralph Loop 시작 조건

### 1. 카탈로그 확인

`team2/catalog/{service_id}.yaml`에서 다음을 확인한다.

- `service_id`
- repo 목록
- stack/runtime
- DB 종류
- `shared_db`
- `direct_sp_write`
- modernization track/status
- harness_status

### 2. 로컬 위키 registry 준비

로컬 Obsidian vault:

```text
/Users/user/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2
```

필수 파일:

```text
registry/services/{service_id}.yaml
registry/ralph/prd-{service_id}-full-resource-analysis.json
wiki/services/{service_id}.md
graph/generated/graphify/{service_id}/  # 있으면 탐색 시 참고
```

없으면 팀 하네스 템플릿을 사용해서 만든다.

### 3. Source Boundary 정의

서비스 유형별 기본 source:

| 유형 | 읽기 source |
|---|---|
| legacy .NET + SP | app repo, DB script repo, 기존 docs/claudedocs |
| Spring/Kotlin | app repo, module docs, OpenAPI, migration/schema |
| Next.js | app repo, route/actions, API handlers, DB schema, env docs |
| 설계 중 서비스 | team2 설계 문서, YouTrack ticket metadata, existing architecture docs |

### 4. Graphify sidecar 사전 탐색

새 서비스 온보딩이나 큰 서비스 재분석에서는 Ralph Loop deep analysis 전에 Graphify sidecar 산출물이 있는지 확인한다.

```text
graph/generated/graphify/{service_id}/{run_id}/
  GRAPH_REPORT.md
  graph.json
  metadata.json
```

확인 순서:

1. 최신 `metadata.json`에서 target path, file count, semantic extraction 여부를 확인한다.
2. `GRAPH_REPORT.md`의 god node, surprise edge, suggested questions를 읽고 P0 후보를 좁힌다.
3. Graphify 후보 edge는 source path/hash와 DEV2 `contract-graph.json`으로 재검증한다.
4. sidecar가 없거나 stale이면 직접 실행하지 않고 queue에 등록한다.

```bash
cd "/Users/user/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
python3 scripts/plan_graphify_runs.py
```

티켓/스킬 분석 중 graph 누락을 발견한 경우:

```bash
python3 scripts/enqueue_graphify_trigger.py --service {service_id} --trigger ticket-graph-missing --reason "{누락된 API/SP/Table/도메인}"
```

자동 실행은 `code-ast-local` 항목만 허용한다. docs/images/PDF semantic extraction은 redaction gate와 사용자 승인이 없으면 `gated`로 둔다.

### 5. Pass 선택

| 서비스 유형 | 필수 pass |
|---|---|
| legacy SP | source-inventory, graphify-sidecar, table, sp, api, domain, completeness, wiki-sync |
| DDD/Kotlin | source-inventory, graphify-sidecar, module/aggregate, api, event, domain, completeness, wiki-sync |
| Next.js | source-inventory, graphify-sidecar, route/action, data-access, config/secret, domain, completeness, wiki-sync |
| 설계 문서 중심 | design-pass, graphify-sidecar(semantic gated), decision-pass, domain-pass, ticket-pass, wiki-sync |

## PRD 작성 규칙

각 서비스는 `registry/ralph/prd-{service_id}-full-resource-analysis.json`을 가진다.

PRD는 다음 story를 기본으로 둔다.

1. 전체 source inventory를 갱신한다.
2. Graphify sidecar 후보를 갱신하고, eligible code-ast-local 항목만 실행한다.
3. 계약 그래프를 생성한다.
4. 도메인 후보와 배치/이벤트 후보를 위키에 투영한다.
5. 서비스/도메인/Graphify 인덱스와 Related Links generated block을 갱신한다.
6. P0 도메인을 선정한다.
7. P0 도메인 canonical 후보 문서를 만든다.
8. unresolved/discovery/action queue를 갱신한다.

링크 유지 명령:

```bash
cd "/Users/user/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
python3 scripts/generate_wiki.py
python3 scripts/lint_wiki.py
```

팀 하네스 템플릿:

```text
templates/ralph-loop-service-prd.json
```

## 서비스 확장 요청 템플릿

```text
Ralph Loop로 {service_id} 서비스를 운영 지식 위키에 온보딩해줘.

범위:
- catalog: team2/catalog/{service_id}.yaml
- registry: 로컬 Obsidian registry/services/{service_id}.yaml
- PRD: registry/ralph/prd-{service_id}-full-resource-analysis.json
- write: 로컬 Obsidian 운영 지식 위키만
- external write: YouTrack/commit/push/KB는 승인 전 금지

진행:
1. catalog를 읽고 service registry를 생성/갱신한다.
2. source inventory pass를 실행한다.
3. Graphify sidecar 산출물이 있으면 먼저 참고하고, 없거나 stale이면 trigger queue에 등록한다.
4. contract/domain graph를 생성한다.
5. P0 도메인을 선정한다.
6. P0 도메인 문서와 Querybook을 만든다.
7. lint 결과와 unresolved queue를 보고한다.
```

## 완료 기준

서비스 온보딩은 아래를 만족해야 한다.

- `wiki/services/{service_id}.md` 존재
- `registry/services/{service_id}.yaml` 존재
- `registry/ralph/prd-{service_id}-full-resource-analysis.json` 존재
- inventory 또는 source snapshot 존재
- Graphify sidecar queue가 최신 source hash 기준으로 갱신됨
- P0 도메인 후보가 최소 1개 이상 선정됨
- `wiki/tasks/discovery-queue.md` 또는 `graph/unresolved-queue.json`에 미해결 항목이 남음
- `python3 scripts/lint_wiki.py` 실행 결과 error 0

## 주의

- 다음 서비스 분석을 시작해도 팀 하네스 정책/가이드를 임의로 바꾸지 않는다.
- 서비스 분석 중 발견한 정책 개선점은 로컬 위키 Action Register가 아니라 팀 하네스 개선 후보로 별도 제안한다.
- 분석 결과를 YouTrack KB에 공유하려면 먼저 사용자에게 요약과 공개 범위를 제시하고 승인을 받는다.
- Graphify installer/hook이 AGENTS.md 또는 CLAUDE.md를 자동 수정하게 두지 않는다. DEV2 탐색 규칙은 팀 하네스와 로컬 위키 지침에 수동 반영한다.
