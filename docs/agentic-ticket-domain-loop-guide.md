# 에이전트 티켓 실행과 도메인 지식 강화 루프

이 문서는 DEV2 업무를 YouTrack 티켓, 로컬 Obsidian 운영 위키, Hermes, gbrain, Codex/Claude Code로 처리할 때의 운영 기준이다. 목표는 자동화가 결정을 대신하는 것이 아니라, 티켓/분석/프로젝트 고도화 같은 work item 처리와 도메인 지식 축적을 분리해서 사용자가 결정과 승인에 집중하도록 만드는 것이다.

## 핵심 원칙

1. YouTrack은 업무 유입 원장이다.
2. Obsidian vault는 티켓 실행, 회의, 도메인 분석, 검증 기록의 원장이다.
3. team2 하네스는 정책, 템플릿, 승인 게이트의 원장이다.
4. gbrain은 검색, 합성, 중복 탐지 계층이며 원장이 아니다.
5. Hermes board는 vault와 YouTrack 상태의 projection이며 원장이 아니다.
6. 자동 산출물은 기본 `draft`, `inferred`, `needs-review`로 시작한다.
7. `confirmed` 또는 `canonical` 승격은 사람 확인이나 검증 근거가 있을 때만 한다.
8. YouTrack, KB, git, DB write, 배포 변경은 사람 승인 전 실행하지 않는다.

## Work Item 범위

board의 기본 단위는 티켓이 아니라 work item이다.

| Work item | 예시 | 기본 원장 |
|---|---|---|
| Ticket work | DEV2 티켓 구현, 버그, 운영 요청 | YouTrack + vault ticket note |
| Analysis work | 영향 분석, DB/SP 분리 검토, 리스크 분석 | vault analysis note |
| Project improvement | agentic OS, storefront 설계, 하네스 고도화 | vault project/proposal note |
| Domain hardening | 서비스/SP/API/Table 야간 분석 | vault analysis/domain note |
| Review work | 코드리뷰, QA, 디자인 검토 | vault ticket 또는 review note |

YouTrack 티켓이 있으면 `work_id=DEV2-1234`와 `ticket_id=DEV2-1234`를 함께 쓴다. 티켓이 없는 분석/프로젝트 업무는 `canonical_id` 또는 vault path stem을 `work_id`로 사용하고 `ticket_id`는 비운다.

## 전체 구조

```text
낮: Ticket Execution Loop

YouTrack 티켓 유입
  ↓
자동 work-prep
  ↓
vault 티켓 노트 생성/갱신
  ↓
gbrain briefing
  ↓
Hermes board 카드 생성
  ↓
티켓별 agent 작업 셀 진행
  ↓
사용자 결정/승인
  ↓
검증, PR 초안, 완료 기록

밤: Domain Hardening Loop

서비스/SP/API/Table 순회 분석
  ↓
Discovery / Contract / Review 모드 분석
  ↓
draft 분석과 unresolved evidence 저장
  ↓
gbrain sync
  ↓
다음 티켓 prep 품질 향상
```

두 루프는 의도적으로 분리한다. 낮에는 티켓을 끝내기 위한 근거와 결정만 다루고, 밤에는 다음 티켓을 더 빨리 이해하기 위한 도메인 지식을 쌓는다.

## 역할 분리

| 구성 | 역할 | 원장 여부 |
|---|---|---|
| YouTrack | 티켓, 담당자, 상태, 외부 공유 | 원장 |
| Obsidian vault | 티켓 노트, 분석, 결정, 검증 기록 | 원장 |
| team2 하네스 | 정책, 스킬, 템플릿, 승인 게이트 | 원장 |
| gbrain | 하네스와 vault 검색, 합성, 중복 탐지 | 원장 아님 |
| Hermes | 상시 분석, board projection, 반복 작업 | 원장 아님 |
| Codex/Claude Code | 티켓별 구현, 리뷰, 문서 초안 | 원장 아님 |
| herdr | 티켓별 작업 셀과 control pane 실행 표면 | 원장 아님 |

## Ticket Execution Loop

### 1. 티켓 유입

내 담당 DEV2 티켓 또는 명시된 작업 설명이 유입되면 `/ad:work-prep`을 실행한다. 티켓 모드에서는 YouTrack을 읽기 전용으로 조회하고, 자유글 모드에서는 후속 `/ad:ticket` 발의를 권장한다.

자동 허용:

- YouTrack 티켓 읽기
- 서비스 추정과 카탈로그 로드
- 코드 레벨 진입점 후보 탐색
- vault 티켓 노트 생성/갱신
- Daily 아젠다 추가
- herdr/cmux 라벨 변경

자동 금지:

- YouTrack 상태, 필드, 댓글 변경
- 브랜치 생성 또는 체크아웃
- git commit, push, PR 생성
- 운영 DB 조회/변경
- dev DB write

### 2. 티켓 노트

티켓 노트는 작업 셀의 상태 원장이다. 각 agent는 자신의 내부 memory가 아니라 티켓 노트를 기준으로 이어서 작업해야 한다.

필수 상태 필드:

```yaml
type: ticket
ticket_id: DEV2-1234
ticket_status: auto-prep | in-progress | blocked | review-needed | done-candidate | done | backlog
status: draft | canonical
decision_status: none | decision-needed | approval-needed | blocked | review-needed
relation_status: inferred | confirmed
related_services:
  - "[[max]]"
related_tickets: []
related_meetings: []
related_domains: []
```

`status`는 문서 신뢰도이고, `ticket_status`는 작업 흐름이다. 야간 자동 분석 또는 work-prep 직후 노트는 `status: draft`로 둔다. 사람이 검토하고 근거가 충분해졌을 때만 `canonical`로 승격한다.

### 3. 작업 셀

각 티켓은 herdr pane 하나, 가능하면 브랜치 하나, 필요하면 git worktree 하나를 가진다. 같은 브랜치를 여러 agent가 동시에 수정하지 않는다.

작업 셀 기본 지시:

```text
이 pane은 DEV2-1234 전용 작업 셀이다.
항상 vault 티켓 노트를 먼저 읽고 진행한다.
진행 결과는 티켓 노트의 현재 상태, 검증, 완료 기록에 반영한다.
사용자에게 질문할 때는 Decision Packet 형식만 사용한다.
YouTrack, KB, git, DB write, 배포 변경은 승인 전 실행하지 않는다.
```

## Hermes Board

Hermes board는 전체 작업 로그가 아니라 사용자 개입 큐다. board 카드가 너무 많아지면 실패다.

### 컬럼

| 컬럼 | 의미 |
|---|---|
| `Auto-prepped` | work-prep과 티켓 노트 생성이 끝남 |
| `Ready to Run` | agent가 사용자 개입 없이 진행 가능 |
| `Investigating` | agent가 조사 중이며 사용자 개입 불필요 |
| `Decision Needed` | 정책, 우선순위, 방향 선택 필요 |
| `Approval Needed` | git, PR, YouTrack, KB, DB, 배포 승인 필요 |
| `Review Needed` | 구현, 분석, 문서 검토 필요 |
| `Blocked` | 외부 확인 또는 근거 부족으로 중단 |
| `Done Candidate` | 완료 처리 후보이며 검증 확인 필요 |

### 카드 생성 조건

카드는 아래 조건 중 하나를 만족할 때만 생성한다.

- 정책 선택이 필요하다.
- 승인 게이트에 걸렸다.
- 리스크 수용 여부를 사용자가 결정해야 한다.
- 우선순위 충돌이 있다.
- 외부 오너 확인 없이는 진행할 수 없다.
- 완료 처리 전에 검증 확인이 필요하다.

카드로 만들지 않는 항목:

- 단순 진행 상황
- grep 결과나 콜그래프 raw 출력
- agent가 더 조사하면 해결 가능한 질문
- 근거 없는 추론
- 위키에만 남기면 되는 작업 로그

### Decision Packet

사용자에게 올리는 결정 카드는 아래 형식을 따른다.

```markdown
## 결정 필요

- ID: D-001
- 티켓: DEV2-1234
- 서비스: max
- 상태: Decision Needed
- 추천: A안

### 선택지
- A안: {추천안}
- B안: {대안}
- 보류: {보류 시 영향}

### 근거
- 위키: [[dev2-1234]]
- 코드:
- 회의:
- 검증:

### 영향
- 사용자:
- 운영:
- 일정:
- 리스크:

### 필요한 답
A / B / 보류 / 추가 조사
```

사용자는 원자료를 읽지 않고 선택지를 결정할 수 있어야 한다. 근거가 부족하면 `Decision Needed`가 아니라 `Investigating` 또는 `Blocked`로 둔다.

### Projection 생성

Hermes와 기존 Discord bot이 읽는 board projection은 vault frontmatter에서 생성한다.

```bash
TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"
LOCAL_WIKI_PATH="${LOCAL_WIKI_PATH:-/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2}"

python3 "$TEAM2_HARNESS_PATH/tools/generate_decision_board.py" --vault "$LOCAL_WIKI_PATH" --apply
```

Claude Code와 Codex에서는 공통으로 `/ad:work-board apply` 또는 `$ad-work-board apply`를 사용한다.

출력:

- `wiki/projects/agentic-os/hermes-decision-board.md`
- `wiki/projects/agentic-os/hermes-decision-board.json`
- `wiki/projects/agentic-os/hermes-discord-dispatch-request.json`
- `wiki/projects/agentic-os/hermes-discord-dispatch-batch.json` (Hermes runtime용 pending batch)
- `wiki/projects/agentic-os/hermes-discord-outbox/{request_id}/manifest.json` (Hermes bot adapter용 파일 handoff)
- `wiki/projects/agentic-os/hermes-discord-delivery-receipt.json` (Hermes bot adapter 전송 결과)
- `wiki/projects/agentic-os/hermes-discord-dispatch-ack.json` (Hermes 처리 후)

`json`에는 Hermes orchestrator가 역할 프로필에 넘길 `work_id`, optional `ticket_id`, `suggested_roles`가 포함된다. board 파일은 projection이므로 직접 원장처럼 수정하지 않는다.
dispatch request와 ack의 중복 전송 방지 규칙은 `configs/hermes-discord-consumer.yaml`을 따른다.
Hermes runtime은 `tools/run_hermes_dispatch_cycle.py`로 board 갱신, pending payload batch 계산, outbox export를 한 번에 수행한다. `tools/run_hermes_discord_adapter.py`는 명시된 외부 adapter command에 outbox item을 넘겨 delivery receipt를 만들고, `tools/import_hermes_discord_receipt.py`가 성공한 payload만 ack에 반영한다.

### Hermes Runtime Cycle

상시 운영의 실행 주체는 Hermes다. 별도 오케스트레이터 서비스를 만들지 않고, Hermes cron이 아래 deterministic runner를 실행한다.

```bash
python3 "$TEAM2_HARNESS_PATH/tools/run_team2_knowledge_cycle.py" \
  --harness "$TEAM2_HARNESS_PATH" \
  --vault "$LOCAL_WIKI_PATH" \
  --apply
```

이 runner는 한 번의 cycle에서 다음만 수행한다.

- harness link projection 갱신
- vault relation backfill
- vault index projection 갱신
- Hermes decision board, Discord dispatch batch, outbox 갱신
- 공유 GBrain health 확인
- cycle status note 저장

Hermes cron에서는 같은 명령을 `/workspace/team2`, `/workspace/team2-vault`, `http://gbrain-team2:3131/health` 기준으로 호출한다. GBrain MCP 검색과 야간 도메인 분석은 Hermes agent job이 담당하고, deterministic runner는 사용자 승인 없이 YouTrack, KB, git commit/push, DB, 배포, canonical 승격을 수행하지 않는다.

현재 로컬 PGLite 기반 GBrain은 `serve --http` 실행 중에 같은 DB로 `gbrain sync --all`을 직접 돌리면 lock 경합이 생긴다. 따라서 인덱스 최신화는 Hermes 컨테이너 안에서 Docker socket을 열어 처리하지 않고, host LaunchAgent `com.team2.gbrain-maintenance`가 매일 01:40 KST에 짧게 `gbrain-team2`를 멈춘 뒤 `sync --all`과 doctor snapshot을 실행하고 다시 올린다. 장기적으로 무중단 sync가 필요하면 GBrain을 Supabase/Postgres/Railway 구성으로 옮긴다.

## Discord Role Profile Orchestration

Discord를 붙일 때 사용자는 오케스트레이터에게만 업무를 전달한다. Hermes는 기존 Discord bot 1개를 통해 board card를 역할 프로필에 분배한다. 역할 프로필은 `configs/discord-agent-profiles.yaml`을 기준으로 한다.

역할:

- `orchestrator`: 사용자 요청 접수, `/ad:work-prep` 또는 `/ad:new-note`, board 갱신, 역할 배정, Decision Packet 발행
- `architect`: 경계, 아키텍처, DB/SP 분리, 리스크 검토
- `developer`: 티켓별 구현, 테스트, PR 초안
- `planner`: 5W1H 티켓화, scope split, 우선순위 질문
- `qa`: 테스트, 회귀 위험, done-candidate 검토
- `designer`: UX, 화면, copy, 디자인 검토
- `domain_analyst`: 야간 도메인 분석, unresolved evidence, 지식 승격 후보

Discord 메시지는 control plane이다. durable record는 vault 노트에 남기고, 사용자에게는 Decision Packet, Approval Request, Completion Evidence만 올린다.
Claude Code와 Codex는 둘 다 같은 team2 하네스 도구와 vault 파일 계약을 사용한다.

## Domain Hardening Loop

야간 분석은 티켓 처리와 별개로 서비스 이해도를 높이는 작업이다. 결과는 다음날 티켓 prep과 영향 분석 품질을 높이는 데 사용한다.

### 분석 모드

| 모드 | 목적 | 산출물 |
|---|---|---|
| Discovery | 분석 seed 생성 | inventory, source gap, P0 후보 |
| Contract | API/SP/Table 계약 연결 | SP contract, caller map, read/write 후보 |
| Review | 자동 분석 의심 | 잘못된 confirmed, source gap, owner gap |
| Promotion | 검증된 지식 승격 후보 정리 | decision, canonical 후보, 하네스 반영 후보 |

### 기본 frontmatter

야간 분석 산출물은 기본적으로 아래 상태로 시작한다.

```yaml
type: analysis
status: draft
review_state: needs-review
evidence_level: E0 | E1 | E2
relation_status: inferred
```

모델이 확신한다고 해서 `confirmed`가 아니다. `confirmed`는 근거가 충분하고 사람이 확인했거나 테스트, 리뷰, 운영 검증으로 인정된 상태다.

### Evidence Level

| Level | 기준 | 사용 가능 범위 |
|---:|---|---|
| E0 | 이름, 주석, 검색 결과만 있음 | 질문 후보 |
| E1 | source path, hash, 추출 시점이 있음 | inventory |
| E2 | caller, SP, table read/write가 연결됨 | 영향 분석 초안 |
| E3 | 코드 경로와 DB script 또는 테스트가 교차 검증됨 | reviewed analysis |
| E4 | 사용자 확인 또는 PR/리뷰/운영 검증으로 인정됨 | confirmed 지식 |
| E5 | shadow-read, reconciliation, rollback 기준이 있음 | 구현 착수 후보 |

현대화나 DB 분리 판단은 최소 E3가 필요하다. 구현 착수는 E5 또는 별도 승인된 예외가 필요하다.

## gbrain 사용 기준

현재 DEV2 공유 gbrain은 Hermes Docker의 `gbrain-team2` 서비스가 제공하는 HTTP MCP를 기준으로 한다. 로컬 Codex/Claude Code는 `http://127.0.0.1:3131/mcp`, Hermes 내부에서는 `http://gbrain-team2:3131/mcp`를 사용한다. Mac의 직접 `gbrain` CLI는 개인 로컬 PGLite일 수 있으므로 공유 brain sync, embed, dream 같은 운영 명령은 `docker exec gbrain-team2 ...`로 실행한다.

gbrain은 아래 질문에 답하는 데 사용한다.

- 이 티켓과 관련된 과거 회의, 결정, 분석이 있는가?
- 같은 서비스, 같은 SP, 같은 테이블을 건드리는 티켓이 있는가?
- 사용자가 지금 결정해야 할 항목만 무엇인가?
- 이 작업이 blocked인 이유는 정책, 근거 부족, 승인 대기 중 무엇인가?
- 야간 분석 중 다음 티켓 prep에 재사용할 수 있는 draft 지식은 무엇인가?

gbrain 결과는 후보다. gbrain 답변만으로 `confirmed`, `canonical`, `done` 상태를 부여하지 않는다.

## 승인 게이트

아래 작업은 항상 사용자 승인 후 실행한다.

- YouTrack 티켓/Task 생성, 상태 전환, 담당자/필드 변경
- YouTrack KB 생성/수정/삭제/이동
- git commit, push, merge, PR 생성/머지
- dev DB write
- 운영 DB 조회/변경
- SP, schema 변경
- 프로덕션 배포
- vault 문서의 `canonical` 승격

아래 작업은 자동으로 수행할 수 있다.

- read-only YouTrack 조회
- vault draft 노트 생성/갱신
- Daily 아젠다 추가
- read-only 코드 분석
- dev/staging read-only SQL 검증
- gbrain sync
- Hermes board projection 생성
- PR 본문, 테스트 계획, Decision Packet 초안 생성

## 완료 기준

티켓을 완료 후보로 보려면 아래를 만족해야 한다.

- 티켓 노트에 문제, 판단, 해결 방향, 검증 결과가 있다.
- 변경 사항 또는 분석 결과가 관련 서비스/도메인/회의와 연결되어 있다.
- 실행한 테스트 또는 검증하지 못한 이유가 기록되어 있다.
- 남은 리스크가 `none` 또는 명시된 승인 사항으로 정리되어 있다.
- YouTrack/KB/git/DB/배포 변경은 승인 상태가 분리되어 있다.
- agent 내부 memory에만 남은 결정이나 근거가 없다.

## 주기 점검

매일:

- `Decision Needed`, `Approval Needed`, `Review Needed` 카드만 우선 확인한다.
- `Ready to Run`, `Investigating`은 agent가 계속 진행하게 둔다.

매주:

- `inferred` 상태로 7일 이상 남은 관계를 점검한다.
- `needs-review` 분석 중 티켓 prep에 자주 재사용되는 항목을 검토한다.
- 반복적으로 발생한 agent 실수는 team2 하네스 또는 서비스 하네스 개선 후보로 정리한다.

매월:

- 서비스별 unresolved evidence를 정리한다.
- 오래된 draft 분석은 폐기, 재분석, 승격 후보로 분류한다.
- Hermes board 카드가 과도하게 늘어난 원인을 점검한다.

## 관련 문서

- [에이전트 런타임 DEV2 운영 지침](./hermes-agent-operating-guide.md)
- [Discord 에이전트 오케스트레이션 가이드](./discord-agent-orchestration-guide.md)
- [LLM 위키 운영 가이드](./llm-wiki-operating-guide.md)
- [운영 위키 탐색 가이드](./wiki-navigation-guide.md)
- [작업 준비 command](../.claude/commands/ad/work-prep.md)
- [지식베이스 관리 정책](../policies/knowledge-base-policy.md)
