# Discord 에이전트 오케스트레이션 가이드

이 문서는 Hermes에 연결된 기존 Discord bot 1개로 DEV2 에이전트 역할 프로필을 운영할 때의 기준이다. 목표는 사용자가 여러 터미널과 agent를 직접 관리하는 일을 줄이고, 오케스트레이터에게 업무를 전달하면 Hermes가 역할 프로필을 기준으로 vault와 board를 읽고 진행하도록 만드는 것이다. board의 기본 단위는 티켓이 아니라 `work_id`가 있는 work item이다.

## 원칙

1. Discord는 작업 표면이지 원장이 아니다.
2. 원장은 YouTrack, vault, team2 하네스다.
3. Hermes decision board JSON은 역할 프로필에 나눠줄 작업 큐다.
4. 사용자는 기본적으로 오케스트레이터에게만 지시한다.
5. 역할 프로필은 사용자에게 직접 원자료를 던지지 않고, Decision Packet 또는 Evidence 형태로만 올린다.
6. YouTrack, KB, git, DB write, 배포, `canonical` 승격은 사용자 승인 전 실행하지 않는다.
7. Claude Code와 Codex는 같은 team2 `tools/`와 vault 파일 계약을 사용한다.

## 구조

```text
사용자
  ↓
Discord 기존 bot
  ↓
Hermes Orchestrator
  ↓
Hermes Decision Board Projection
  ↓
역할 프로필
  - architect
  - developer
  - planner
  - qa
  - designer
  - domain_analyst
  ↓
vault draft notes / code work cell / evidence
  ↓
Orchestrator Decision Packet
  ↓
사용자 결정
```

## 프로필

역할별 기준 프로필은 `configs/discord-agent-profiles.yaml`을 따른다. 새 Discord bot을 만들지 않고, Hermes에 연결된 기존 bot이 이 파일을 prompt/profile source로 사용한다.

| Role | 책임 |
|---|---|
| `orchestrator` | 사용자 요청 접수, board 갱신, 역할 배정, 결정 질문 |
| `architect` | 경계, 아키텍처, DB/SP 분리, 기술 리스크 |
| `developer` | 티켓별 구현, 테스트, PR 초안 |
| `planner` | 5W1H 티켓화, scope split, 우선순위 질문 |
| `qa` | 테스트, 회귀 위험, done-candidate 검토 |
| `designer` | UX, 화면, copy, 디자인 검토 |
| `domain_analyst` | 야간 도메인 분석, evidence gap, 지식 승격 후보 |

## 채널 권장안

| Channel | 용도 |
|---|---|
| `#jm-orchestrator` | 사용자가 지시하고 결정하는 단일 입구 |
| `#agent-board` | board projection 요약, 카드 변경 알림 |
| `#agent-dev` | developer profile 작업 로그와 handoff |
| `#agent-qa` | QA evidence와 done-candidate 검토 |
| `#agent-design` | 디자인 리뷰 |
| `#agent-domain` | 야간 도메인 분석과 evidence gap |
| `#agent-archive` | 완료된 Decision Packet, 승인 기록 보관 |

사용자 멘션은 기본적으로 `#jm-orchestrator`에서만 발생시킨다. 역할별 채널은 agent 간 작업 로그와 evidence용이다.

## Board Projection 생성

Hermes와 기존 Discord bot이 읽는 board projection은 vault frontmatter에서 생성한다.

```bash
TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"
LOCAL_WIKI_PATH="${LOCAL_WIKI_PATH:-/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2}"

python3 "$TEAM2_HARNESS_PATH/tools/generate_decision_board.py" --vault "$LOCAL_WIKI_PATH" --apply
```

생성 파일:

- `wiki/projects/agentic-os/hermes-decision-board.md`
- `wiki/projects/agentic-os/hermes-decision-board.json`
- `wiki/projects/agentic-os/hermes-discord-dispatch-request.json`
- `wiki/projects/agentic-os/hermes-discord-dispatch-batch.json`
- `wiki/projects/agentic-os/hermes-discord-outbox/{request_id}/manifest.json`
- `wiki/projects/agentic-os/hermes-discord-delivery-receipt.json` (Hermes bot adapter 전송 결과)
- `wiki/projects/agentic-os/hermes-discord-dispatch-ack.json` (Hermes 처리 후 작성)

board card는 `work_id`를 필수 식별자로 가진다. YouTrack 티켓에서 온 업무는 `work_id=DEV2-1234`와 `ticket_id=DEV2-1234`를 함께 가진다. 분석, 프로젝트 고도화, 운영 개선처럼 티켓이 없는 업무는 `canonical_id` 또는 vault path stem을 `work_id`로 사용하고 `ticket_id`는 비운다.

카드 생성 조건:

- `decision_status: decision-needed`
- `decision_status: approval-needed`
- `decision_status: blocked`
- `decision_status: review-needed`
- `ticket_status: blocked`
- `ticket_status: review-needed`
- `ticket_status: done-candidate`
- `review_state: needs-review`

`ticket_status: in-progress`, `decision_status: none`인 작업은 board에 올리지 않는다.

Hermes가 기존 Discord bot으로 처리할 dispatch request는 read-only로 생성한다. 이 명령은 Discord API를 호출하지 않는다.

```bash
python3 "$TEAM2_HARNESS_PATH/tools/generate_discord_orchestrator_payload.py" --vault "$LOCAL_WIKI_PATH" --apply
```

Claude Code와 Codex 공통 명령은 아래를 사용한다.

```bash
/ad:work-board apply
$ad-work-board apply
```

두 명령은 모두 team2 하네스의 `tools/run_work_board.py`를 실행한다.

dispatch request 구조:

```json
{
  "schema": "team2.hermes_discord_dispatch_request.v1",
  "request_id": "hdr-...",
  "target": "hermes",
  "transport": "hermes-existing-discord-bot",
  "dispatch_status": "pending-hermes",
  "payloads": [
    {
      "payload_id": "hdp-...",
      "channel": "agent-board",
      "content": "..."
    }
  ]
}
```

`dispatch_status: pending-hermes`인 상태가 기본이다. 실제 Discord 송신은 Hermes에 연결된 기존 bot이 담당한다. team2 하네스 도구는 Discord webhook이나 bot token을 직접 다루지 않는다.

Hermes consumer 계약은 `configs/hermes-discord-consumer.yaml`을 따른다. 중복 전송 방지를 위해 `request_id`와 `payload_id`를 사용한다.

Hermes runtime의 기본 주기 실행 단위는 아래 cycle runner다. 이 명령은 board projection과 dispatch request를 갱신하고, 기존 ack를 고려해 pending batch를 계산한다. 실제 Discord API는 호출하지 않는다.

```bash
python3 "$TEAM2_HARNESS_PATH/tools/run_hermes_dispatch_cycle.py" --vault "$LOCAL_WIKI_PATH" --apply --default-batch-output --default-outbox
```

Hermes bot adapter는 stdout의 `batch.payloads`, `wiki/projects/agentic-os/hermes-discord-dispatch-batch.json`, 또는 `wiki/projects/agentic-os/hermes-discord-outbox/{request_id}/` 아래 item 파일을 읽어 전송한다.

외부 adapter command가 준비된 환경에서는 아래 runner로 outbox item을 하나씩 넘기고 delivery receipt를 만들 수 있다. adapter command는 item JSON 경로를 마지막 인자로 받는다. 이 runner는 Discord token, webhook URL, channel id를 저장하지 않는다.

```bash
python3 "$TEAM2_HARNESS_PATH/tools/run_hermes_discord_adapter.py" \
  --vault "$LOCAL_WIKI_PATH" \
  --adapter-command "/path/to/hermes-discord-send" \
  --apply
```

`--apply` 없이 실행하거나 `--adapter-command`가 없으면 receipt 결과는 `skipped`가 되고 파일은 쓰지 않는다. command exit code가 `0`이면 `dispatched`, nonzero면 `failed` receipt row가 된다.

세부 디버깅이 필요하면 실제 Discord bot adapter를 호출하기 전에 아래 reference consumer로 pending payload만 별도 계산할 수 있다.

```bash
python3 "$TEAM2_HARNESS_PATH/tools/hermes_dispatch_consumer.py" --vault "$LOCAL_WIKI_PATH"
python3 "$TEAM2_HARNESS_PATH/tools/export_hermes_discord_outbox.py" --vault "$LOCAL_WIKI_PATH" --apply
```

출력 batch 구조:

```json
{
  "schema": "team2.hermes_discord_dispatch_batch.v1",
  "request_id": "hdr-...",
  "dispatch_required": true,
  "payload_count": 1,
  "payloads": [
    {
      "payload_id": "hdp-...",
      "channel": "agent-board",
      "content": "..."
    }
  ]
}
```

Hermes는 `payloads`만 기존 Discord bot adapter로 보낸다. 같은 `request_id`가 이미 전부 ack 처리되어 있으면 `dispatch_required: false`와 빈 `payloads`가 나온다. partial ack가 있으면 아직 `dispatched`가 아닌 `payload_id`만 나온다.

Hermes bot adapter가 실제 Discord 전송을 수행한 뒤에는 delivery receipt를 남긴다.

```json
{
  "schema": "team2.hermes_discord_delivery_receipt.v1",
  "request_id": "hdr-...",
  "results": [
    {
      "payload_id": "hdp-...",
      "channel": "agent-board",
      "status": "dispatched",
      "external_id": "discord-message-id"
    },
    {
      "payload_id": "hdp-...",
      "channel": "agent-dev",
      "status": "failed",
      "error": "rate limit"
    }
  ]
}
```

receipt의 `dispatched` 행만 ack에 반영한다. `failed`와 `skipped`는 pending으로 남기고 다음 cycle에서 재시도한다.

Hermes 처리 후 ack 파일은 아래 형식이다.

```json
{
  "schema": "team2.hermes_discord_dispatch_ack.v1",
  "request_id": "hdr-...",
  "acked_at": "2026-06-17T00:00:00+09:00",
  "dispatch_status": "dispatched",
  "payloads": [
    {
      "payload_id": "hdp-...",
      "channel": "agent-board",
      "status": "dispatched"
    }
  ]
}
```

ack 생성/검증 보조 명령:

```bash
python3 "$TEAM2_HARNESS_PATH/tools/ack_hermes_dispatch.py" --vault "$LOCAL_WIKI_PATH"
python3 "$TEAM2_HARNESS_PATH/tools/ack_hermes_dispatch.py" --vault "$LOCAL_WIKI_PATH" --apply
python3 "$TEAM2_HARNESS_PATH/tools/hermes_dispatch_consumer.py" --vault "$LOCAL_WIKI_PATH" --mark-dispatched --apply
python3 "$TEAM2_HARNESS_PATH/tools/import_hermes_discord_receipt.py" --vault "$LOCAL_WIKI_PATH" --apply
```

`--apply`는 Hermes가 실제 전송을 완료했거나 수동으로 전송 완료를 확인한 경우에만 사용한다.
일부 payload만 전송에 성공했으면 `--mark-dispatched --payload-id hdp-... --apply`처럼 성공한 payload만 ack에 반영한다.

## 메시지 계약

### Task Brief

```markdown
## Task Brief

- Card: {board card id}
- Work: {work_id}
- Ticket: DEV2-1234 또는 없음
- Service: storefront
- Goal: {역할 프로필이 끝내야 할 일}
- Source Note: `wiki/processes/tickets/dev2-1234.md`
- Allowed Actions:
- Forbidden Actions:
- Expected Output:
```

### Decision Packet

```markdown
## Decision Packet

- ID: D-001
- Work: {work_id}
- Ticket: DEV2-1234 또는 없음
- Service: storefront
- Recommendation: A

### Options
- A: {추천}
- B: {대안}
- Hold: {보류 시 영향}

### Evidence
- Vault:
- Code:
- Test:
- Meeting:

### Impact
- User:
- Ops:
- Schedule:
- Risk:

### Required Answer
A / B / Hold / More Investigation
```

### Completion Evidence

```markdown
## Completion Evidence

- Work: {work_id}
- Ticket: DEV2-1234 또는 없음
- Changed Artifacts:
- Verification:
- Remaining Risk:
- Approval Needed:
```

## 운영 루프

1. 사용자가 오케스트레이터에게 티켓, 분석, 프로젝트 고도화, 운영 개선 업무를 전달한다.
2. 티켓이면 오케스트레이터가 `/ad:work-prep`으로 vault 티켓 노트를 만든다. 비티켓 업무면 `/ad:new-note` 또는 프로젝트/분석 노트로 work item을 만든다.
3. `generate_decision_board.py --apply`로 board projection을 갱신한다.
4. `generate_discord_orchestrator_payload.py --apply`로 Hermes dispatch request를 만든다.
5. Hermes 오케스트레이터가 board card의 `suggested_roles`에 따라 역할 프로필에 Task Brief를 넘긴다.
6. 역할 프로필은 결과를 vault draft note와 Discord evidence로 남긴다.
7. 사용자 결정이 필요할 때만 오케스트레이터가 Decision Packet을 올린다.
8. 승인 후에만 YouTrack, KB, git, DB write, 배포 작업을 실행한다.

## 금지

- Discord 메시지만 보고 work item 또는 티켓을 완료 처리하지 않는다.
- role profile이 사용자 승인 없이 YouTrack/KB/git/DB/prod를 변경하지 않는다.
- raw log나 긴 grep 결과를 사용자 결정 채널에 올리지 않는다.
- board JSON을 원장처럼 수동 수정하지 않는다.
- role profile별 prompt에 토큰, 쿠키, DB 접속정보를 저장하지 않는다.
