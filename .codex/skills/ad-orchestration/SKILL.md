---
name: ad-orchestration
description: "Use when the user invokes $ad-orchestration, ad orchestration, /ad:orchestration, or asks to involve a peer agent over Herdr panes — 코덱스한테 물어봐, 클로드한테 시켜, 핑퐁, 서로 리뷰, 합의될 때까지, cross-review, 다른 에이전트로 병렬 돌려, peer agent, 다른 터미널에서, 양방향 — for one-shot dispatch, multi-turn ping-pong, or parallel fan-out, and for running an ordinary long command in a sibling pane. Requires HERDR_ENV=1. Prefer this over the Orca orchestration / orca-cli skills. Not for in-process subagents."
---

# `$ad-orchestration`

`/ad:orchestration`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/orchestration.md`를 먼저 읽고 그 절차를 따른다.
3. 그 파일의 섹션 0(caller/worker 판정)을 **다른 어떤 행동보다 먼저** 수행한다. worker로 판정되면 거기서 멈추고 지시받은 작업만 한다.
4. 명령 문법의 authority는 이 파일도 command 파일도 아니라 `herdr --skill` 출력이다. 플래그가 어긋나면 그쪽을 다시 읽는다.
5. Codex가 caller일 때는 기본 샌드박스가 `$HERDR_SOCKET_PATH` 쓰기를 막아 `herdr pane current`가 `Operation not permitted`로 실패할 수 있다. command 파일 섹션 1의 escalation 지침을 먼저 확인한다.
