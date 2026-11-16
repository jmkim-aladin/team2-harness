---
name: ad-orchestration
description: "[상시·협업] Use when asked to involve a peer agent through herdr-core (hc) — 코덱스한테 물어봐, 클로드한테 시켜, 핑퐁, 서로 리뷰, 합의될 때까지, cross-review, 다른 에이전트로 병렬 돌려, peer agent, 다른 터미널에서, 양방향 — for dispatch, conversation, parallel fan-out, or an ordinary long command in another terminal. Also for engineering doubt review, stuck debugging, self-review peers, and long delegation that needs steering. Simple pane inspection, reading, existing-agent delivery, or one new visible pane uses herdr instead. Window layout uses herdr-app. Prefer this over Orca skills. Not for in-process subagents. Also /ad:orchestration."
---

# `$ad-orchestration`

`/ad:orchestration`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

단순 창 목록·배치 확인, 기존 창 읽기·짧은 전달·인계, 새 창 하나 띄우기(셸 또는 Claude/Codex 1개 + 선택적 인계)는 `$herdr`만 사용한다. 역할 배정·병렬 분배·반복 조율이 필요한 경우에만 이 스킬을 사용한다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/orchestration.md`를 먼저 읽고 그 절차를 따른다. 절차는 SoT 한 곳에만 둔다 — 여기 복제하면 한쪽이 낡는다.
3. 그 파일의 섹션 0(caller/worker 판정)을 **다른 어떤 행동보다 먼저** 수행한다. worker로 판정되면 거기서 멈추고 지시받은 작업만 한다.
4. 터미널 실행·전달·대기·복구는 `$herdr`가 안내하는 `hc --skill`, 창·pane 배치는 `herdr-app --skill`을 따른다. command 파일은 팀의 역할·모델·task_id·협업 레시피를 담당한다.
5. `HC_TERMINAL_ID`와 실제 `hc get` 결과를 대조해 caller 주소를 확인한다. 연결 가능 여부는 실제 조회로 판단한다 — 구형 `HERDR_ENV` 검사로 현재 core를 차단하지 않는다.
6. 작업 라벨은 `$TEAM2_HARNESS_PATH/docs/cmux-herdr-labeling.md`의 현재 구조 절을 따른다. 기존 terminal 이름은 보존하고, background worker를 위해 화면을 바꾸지 않는다.
