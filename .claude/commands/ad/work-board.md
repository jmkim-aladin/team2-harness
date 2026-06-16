# Work Board Projection

Hermes가 읽는 work-board projection과 Discord dispatch request를 갱신한다.

## 사용법

```bash
/ad:work-board
/ad:work-board apply
```

기본은 dry-run이다. `apply`가 있으면 vault projection 파일을 갱신한다.

## 역할

이 명령은 Claude Code와 Codex 공통 진입점이다. 실제 실행은 team2 하네스의 공통 CLI를 사용한다.

```bash
TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"
LOCAL_WIKI_PATH="${LOCAL_WIKI_PATH:-/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2}"

python3 "$TEAM2_HARNESS_PATH/tools/run_work_board.py" --vault "$LOCAL_WIKI_PATH"
python3 "$TEAM2_HARNESS_PATH/tools/run_work_board.py" --vault "$LOCAL_WIKI_PATH" --apply
```

## 생성 산출물

- `wiki/projects/agentic-os/hermes-decision-board.md`
- `wiki/projects/agentic-os/hermes-decision-board.json`
- `wiki/projects/agentic-os/hermes-discord-dispatch-request.json`
- `wiki/projects/agentic-os/hermes-discord-dispatch-batch.json` (Hermes runtime용 pending batch)
- `wiki/projects/agentic-os/hermes-discord-outbox/{request_id}/manifest.json` (Hermes bot adapter용 파일 handoff)
- `wiki/projects/agentic-os/hermes-discord-delivery-receipt.json` (Hermes bot adapter 전송 결과)
- `wiki/projects/agentic-os/hermes-discord-dispatch-ack.json` (Hermes 처리 후)

## 원칙

- board의 기본 단위는 `work_id`가 있는 work item이다.
- `ticket_id`는 YouTrack 티켓이 있을 때만 채운다.
- Hermes가 기존 Discord bot을 통해 dispatch request를 처리한다.
- Hermes runtime은 `tools/run_hermes_dispatch_cycle.py`로 board 갱신, pending payload 계산, outbox export를 수행한다.
- Hermes bot adapter 실행은 `tools/run_hermes_discord_adapter.py`로 명시적 adapter command에 outbox item을 넘긴다.
- Hermes bot adapter는 delivery receipt를 남기고 `tools/import_hermes_discord_receipt.py`로 ack를 갱신한다.
- 이 명령은 Discord API, webhook, bot token을 직접 다루지 않는다.
- 이 명령은 YouTrack, KB, git, DB, 배포를 변경하지 않는다.
- Claude Code와 Codex는 같은 `tools/run_work_board.py`와 같은 vault 파일 계약을 사용한다.

## 카드 생성 조건

- `decision_status: decision-needed`
- `decision_status: approval-needed`
- `decision_status: blocked`
- `decision_status: review-needed`
- `ticket_status: blocked`
- `ticket_status: review-needed`
- `ticket_status: done-candidate`
- `review_state: needs-review`

## 실행 절차

1. `$TEAM2_HARNESS_PATH`와 `$LOCAL_WIKI_PATH`를 확정한다.
2. 인자에 `apply`가 없으면 dry-run으로 실행한다.
3. 인자에 `apply`가 있으면 `--apply`로 projection 파일을 갱신한다.
4. 결과의 `cards`, `payloads`, 생성 파일 목록을 사용자에게 요약한다.
5. 카드가 0개면 "현재 사용자 개입 카드 없음"으로 보고한다.

## 금지

- Discord 송신 직접 실행 금지. 송신은 Hermes의 기존 bot 통합에서 처리한다.
- dispatch request JSON을 원장처럼 수동 수정하지 않는다.
- `canonical` 승격, YouTrack 상태 변경, KB 수정, git commit/push/PR은 이 명령의 책임이 아니다.

ARGUMENTS: $ARGUMENTS
