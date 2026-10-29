# 하네스 운영 가이드

## 하네스란?

**하네스 = 마크다운 문서들 + 템플릿 + 체크리스트 + 자동화 규칙 + 그걸 계속 갱신하는 운영 방식**

단순 문서 모음이 아니라, 실제 개발/운영/리뷰/배포 흐름에 연결되어 있어야 한다.

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
git clone https://github.com/jmkim-aladin/team2-harness.git team2
cd team2 && ./scripts/setup.sh
```

셋업 후에는 **어떤 서비스 레포에서든** Claude Code를 실행하면 팀 스킬이 자동으로 사용 가능하다.
team2 레포에서 실행할 필요 없이, 평소처럼 각 서비스 레포에서 작업하면 된다.

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

운영 지식 위키 내부 구조는 vault `wiki/guides/taxonomy.md`를 따른다. 이 위키는 System Discovery Loop와 Ticket Execution Loop를 분리하여 전체 서비스 분석과 티켓 기반 실행을 같은 graph/wiki에 연결한다.
Hermes, gbrain, Codex/Claude Code를 함께 쓰는 자동 prep, decision board, 야간 도메인 분석 루프는 [agentic-ticket-domain-loop-guide.md](./agentic-ticket-domain-loop-guide.md)를 따른다.
Hermes에 연결된 기존 Discord bot을 control surface로 쓰는 역할 프로필 orchestration은 [discord-agent-orchestration-guide.md](./discord-agent-orchestration-guide.md)와 `configs/discord-agent-profiles.yaml`을 따른다. Claude Code와 Codex는 모두 같은 team2 `tools/` 명령과 vault 산출물 계약을 사용한다.

운영 지식 위키의 Obsidian vault 경로는 `$LOCAL_WIKI_PATH` (기본 `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2`)로 둔다.

용어상 "위키"는 이 로컬 Obsidian vault만 뜻한다. YouTrack Articles는 "지식베이스(KB)" 또는 "기술자료"라고 부르며, "위키에 저장" 요청은 로컬 위키 파일 작성으로 처리한다.

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
$LOCAL_WIKI_PATH/
  graph/contract-graph.json
  graph/source-inventory.json
  graph/unresolved-queue.json
  graph/generated/graphify/{service_id}/{run_id}/GRAPH_REPORT.md
```

Graphify sidecar 산출물이 있으면 `GRAPH_REPORT.md`의 god node, surprise edge, suggested questions를 먼저 참고한다. 단, Graphify 결과는 후보 지식이며 source path/hash, DEV2 graph, 사람 검토 없이 canonical 사실로 쓰지 않는다.

Obsidian에서 위키처럼 탐색할 때는 자동 생성 인덱스와 Related Links 블록을 진입점으로 쓴다.

```text
wiki/services/services-index.md
wiki/processes/processes-index.md
wiki/wiki-index.md
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

두 명령을 한 번에 돌리는 공통 진입점은 아래 도구다. 스킬이 아니라 도구 명령이다 — 2026-10-21 `work-board` 스킬을 걷고(90일 사용 0회) 도구·Hermes 경로만 남겼다. 컴퓨터 앞 control pane에서는 `team2-agent board`·`team2-agent cockpit`을 쓴다.

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

### agent 모델 라우팅

herdr가 agent를 시작하면 prompt의 역할명만 쓰지 않고 launch role별 모델을 CLI 인자로 지정한다. Codex는 model과 reasoning effort를, Claude는 native `--model`과 `--effort`를 지정한다. 각 agent는 새 작업의 첫 응답 첫 줄에 `[model] role=<role> model=<model> effort=<effort>`를 출력한다.

| 실행 대상 | launch role |
|---|---|
| global orchestrator, ticket/work lead, planner, architect | `orchestrator` |
| orch-worker, analyst, developer, designer, data | `worker` |
| reviewer | `reviewer` |
| QA | `verifier` |

role별 모델 값은 `tools/team2_agent.py`의 `MODEL_TIERS`(모델 id)·`ROLE_LAUNCH_DEFAULTS`(role→tier·effort)가 SoT다. 문서에 복제하지 않으므로 현재 값은 `team2-agent profiles`로 조회한다.

기본값을 쓰되 업무 난이도가 기본과 다를 때만 `herdr worker`·`herdr role`에 `--tier {fast|workhorse|frontier}`·`--effort`·`--why "사유"`를 붙여 바꾸고, 엔진 중립 tier는 CLI가 `MODEL_TIERS` 표로 엔진별 모델 id로 푼다(tier 표와 규칙도 `team2-agent profiles`가 출력). CLI는 herdr 호출 전에 사유 누락, orchestrator override, reviewer·verifier의 tier 변경·effort 하한 미달, 모델별 effort 상한 초과를 거부하고(exit 2), 통과하면 시작 로그 끝에 `override="<사유>"`를 남긴다. tier는 모델과 effort를 함께 선택하며, 명시 `--effort`가 우선한다. 동일 tier를 지정한 reviewer·verifier는 역할 기본 effort를 유지한다. Claude도 역할 기본값부터 native `--effort`를 받으며, 최상위 모델은 사용자 지정 Opus 5.5로 제한한다.

이 launch role은 새 최상위 thread의 역할이다. Codex thread가 다시 Codex subagent를 생성하면 개인 `~/.codex/config.toml`과 custom agent 설정이 적용된다. Claude engine에는 Codex 전용 `model_reasoning_effort`를 전달하지 않는다.

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

## 작업 플로우 — 업무 상황 지도

**상황당 동사 하나** — 어떤 업무든 아래 지도에서 상황을 찾으면 진입 동사(`ad:*`)가 나온다. 대부분 모델 호출이라 요청에 맞으면 에이전트가 스스로 부르고, 이 절은 사람이 전체를 보는 지도다. 층 설계(동사/엔진/자료)는 [skill-authoring-principles.md](../policies/skill-authoring-principles.md) §구조.

사용자 호출 전용(사이드이펙트, 사람이 시점 결정) 목록은 [skill-authoring-principles.md](../policies/skill-authoring-principles.md) §1 — frontmatter `disable-model-invocation: true`가 SoT이고, 그 절의 블록이 `CLAUDE.md`·`AGENTS.md`에 생성된다. 사본을 여기 두지 않는다 — 세 곳 사본이 드리프트 원인이었다(2026-10-21 감사).

### 4그룹 요약

그룹 이름은 시간 축이다 — 떠올릴 단서는 "지금 티켓 기준 어디냐" 하나다. 그룹의 허브를 먼저 부르면 허브가 나머지를 안내한다.

| 그룹 | 기억 단서 | 허브 동사 |
|---|---|---|
| 1. 구상 (티켓 전) | 아직 티켓이 없다 — 무엇을 만들지 정한다 | `/ad:plan` · `/ad:grill` |
| 2. 개발 (티켓 하나) | 티켓 하나를 끝까지 민다 | `/ad:work-prep` — 출력 "다음 단계"가 강도에 따라 `/ad:eng-review`·`/ad:implement`·`/ad:code-review-self`를 지목 |
| 3. 주기 (팀 운영) | 달력이 부른다 — 주간·월말 | 달력 |
| 4. 상시 (언제든) | 티켓과 무관하게 상황이 부른다 — 지식·이해·협업·운영 DB·하네스 | 상황 |

표기 규칙: 스킬은 **주 소속 1곳**에서만 설명(무엇·언제)하고, 그 행의 `다른 곳에서도` 열에 교차 사용을 적는다. 다른 그룹·단계에는 `→ /ad:x (주 소속: 그룹·단계)` 참조로만 등장한다 — 설명을 복제하면 한쪽이 낡는다. 이름은 바꾸지 않는다([skill-authoring-principles.md](../policies/skill-authoring-principles.md) §동사층 네이밍 규칙). `/ad:` 메뉴에서 그룹이 보이도록 command `description` 맨 앞에 주 소속을 `[그룹·단계]` 태그로 옮겨 적는다 — 주 소속을 옮기면 태그도 같은 PR에서 고친다(`tests/test_work_prep_command_docs.py`가 태그 그룹과 지도 절을 대조).

근거: 2026-10-21 사용자 요청 — 지도·스킬 목록·claude-base 세 곳의 분류가 달라 파편화. 60일 사용 실측: work-prep 171·code-review 135·plan 104회 vs eng-review 0·implement 1회 — 허브가 다음 단계를 안내해야 중간 단계가 쓰인다. 스킬은 여러 단계에 걸치므로 분류는 이름이 아니라 지도의 주 소속+참조로 표현한다.

### 1. 구상 (티켓 전)

```
과제 크기 판정 ┬ 세션 하나에 담김 ─────────────── /ad:grill ──→ /ad:ticket (개발 합류)
               ├ 다세션 계획·미성숙 구상 ───────── /ad:plan ───→ /ad:plan-run (티켓 없는 내부 단계)
               └ 미결 결정 여럿·세션을 넘는 안개 ─ /wayfinder ─→ 길이 보이면 /ad:ticket
```

| 상황 (신호) | 동사·엔진 | 다른 곳에서도 |
|---|---|---|
| 아이디어를 세션 안에서 정리 가능 | `/ad:grill` — `grilling` + `domain-modeling`, frontier 라운드·용어집·결정 기록 → `/ad:ticket`으로 개발 합류 | 개발 — 구현 중 신호 "티켓 전제 깨짐"으로 재진입 |
| 다세션 계획·미성숙 구상을 위키에 | `/ad:plan` — grill 결과를 계획·진행 원장으로 합성 | 개발 — 다세션 개발의 진행 원장 |
| 티켓 없는 내부 계획의 다음 단계 실행 | `/ad:plan-run` — internal milestone 하나를 TDD로 실행하고 status·evidence 기록 | — |
| 미결 결정이 여럿이고 세션을 넘는 안개 과제 | `/wayfinder` — wayfinder 맵(YouTrack 결정 티켓 지도)을 프런티어에서 하나씩 풀고, 길이 보이면 `/ad:ticket`으로 합류. 매핑: [issue-tracker.md](./agents/issue-tracker.md) §Wayfinding operations | — |
| 설계 질문을 코드로 답해야 | `prototype` (모델 호출) | — |
| 문서·API 1차 자료 조사 위임 | `research` (모델 호출, 백그라운드) | — |
| 다른 조직에 결정 질문 | `/to-questionnaire` | — |
| 용어·결정을 기록해야 | `domain-modeling` (모델 호출) | — |
| 계획 노트를 구현 전에 검증 | → `/ad:eng-review` (주 소속: 개발·설계 검증) | |

### 2. 개발 (티켓 하나)

```
/ad:ticket → /ad:work-prep → (/ad:eng-review) → /ad:implement ×슬라이스 → /ad:code-review(-self) → /ad:work-close
 스펙+분할     착수 준비         설계 검증           구현                      리뷰                      종료
                  │
                  └ 강도 판정 ┬ 가벼움  바로 수정 → 직접 확인 → 리뷰
                              ├ 보통    구현 계획(슬라이스 1~2) → 슬라이스 실행 → 리뷰
                              ├ 무거움  구현 계획 → 설계 검증 → 슬라이스마다 검증 명령 → 리뷰
                              └ 위험    무거움 + 반증 검토 → 페르소나 리뷰·안전 가정 입증 → 롤백 트리거

구현 중 엔진: tdd · codebase-design · diagnosing-bugs (막히면 경쟁 가설 조사)
```

`/ad:work-prep`이 허브다. 강도를 판정하고, 개발 Task면 티켓 노트에 구현 계획을 쓰고, 출력 "다음 단계"로 다음 동사를 지목한다. `/ad:implement`는 한 번 호출에 슬라이스 하나를 실행하고 노트를 체크한 뒤 멈춘다 — 다음 슬라이스는 사람이 지시한다.

#### 강도 (ceremony level)

절차의 무게는 걸린 위험에 맞춘다. 시간 축으로 고르고, 위험 축 단서가 하나라도 있으면 크기와 무관하게 위험이다.

| 강도 | 기준 | 절차 |
|---|---|---|
| 가벼움 | 1시간 이내 · 설정 · 문구 | 바로 수정, 직접 확인. 구현 계획 생략 |
| 보통 | 반나절 · 버그 · 작은 기능 | (필요 시 짧은 정렬) → 구현 계획(슬라이스 1~2) → `tdd` → 기본 리뷰 |
| 무거움 | Task 여럿(Feature 단위) · 모호 · 경계 변경 — Task ≤1일이라 크기는 Task 묶음으로 본다 | 전체 플로우, 슬라이스마다 검증 명령, 설계 검증 |
| 위험 | 운영 데이터 · 결제 · 인증 · 개인정보 · 공유 DB 스키마 · 비가역 — **크기와 무관** | 무거움 + 비가역 결정의 반증 검토 + 리뷰에서 페르소나 리뷰·안전 가정 입증 + 롤백 트리거 |

- 판정은 `/ad:work-prep`이 자기 §3(서비스 추정)에서 모은 단서(카탈로그·공통 서비스·DB/SP·결제)로 한다. 애매하면 높은 쪽 — 낮게 잡은 위험은 리뷰에서야 드러난다
- 근거: 2026-10-21 3팩(mattpocock/skills·cursor pstack·addyosmani/agent-skills) 비교 검토 — 절차의 무게는 걸린 위험에 맞춘다. 팀원이 개발 도중 "지금 이걸 쓸 때"라는 신호를 못 받던 문제를 강도와 구현 계획으로 푼다

#### 단계별 도구 명칭

층 규칙은 [skill-authoring-principles.md](../policies/skill-authoring-principles.md) §구조 3층 — 동사·엔진 이름은 바꾸지 않고, 3팩에서 가져와 붙인 것은 자료층 **보조 장치**로 부른다. 원어 leading word는 이 표의 첫 등장에만 병기한다. 이 표가 명칭 SoT다.

| 단계 | 동사 | 엔진 (이름 불변) | 보조 장치 | 쓰는 신호 · 적용 강도 | 다른 곳에서도 |
|---|---|---|---|---|---|
| 정렬 | → `/ad:grill` · `/ad:plan` (주 소속: 구상) | → `grilling` · `domain-modeling` · `wayfinder` (주 소속: 구상) | 과제 크기 판정 | 보통 이상(보통은 짧게). 신호는 §1 구상 | |
| 스펙+분할 | `/ad:ticket` — 5W1H Feature 발행 → Task 분할 | — | — | 전 강도 | 구상 — grill·wayfinder 뒤 합류 |
| 착수 준비 | `/ad:work-prep` — 위키 노트 + 코드 진입점 + 강도 판정 + 구현 계획, "다음 단계" 지목 | — | 강도 판정(ceremony level) · 근거 등급(사실·추론·미확인) · 구현 계획(implementation plan) = 완료 조건(acceptance criteria) · 검증 명령(verification command) · 경계(boundaries — 그냥 진행/먼저 확인/손대지 않음) · 슬라이스(vertical slice) · 구현 중 신호(in-flight signals) | 강도 판정은 전 강도. 구현 계획은 보통 이상 개발 Task. 근거 등급은 레거시 설계 의도·과거 결정을 조사할 때 | 종료 — 위키 노트 종료 반영(`/ad:work-prep DEV2-XXXX 종료`) |
| 설계 검증 | `/ad:eng-review` — 스코프 챌린지 + 아키텍처·품질·테스트·성능 판정 | — | 멱등키 계약(idempotency key contract) · Expand/Contract · 성능 판정 규칙 · 시도 기록(attempt ledger) · 사용 예 선행 설계(usage-first design) · 반증 검토(doubt review) | 무거움 이상. 결제·쿠폰·지급 → 멱등키 계약 / 스키마 rename·drop → Expand/Contract / 최적화 → 성능 판정 규칙·시도 기록 / 새 API·시그니처 → 사용 예 선행 설계 / 위험의 비가역 결정 → 반증 검토, 검토자는 → `/ad:orchestration` Codex peer (주 소속: 상시·협업) — 다른 벤더로는 완료 조건·슬라이스·코드만 보낸다([교차 모델 리뷰 데이터 경계](./code-review/cross-model.md)) | 구상 — `/ad:plan` 계획 노트 검증 |
| 구현 | `/ad:implement` — 구현 계획의 슬라이스 하나 | `implement` · `tdd` · `codebase-design` | 슬라이스 실행(one slice at a time) · 범위 밖 기록 | 보통 이상. 한 번 호출에 슬라이스 하나, 범위 밖 문제는 `진행 메모`에 기록만. 모듈 경계·seam이 애매하면 `codebase-design`. 오래 걸리고 중간 조향이 필요한 위임 → `/ad:orchestration` (주 소속: 상시·협업) | `tdd`: 구상 — `/ad:plan-run` 내부 실행 |
| 리뷰 | `/ad:code-review` — 기준축·스펙축 분리 + 구조 재점검(비차단). `/ad:code-review-self` — 자기 PR, 별도 리뷰어 + 반영·재리뷰 루프(리뷰어 pane → `/ad:orchestration`) | — | 완화 신호 스캔(gate loosening scan) · 교차 모델 리뷰 · 페르소나 리뷰(보안 감사/테스트 엔지니어/데이터 정합성 감사) · 안전 가정 입증(blast radius) · SP 중복 호출 판정 | 전 강도. 완화 신호 스캔은 서비스 코드 PR / SP 중복 호출 판정은 DB 스크립트·SP PR / 페르소나 리뷰·안전 가정 입증은 위험 | `/ad:code-review`: 릴리스 묶음 리뷰([release-bundle.md](./code-review/release-bundle.md)) |
| 종료 | `/ad:work-close` — 소요시간 기록 + Fixed | — | DoD 체크리스트 · 롤백 트리거 | 전 강도. 롤백 트리거는 위험 | — |
| 디버깅 (온램프) | — | `diagnosing-bugs` (모델 호출) | 경쟁 가설 조사(competing hypotheses) | "고장났다"·근본 원인 → 자동 호출. 재현이 안 되거나 막히면 경쟁 가설 조사 — 가설마다 독립 에이전트로 병렬 조사하고 반증된 가설부터 지운다, → `/ad:orchestration` (주 소속: 상시·협업) | 설계 검증 — 성능 회귀 |
| 공통 게이트 | — | — | 승인 응답 판별 | 커밋·푸시·티켓·KB 승인 질문에 포괄 위임("알아서")만 돌아오면 승인이 아니다 | 모든 그룹의 사용자 확인 게이트 |

금지 동의어 — 신호 카드→구현 중 신호 / 수락 기준·인수 조건→완료 조건 / doubt-driven·의심 검토→반증 검토 / 핵심 가정 실행 입증→안전 가정 입증 / 게이트 완화 감지·floor guard→완화 신호 스캔 / 교차 모델 검증·교차검증→교차 모델 리뷰 / 레벨·등급→강도 / 결정 지도·안개 지도→wayfinder 맵. `강도`는 작업 절차의 무게다 — 지시문의 [지시 강도](../policies/instruction-precedence-policy.md)(invariant~example)와 다르다.

보조 장치 SoT와 출처 팩 (Pocock = mattpocock/skills, pstack = cursor pstack, Osmani = addyosmani/agent-skills). 원본 스킬 링크·채택 판정은 [skill-packs-adoption-review.md](./skill-packs-adoption-review.md):

- 착수 준비 → [work-prep-note-template.md](./sprint/work-prep-note-template.md) §구현 계획 기준·§본문 템플릿 — Osmani planning·spec(완료 조건·경계·위험 먼저), pstack create-verification(실제 실행 검증 명령, 빌드 통과는 증거 아님), pstack why(근거 등급)
- 설계 검증 → [review-sections.md](./eng-review/review-sections.md) · [doubt-review.md](./eng-review/doubt-review.md) — Osmani(멱등키 계약·Expand/Contract·성능 판정 규칙·시도 기록·반증 검토), pstack architect(사용 예 선행 설계·비싼 결정만 대안 비교)
- 구현 → [implement.md](../.claude/commands/ad/implement.md) — Osmani incremental
- 리뷰 → [code-review-policy.md](../policies/code-review-policy.md) · [personas.md](./code-review/personas.md) · [cross-model.md](./code-review/cross-model.md) — Osmani(완화 신호 스캔·페르소나 리뷰·SP 중복 호출 판정), pstack blast-radius(안전 가정 입증)
- 종료 → [dod-checklist.md](../templates/dod-checklist.md) · [work-close.md](../.claude/commands/ad/work-close.md) — Osmani shipping(롤백 트리거)
- 디버깅 → `diagnosing-bugs` + `/ad:orchestration` — pstack arena/swarm 컨셉
- 공통 게이트 → [instruction-precedence-policy.md](../policies/instruction-precedence-policy.md) §승인 응답 판별 — Osmani

### 3. 주기 (팀 운영)

| 주기 | 동사 |
|---|---|
| 주간 | `/ad:ticket-schedule`(월요일 오전, 팀장 취합 전 계획 일정 채움) → `/ad:weekly-report` (`planned` 모드 = planned 태그 트리 스냅샷을 위키 meetings에) |
| 월말 | `/ad:sprint-close-check` → `/ad:capacity-plan` → `/ad:weekly-report planned` → `/ad:ticket-schedule {다음 달}`(계획 일정 초안). 뒤 둘은 주간 행이 주 소속 |
| 월별 정적 점검 | [Fortify SSC FPR 일괄 등록 런북](./static-scan-runbook.md#월별-fpr-일괄-등록) — `scripts/upload-fortify-fprs.py --month YYYYMM` dry-run 확인 후 `--apply`; 대상 버전이 이미 있으면 전체 skip |
| 수시 | `/ad:okr`, `/ad:wbs`(WBS·간트 엑셀/HTML 추출), `/ad:granola-sync`. Hermes work board는 스킬이 아니라 도구 명령 — `team2-agent board` 또는 `tools/run_work_board.py --apply`([운영 지식 위키 탐색](#운영-지식-위키-탐색과-graphify-sidecar)) |

### 4. 상시 (언제든)

| 분류 | 상황 (신호) | 동사·엔진 | 다른 곳에서도 |
|---|---|---|---|
| 지식 | 신규 위키 노트 | `/ad:new-note` (배치는 [knowledge-base-policy.md](../policies/knowledge-base-policy.md) 결정 트리) | — |
| 지식 | KB 조회 | `/ad:team2-kb-read` | — |
| 지식 | KB 등록·초안 게시 | `/ad:kb-publish` — 등록할 때 로컬 전용 내용 제외·링크 변환·저장 확인 | — |
| 지식 | 변경·분석 설명서, 아키텍처 한 장 요약 | `/ad:explain` — 변경·분석은 배경→직관→본체→퀴즈, `--tldr`은 아키텍처 one-pager | — |
| 지식 | 기존 저장소 아키텍처 분석 | `/ad:architecture-analysis` | — |
| 브라우저 | 웹 UI를 띄워 개발 중 확인·테스트 | `aside-browser`(Aside) 기본 — 흐름은 `aside exec`, 스크린샷·DOM·콘솔은 `aside repl`. 규칙 SoT: [memory/claude-base.md](../memory/claude-base.md) §브라우저 개발·테스트 | 개발 — 구현 계획의 검증 명령·리뷰 확인 |
| 이해 | 낯선 주제·용어·에러를 빨리 정확히 이해하고 남에게 옮기기 | `/eli5` — 구체 사례 + ASCII 그림 + 옮겨 말하기 대본, 터미널 | — |
| 이해 | 같은 설명을 남에게 보낼 한 장으로 | `/eli5-html` — 자족 HTML 1개 | — |
| 이해 | 낯선 저장소에 처음 투입 | `/eli5-onboard` — 30분 안에 1분 설명 가능 → 업무→용어→흐름→구조 순 단계별 커리큘럼 | — |
| 이해 | 방금 설명이 이해 안 될 때 재설명 | `/wait-what` — 팀 용어집 어휘로 재피치 | — |
| 이해 | 새 기술·개념 다세션 학습 | `/teach` — 현재 디렉토리를 학습 워크스페이스로 | — |
| 협업 | 다른 에이전트와 협업 (Herdr) | `/ad:orchestration` | 개발 — `HERDR_ENV=1`이면 필요할 때 자동 사용, 아니면 서브에이전트로 대체: 설계 검증(위험) 반증 검토를 다른 벤더 peer(Codex)의 fresh context로(완료 조건·슬라이스·코드만 전송 — 교차 모델 리뷰와 같은 데이터 경계) / 디버깅 `diagnosing-bugs`가 막히면 경쟁 가설 조사를 가설별 peer 병렬로 / 리뷰 `/ad:code-review-self` 리뷰어 pane / 구현 중 오래 걸리고 중간 조향이 필요한 위임. 슬라이스 구현은 하나씩 — 병렬 슬라이스는 사용자 지시가 있을 때만 |
| 협업 | DEV2 티켓을 로컬 Paperclip 에이전트에 맡김 (파일럿) | `/ad:paperclip-dispatch` — Inbox 등록(`{ID…}`·`--inbox`), 프로젝트·격리·리뷰→승인 정책 분류(`--project`). 결정적 층 `tools/paperclip_import_ticket.py`, 구성 [templates/paperclip/README.md](../templates/paperclip/README.md) | 개발·착수 준비 — 쇼핑 데이터 추출 요청이면 work-prep 다음 단계로 `--project` 분류 |
| 협업 | 새 하네스·디렉토리·동료에게 인계 | `/handoff` | 단계 경계 — 세션·사람 이동 |
| 협업 | 사람만 할 수 있는 절차 (자격증명·대시보드) | `wizard` (모델 호출) | — |
| 협업 | merge·rebase 충돌 | `resolving-merge-conflicts` (모델 호출) | — |
| 운영 DB | 운영 데이터 추출 SQL | `/ad:data-request` (data-requests-dev2 등록) | 개발·착수 준비 — work-prep 검증 SQL을 노트에 남긴 뒤 등록 |
| 운영 DB | 운영 DB 조회 취소·종료 확인 | `/ad:db-stop` | — |
| 운영 DB | 장애 대응 절차 | [policies/incident-response.md](../policies/incident-response.md) | — |
| 하네스 | 스킬·제약·스택·동기화 점검 | `/ad:harness-optimize` — 주기는 [harness-governance-policy.md](../policies/harness-governance-policy.md). 에이전트가 실수하면 스킬·지도를 고친다 — 사람이 같은 실수를 매번 잡는 대신 다음 세션이 덜 틀린다 | 주기 — 스프린트 마감 주간 감사 |

### 단계 경계

- 정렬 → 분할은 한 창에서 끊지 않는다. 분할이 정렬 사고 위에 서야 한다
- 각 구현 앞에서 `/clear`. 티켓은 자족적이므로 앞 티켓 컨텍스트는 버린다
- 판단은 단계 경계에서만. 순서: 계속 → `/clear` → handoff → 서브에이전트 → `/compact`. `/compact`는 기본값이지 첫 선택이 아니다
- **서브에이전트 판정**: 다음 단계가 조향 없이 돌 수 있으면(스코프 확정 + headless 검증 루프) 새 세션 대신 서브에이전트. 업무별 모델 매트릭스는 [memory/claude-base.md](../memory/claude-base.md) §서브에이전트 위임

> 스킬을 추가·개명·삭제하면 이 지도도 같은 PR에서 갱신한다. 갱신하지 않은 지도는 거짓말을 한다 — `/ad:harness-optimize` 체크리스트 항목.

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

두 경로 모두 [실행 검증 계약 연결](service-harness-setup.md#실행-검증-계약-연결)에 따라 계약을 준비·실행하고 카탈로그에 연결한다. 템플릿 복사만으로 검증 완료로 처리하지 않는다.

## 하네스 갱신 트리거

| 상황 | 갱신 대상 |
|------|-----------|
| 신규 외부 연동 추가 | AGENTS.md |
| 주요 API 경로 변경 | AGENTS.md |
| 배포/롤백 절차 변경 | RUNBOOK.md |
| DB/SP 영향 범위 변경 | LEGACY_BOUNDARY.md |
| 서비스 책임 이동 | service-manifest.yaml |
| 장애/위험 포인트 발견 | 운영 노트·하네스 감사, 코드·검사로 표현하기 어려운 제약만 AGENTS.md에 참조 |
| 실행 명령·기능별 검증 경로 변경 | 서비스 실행 검증 계약·카탈로그의 계약 포인터 |
| 현대화 진행 상태 변경 | modernization-plan.md |
| 금지 패턴 추가 | AGENTS.md 금지 사항 |

## 팀 하네스 유지보수

팀 하네스(이 repo) 자체의 감사 주기·판정 권한·기록 규칙은 [policies/harness-governance-policy.md](../policies/harness-governance-policy.md)가 SoT다. 요약:

- 스프린트 마감 주간 1회 `/ad:harness-optimize` (`스킬`+`제약` 모드), 결과는 [skill-audit-baseline.md](./skill-audit-baseline.md)에 회차 기록
- 실수 발생 시 즉시 보강 (ai-usage-policy §하네스 개선 루프)
- 에이전트는 제안까지 — 지시 강도 하향·등급 변경·스킬 삭제는 사람 판정

## 스킬 목록

분류는 §작업 플로우의 4그룹 하나뿐이다 — 분류 체계가 두 개면 파편화가 재발한다. 존재 여부는 디렉토리가 SoT(`ls .claude/commands/ad/`, Codex alias `ls .codex/skills/`)이고, 한 줄 설명은 각 command 파일 frontmatter `description`이다.

미구현 후보(수요가 생기면 재검토): `/ad:ticket-split`(2일 초과 이슈 분할) · `/ad:time-log`(소요시간 기록 — 현재 `/ad:work-close`가 담당) · `/ad:status-update`(티켓 상태 전환) · `/ad:daily-report`(일일 작업 요약) · `/ad:sprint-plan`(스프린트 계획 보조) · `/ad:team2-onboard`(신규 서비스 하네스 생성) · `/ad:team2-catalog`(서비스 카탈로그 조회/갱신) · `/ad:team2-harness-check`(서비스 하네스 완성도 점검) · `/ad:team2-members`(팀원/담당 서비스 조회)
