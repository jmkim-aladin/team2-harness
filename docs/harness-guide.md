# 하네스 운영 가이드

## 하네스란?

**하네스 = 마크다운 문서들 + 템플릿 + 체크리스트 + 자동화 규칙 + 그걸 계속 갱신하는 운영 방식**

단순 문서 모음이 아니라, 실제 개발/운영/리뷰/배포 흐름에 연결되어 있어야 합니다.

### 하네스가 아닌 것
- 한 번 써놓고 안 보는 문서
- 너무 추상적이라 실제 작업에 도움 안 되는 규칙집
- 코드와 따로 놀아서 금방 낡는 위키

### 하네스인 것
- 작업 시작 전에 반드시 참고하는 문서
- PR/배포 체크리스트와 연결된 문서
- 장애/변경 후 계속 수정되는 문서
- AI와 사람 둘 다 같은 기준으로 쓰는 문서

## 팀원 초기 셋업

상세 가이드: [setup-guide.md](./setup-guide.md)

```bash
git clone https://github.com/AladinCommunication/team2.git
cd team2 && ./scripts/setup.sh
```

셋업 후에는 **어떤 서비스 레포에서든** Claude Code를 실행하면 팀 스킬이 자동으로 사용 가능합니다.
team2 레포에서 실행할 필요 없이, 평소처럼 각 서비스 레포에서 작업하면 됩니다.

---

## 2계층 구조

### 팀 공통 하네스 (이 레포)
- **역할**: 정책, 판단 기준, 기본값
- **관리**: 팀장 + 시니어 중심, 변경은 신중하게
- **위치**: `team2/policies/`

### 서비스별 하네스 (각 서비스 레포)
- **역할**: 현장 매뉴얼, 실행 가이드
- **관리**: 각 서비스 owner, PR과 같이 수정
- **위치**: 각 서비스 레포 루트

## 하네스의 3가지 역할

### 1. 작업 전 — 판단 기준
- 작업 유형 분류 (기능/버그/핫픽스/리팩토링/현대화)
- DB/SP 변경 승인 필요 여부
- 서비스 경계를 넘는지 확인

### 2. 작업 중 — 실행 가이드
- 빌드/실행 방법
- 금지 영역 확인
- 테스트 방법
- 배포/롤백 절차

### 3. 작업 후 — 학습 반영
- 새로 알게 된 운영 지식 기록
- 장애/위험 포인트 추가
- 금지 패턴 갱신

운영 지식 위키 설계는 [operational-knowledge-wiki.md](./designs/operational-knowledge-wiki.md)를 따른다. 이 위키는 System Discovery Loop와 Ticket Execution Loop를 분리하여 전체 서비스 분석과 티켓 기반 실행을 같은 graph/wiki에 연결한다.

운영 지식 위키의 Obsidian vault 경로는 `/Users/user/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2`로 둔다.

AI 도구는 하네스 문서를 갱신하거나 티켓 초안을 작성할 수 있지만, YouTrack 티켓/Task 생성, 티켓 상태/필드 변경, YouTrack KB 생성/수정/삭제/이동, 커밋/푸시/머지 전에는 반드시 사용자에게 확인한다.

가이드/정책/스킬은 팀 하네스에 저장하고, 서비스 분석 결과와 Querybook은 로컬 Obsidian 운영 지식 위키에 저장한다. Ralph Loop로 도메인 지식을 고도화할 때는 [ralph-loop-domain-knowledge-guide.md](./ralph-loop-domain-knowledge-guide.md)를 따른다.
운영 지식 위키 산출물을 레거시 현대화와 DB 분리 판단에 사용할 때는 [legacy-modernization-db-separation-analysis-guide.md](./legacy-modernization-db-separation-analysis-guide.md)의 readiness level과 rubric을 함께 적용한다.
IDC DB 운영 안정화와 AWS 전환을 위한 batch/SP/table/query 진단은 [db-migration-cdc-assessment-guide.md](./db-migration-cdc-assessment-guide.md)를 따른다.
다른 서비스로 Ralph Loop를 확장할 때는 [ralph-loop-service-expansion-guide.md](./ralph-loop-service-expansion-guide.md)를 따른다.

### 문서 언어와 제목

팀 하네스와 로컬 Obsidian 운영 지식 위키의 문서는 한국어로 작성한다. 코드, API, SP, Table, CDC, DTO, Querybook 같은 기술 용어는 영어를 허용하지만, H1 제목과 `title` frontmatter는 한국어 명사구가 중심이어야 한다.

서비스별 문서는 폴더 구조와 별개로 제목에서 서비스가 바로 보이도록 한다. 파일명은 `tobe-...`, `web-aladin-...`처럼 `service_id` 접두어를 유지하고, H1/title은 `투비 ...`, `알라딘 웹 ...`처럼 한글 서비스 표시명으로 시작한다. 전체 기준은 [wiki-document-language-and-title-policy.md](../policies/wiki-document-language-and-title-policy.md)를 따른다.

### 운영 지식 위키 탐색과 Graphify sidecar

서비스/API/SP/Table 관계를 탐색할 때는 로컬 Obsidian 운영 지식 위키의 graph를 먼저 확인한다.

```text
/Users/user/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/
  graph/contract-graph.json
  graph/source-inventory.json
  graph/unresolved-queue.json
  graph/generated/graphify/{service_id}/{run_id}/GRAPH_REPORT.md
```

Graphify sidecar 산출물이 있으면 `GRAPH_REPORT.md`의 god node, surprise edge, suggested questions를 먼저 참고한다. 단, Graphify 결과는 후보 지식이며 source path/hash, DEV2 graph, 사람 검토 없이 canonical 사실로 쓰지 않는다.

Obsidian에서 위키처럼 탐색할 때는 자동 생성 인덱스와 Related Links 블록을 진입점으로 쓴다.

```text
wiki/indexes/services.md
wiki/indexes/domains.md
wiki/indexes/graphify.md
```

링크 유지는 로컬 위키의 `generate_wiki.py`가 담당한다. 문서 파일명을 바꾸거나 새 서비스/도메인/인벤토리 문서를 추가한 뒤에는 `python3 scripts/generate_wiki.py`와 `python3 scripts/lint_wiki.py`를 실행해 wikilink, index, related-links block을 확인한다.

Graphify sidecar가 없거나 stale이면 직접 full pipeline을 실행하지 않고 queue에 등록한다.

```bash
cd "/Users/user/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
python3 scripts/generate_wiki.py
python3 scripts/lint_wiki.py
python3 scripts/plan_graphify_runs.py
python3 scripts/enqueue_graphify_trigger.py --service {service_id} --trigger ticket-graph-missing --reason "{탐색 중 graph 누락 사유}"
```

자동 최신화는 다음 기준을 따른다.

| Trigger | 처리 |
|---------|------|
| `scan_sources.py` 이후 source commit/hash 변경 | `plan_graphify_runs.py`가 `source-hash-changed` 후보 생성 |
| 새 `registry/services/*.yaml` | `service-registry-added` 후보 생성 |
| docs/claudedocs 변경 | `docs-changed` 후보 생성, semantic extraction은 gated |
| unresolved queue 급증 | `unresolved-spike` 후보 생성 |
| 티켓/스킬 분석 중 graph 누락 | `enqueue_graphify_trigger.py --trigger ticket-graph-missing`로 후보 생성 |
| 동기화/주기 실행 이후 | `python3 scripts/run_all.py --run-graphify`로 eligible 항목만 처리 |

git hook은 Graphify full pipeline을 직접 실행하지 않는다. hook을 붙일 경우 queue item 생성까지만 허용한다.

## 실제 작업 흐름

```
요청/이슈 발생
↓
YouTrack 티켓 생성 (5W1H)
↓
팀 하네스로 작업 유형/승인 기준 확인
↓
대상 서비스의 서비스 하네스 확인
↓
영향도 분석
↓
브랜치 생성
↓
구현/리팩토링/문서 수정
↓
테스트/스모크/체크리스트 수행
↓
PR 생성 (체크리스트 포함)
↓
리뷰/승인
↓
배포
↓
배포 후 검증 및 하네스 갱신
```

## 서비스 하네스 적용 방법

### 기존 서비스 (레거시)
1. `catalog/`에 서비스 프로파일 작성 (`.yaml`)
2. 서비스 분석 → 현대화 트랙 분류 (Observe/Wrap/Extract/Freeze)
3. `templates/service-harness/`의 템플릿을 복사하여 서비스 레포에 적용
4. 실제 정보로 템플릿 채우기
5. PR로 리뷰 후 머지

### 신규 서비스
1. `templates/service-harness/`의 템플릿을 복사하여 서비스 레포에 적용
2. 신규 서비스 정보로 템플릿 채우기
3. 서비스 개발하면서 계속 갱신

## 하네스 갱신 트리거

| 상황 | 갱신 대상 |
|------|-----------|
| 신규 외부 연동 추가 | AGENTS.md |
| 주요 API 경로 변경 | AGENTS.md |
| 배포/롤백 절차 변경 | RUNBOOK.md |
| DB/SP 영향 범위 변경 | LEGACY_BOUNDARY.md |
| 서비스 책임 이동 | service-manifest.yaml |
| 장애/위험 포인트 발견 | AGENTS.md 주의사항 |
| 현대화 진행 상태 변경 | modernization-plan.md |

## 스킬 목록

### ad: (공통 업무)

| 스킬 | 설명 | 상태 |
|------|------|------|
| `/ad:ticket` | YouTrack 티켓 생성 (5W1H) | 구현됨 |
| `/ad:ticket-split` | 2일 초과 이슈 분할 | 미구현 |
| `/ad:time-log` | 소요시간 기록 | 미구현 |
| `/ad:code-review` | GitHub PR 코드 리뷰 (팀 체크리스트 기반) | 구현됨 |
| `/ad:status-update` | 티켓 상태 전환 | 미구현 |
| `/ad:daily-report` | 일일 작업 요약 | 미구현 |
| `/ad:sprint-plan` | 스프린트 계획 보조 | 미구현 |

### ad:team2 (팀 운영)

| 스킬 | 설명 | 상태 |
|------|------|------|
| `/ad:team2-kb-read` | YouTrack KB 문서 조회/검색 | 구현됨 |
| `/ad:team2-kb-list` | YouTrack KB 문서 트리 조회 | 구현됨 |
| `/ad:team2-kb-sync` | KB 변경 시 하네스 정책 동기화 | 구현됨 |
| `/ad:team2-onboard` | 신규 서비스 하네스 생성 | 미구현 |
| `/ad:team2-catalog` | 서비스 카탈로그 조회/갱신 | 미구현 |
| `/ad:team2-harness-check` | 서비스 하네스 완성도 점검 | 미구현 |
| `/ad:team2-members` | 팀원/담당 서비스 조회 | 미구현 |
