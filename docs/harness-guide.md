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
- 공통 서비스(알라딘 인증, 뉴빌링 등) 영향 여부 확인

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
Hermes, gbrain, Codex/Claude Code를 함께 쓰는 자동 prep, decision board, 야간 도메인 분석 루프는 [agentic-ticket-domain-loop-guide.md](./agentic-ticket-domain-loop-guide.md)를 따른다.
Hermes에 연결된 기존 Discord bot을 control surface로 쓰는 역할 프로필 orchestration은 [discord-agent-orchestration-guide.md](./discord-agent-orchestration-guide.md)와 `configs/discord-agent-profiles.yaml`을 따른다. Claude Code와 Codex는 모두 같은 team2 `tools/` 명령과 vault 산출물 계약을 사용한다.

운영 지식 위키의 Obsidian vault 경로는 `/Users/user/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2`로 둔다.

AI 도구는 하네스 문서를 갱신하거나 티켓 초안을 작성할 수 있지만, YouTrack 티켓/Task 생성, 티켓 상태/필드 변경, YouTrack KB 생성/수정/삭제/이동, 커밋/푸시/머지 전에는 반드시 사용자에게 확인한다.

가이드/정책/스킬은 팀 하네스에 저장하고, 서비스 분석 결과와 Querybook은 로컬 Obsidian 운영 지식 위키에 저장한다. Ralph Loop로 도메인 지식을 고도화할 때는 [ralph-loop-domain-knowledge-guide.md](./ralph-loop-domain-knowledge-guide.md)를 따른다.
운영 지식 위키 산출물을 레거시 현대화와 DB 분리 판단에 사용할 때는 [legacy-modernization-db-separation-analysis-guide.md](./legacy-modernization-db-separation-analysis-guide.md)의 readiness level과 rubric을 함께 적용한다.
IDC DB 운영 안정화와 AWS 전환을 위한 batch/SP/table/query 진단은 [db-migration-cdc-assessment-guide.md](./db-migration-cdc-assessment-guide.md)를 따른다.
다른 서비스로 Ralph Loop를 확장할 때는 [ralph-loop-service-expansion-guide.md](./ralph-loop-service-expansion-guide.md)를 따른다.
팀 소유 서비스와 별개로 알라딘 인증, 뉴빌링 같은 공통 서비스 영향은 [공통 서비스 정책](../policies/common-service-policy.md)과 [`catalog/common-services/registry.yaml`](../catalog/common-services/registry.yaml)을 따른다. 티켓 준비와 설계 분석은 대상 팀 서비스의 `catalog/{service_id}.yaml`을 먼저 읽고, 로그인/권한/회원 식별/결제/정산/구독/공유 API가 걸리면 공통 서비스 registry를 함께 확인한다. 신규 빌링, 결제, 정산, 구독, 빌링키 기능은 [`catalog/common-services/new-billing.yaml`](../catalog/common-services/new-billing.yaml)의 뉴빌링 API 경계를 먼저 본다.

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

링크와 projection 유지는 팀 하네스의 `tools/generate_vault_indexes.py`와 `tools/lint_vault.py`가 담당한다. 문서 파일명을 바꾸거나 새 서비스/도메인/인벤토리 문서를 추가한 뒤에는 아래 명령으로 index, related-links block, frontmatter를 확인한다.

Graphify sidecar가 없거나 stale이면 직접 full pipeline을 실행하지 않는다. Graphify queue 도구가 연결된 환경에서는 queue에 등록하고, 없으면 티켓 노트나 서비스 unresolved evidence에 `ticket-graph-missing` 후보로 남긴다.

```bash
TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"
LOCAL_WIKI_PATH="${LOCAL_WIKI_PATH:-/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2}"

python3 "$TEAM2_HARNESS_PATH/tools/generate_vault_indexes.py" --vault "$LOCAL_WIKI_PATH"
python3 "$TEAM2_HARNESS_PATH/tools/lint_vault.py" --vault "$LOCAL_WIKI_PATH" --all
```

Hermes/Discord decision board projection은 아래 명령으로 갱신한다.

```bash
python3 "$TEAM2_HARNESS_PATH/tools/generate_decision_board.py" --vault "$LOCAL_WIKI_PATH" --apply
python3 "$TEAM2_HARNESS_PATH/tools/generate_discord_orchestrator_payload.py" --vault "$LOCAL_WIKI_PATH" --apply
```

Claude Code와 Codex에서는 위 두 명령 대신 공통 진입점 `/ad:work-board` 또는 `$ad-work-board`를 사용한다.

```bash
python3 "$TEAM2_HARNESS_PATH/tools/run_work_board.py" --vault "$LOCAL_WIKI_PATH" --apply
```

Hermes가 dispatch request를 처리한 뒤 남기는 ack 계약은 `configs/hermes-discord-consumer.yaml`과 `tools/ack_hermes_dispatch.py`를 따른다.
Hermes runtime에서는 아래 knowledge cycle runner를 주기 실행 단위로 사용한다. 이 명령은 harness link, vault relation/index, board projection, dispatch request, pending batch, outbox, Hermes Kanban sync, board action queue import, desktop decision cockpit, cycle status를 갱신한다. Discord API는 직접 호출하지 않는다.

```bash
python3 "$TEAM2_HARNESS_PATH/tools/run_team2_knowledge_cycle.py" --vault "$LOCAL_WIKI_PATH" --apply
```

컴퓨터 앞 control pane에서는 같은 작업을 짧게 실행한다.

```bash
team2-agent cycle
team2-agent board
team2-agent cockpit
```

herdr를 사용하는 로컬 작업실에서는 `team2-agent`가 Hermes/wiki 상태와 herdr 실행 표면을 연결한다. `herdr open`은 `team2-orchestration` space가 없으면 새로 만들어 `global-orchestrator`를 띄우고, 이미 있으면 빈 slot에 맞춰 새 tab으로 추가 instance(`global-orchestrator-2`/`-3`, 최대 3개)를 띄운 뒤 herdr session에 attach한다. 3개가 모두 떠 있으면 첫 instance를 focus한다. `worker`/`ask`/`route`/`refresh-global` 등 이름 기반 명령은 첫 instance(`global-orchestrator`)를 대상으로 한다. 기본 agent engine은 codex이며, Claude Code로 시작하려면 `--engine claude`를 붙인다. `open` 때 선택한 engine은 orchestrator prompt의 후속 `worker`/`tickets`/`work`/`role` 명령 예시에 반영된다. 서비스 작업은 서비스별 space, 티켓/작업별 tab, 임시 role agent pane으로 나눈다. Hermes board와 desktop cockpit은 상시 패널이 아니라 orchestrator가 필요할 때 조회하는 내부 상태 도구다. 이미 herdr 안에서 실행 중이거나 attach가 필요 없으면 `--no-attach`를 붙인다. herdr는 원장이 아니므로 상태 판단은 Hermes Board와 vault note를 기준으로 한다.

```bash
team2-agent herdr doctor
team2-agent herdr install-hooks
team2-agent herdr open
team2-agent herdr open --engine claude
team2-agent herdr sync
team2-agent herdr tickets --engine claude --service max --concurrency 4 DEV2-6509 DEV2-6510
team2-agent herdr route --engine claude --service max DEV2-6509 "후속 지시"
team2-agent herdr collect DEV2-6509
team2-agent herdr close --service max DEV2-6509
team2-agent herdr worker --engine claude orch-worker-3 "추가 분석 작업"
team2-agent herdr role --engine claude --service max DEV2-6509 analyst "요구사항과 코드 진입점 분석"
```

사용자는 `global-orchestrator` pane에 자연어로 지시한다. 오래 걸리거나 병렬 처리할 비서비스 작업은 orchestrator가 `team2-agent herdr worker --engine {codex|claude} orch-worker-N "작업"`으로 작업 단위 worker를 동적으로 띄운다. instruction이 있는 worker는 결과를 읽은 뒤 자동으로 pane을 닫는다. DEV2 티켓 묶음은 orchestrator가 서비스 판정에 필요한 최소 정보만 확인한 뒤 `team2-agent herdr tickets --engine {codex|claude} --service {service}`로 서비스 space 안에 ticket tab을 만든다. 티켓 상세 정리, 분석, 상태 판단은 각 tab의 `ticket-lead`가 담당하며, `/ad:work-prep` 기준으로 필요한 role agent만 `team2-agent herdr role --engine {codex|claude} --service {service}`로 띄운다. 이미 생성된 티켓/작업에 후속 지시를 보낼 때는 `team2-agent herdr route --engine {codex|claude} --service {service} {DEV2-1234|work-id} "후속 지시"`를 사용하고, 결과 확인은 `team2-agent herdr collect {DEV2-1234|work-id}`로 한다. 종료할 때는 `team2-agent herdr close --service {service} {DEV2-1234|work-id}`로 tab 안의 lead/role pane을 함께 닫는다. 기본은 working/blocked pane이 있으면 닫지 않고, 강제 종료는 `--force`를 명시한다. `team2-agent board`, `cockpit`, `brief`, `ask`, `delegate`, `decide`, `done` 등은 orchestrator/worker/ticket-lead가 내부 도구로 사용한다.

board projection과 dispatch request만 갱신할 때는 아래 runner를 사용한다. 기존 ack를 읽어 중복 전송을 막은 pending batch를 만든다.

```bash
python3 "$TEAM2_HARNESS_PATH/tools/run_hermes_dispatch_cycle.py" --vault "$LOCAL_WIKI_PATH" --apply --default-batch-output --default-outbox
```

Hermes Kanban 화면은 아래 동기화 도구가 관리한다. source card가 새로 생기면 `team2` 보드에 task를 만들고, 사람 결정/검토 대기이므로 `blocked` 상태로 유지한다. 생성된 task 본문에는 `Source of truth: wiki note`, `Projection: Hermes task`, `Vault path`가 포함된다. 이미 존재하던 task에는 `TEAM2-SOURCE-LINK` 댓글을 한 번 남겨 같은 연결을 보강한다. source card가 projection에서 사라지면 기존 task를 `done`으로 이동한다. task만 `done`으로 바꾸지 말고 먼저 wiki note의 `decision_status`, `ticket_status`, `review_state`를 정리해야 한다.

```bash
python3 "$TEAM2_HARNESS_PATH/tools/sync_hermes_kanban.py" --vault "$LOCAL_WIKI_PATH" --apply
```

컴퓨터 앞에서는 Discord 대신 desktop decision cockpit을 주 화면으로 사용한다. Hermes Board 댓글의 `/brief`, `/ask`, `/delegate`, `/decide`, `/approve`, `/revise`, `/split`, `/snooze`, `/done` 지시는 action queue로 수집된다. queue item에는 `source_of_truth`, `vault_path`, `work_id`, `ticket_id`, `service`, `column`을 보존해 실행자가 원장 wiki note로 돌아갈 수 있게 한다.

```bash
python3 "$TEAM2_HARNESS_PATH/tools/import_hermes_board_actions.py" --vault "$LOCAL_WIKI_PATH" --apply
python3 "$TEAM2_HARNESS_PATH/tools/generate_decision_cockpit.py" --vault "$LOCAL_WIKI_PATH" --apply
```

직접 지시는 아래처럼 짧게 남긴다.

```bash
team2-agent brief t_36a47508
team2-agent delegate t_36a47508 planner "추천안과 리스크 정리"
team2-agent decide t_36a47508 "A안으로 결정. 원본 위키에 기록"
```

보낼 payload만 따로 계산할 때는 아래 reference consumer를 사용한다.

```bash
python3 "$TEAM2_HARNESS_PATH/tools/hermes_dispatch_consumer.py" --vault "$LOCAL_WIKI_PATH"
```

Hermes가 기존 Discord bot으로 전송을 완료한 뒤에는 아래처럼 ack를 남긴다.

```bash
python3 "$TEAM2_HARNESS_PATH/tools/run_hermes_discord_adapter.py" --vault "$LOCAL_WIKI_PATH" --adapter-command "/path/to/hermes-discord-send" --apply
python3 "$TEAM2_HARNESS_PATH/tools/hermes_dispatch_consumer.py" --vault "$LOCAL_WIKI_PATH" --mark-dispatched --apply
python3 "$TEAM2_HARNESS_PATH/tools/import_hermes_discord_receipt.py" --vault "$LOCAL_WIKI_PATH" --apply
```

자동 adapter 연동에서는 수동 `--mark-dispatched`보다 `run_hermes_discord_adapter.py`로 delivery receipt를 남기고 `import_hermes_discord_receipt.py`로 ack를 갱신한다. receipt의 실패 행은 pending으로 남기고 다음 cycle에서 재시도한다.

자동 최신화는 다음 기준을 따른다.

| Trigger | 처리 |
|---------|------|
| source commit/hash 변경 | Graphify queue 도구가 있으면 `source-hash-changed` 후보 생성, 없으면 unresolved evidence 기록 |
| 새 `registry/services/*.yaml` | `service-registry-added` 후보 생성 또는 서비스 onboarding 노트에 기록 |
| docs/claudedocs 변경 | `docs-changed` 후보 생성, semantic extraction은 gated |
| unresolved queue 급증 | `unresolved-spike` 후보 생성 |
| 티켓/스킬 분석 중 graph 누락 | `ticket-graph-missing` 후보를 티켓 노트 또는 unresolved evidence에 남김 |
| 동기화/주기 실행 이후 | index/projection/lint는 하네스 `tools/`로 실행하고, Graphify full pipeline은 별도 승인된 환경에서만 처리 |

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
| `/ad:work-board` | Hermes work board projection + dispatch request 갱신 | 구현됨 |
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
