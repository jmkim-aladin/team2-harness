---
name: herdr
description: "Herdr 앱의 창·pane 목록과 좌우 배치 확인, 기존 Claude/Codex 터미널 읽기·전달·인계, 새 창 하나 열기에 사용한다. 현재 구조는 herdr-app(창)과 herdr-core의 hc(터미널)다. 역할 배정·반복 리뷰·병렬 조율은 ad-orchestration을 사용한다."
---

# Herdr — 앱과 core 분리

Codex와 Claude가 같은 원본을 사용한다. 현재 Herdr는 창을 관리하는
`herdr-app`과 터미널·프로그램을 관리하는 `hc`(`herdr-core`의 CLI)로 나뉜다.
설치 버전의 지침을 읽어 문법과 동작을 확인하고, 여기에는 팀 설정만 둔다.

## 설치 지침과 조회

터미널을 다루기 전에 `hc --skill`을 읽는다(`herdr-core --skill`도 같은 지침).
창·pane 배치가 필요하면 `herdr-app --skill`도 읽는다. 추가 인자는 해당 명령의
`--help`와 `herdr-app commands`로 확인한다.

기본 조회:

```bash
hc ls --json
herdr-app ls
herdr-app status
```

`hc ls`는 터미널 주소·이름·agent·상태·경로, 앱의 `ls`는
space → tab → pane과 terminal 연결, `status`는 현재 화면의 포커스를 보여 준다.
터미널만 조회할 때는 앱이 열려 있을 필요가 없다. 앱 조회 실패와 core 조회 실패는 구분한다.

현재 구조에서는 `HERDR_ENV` 검사나 구형 `herdr` CLI를 사용하지 않는다.
환경변수가 없다는 이유로 조회를 중단하지 말고 실제 조회 결과로 연결 가능 여부를 판단한다.
근거: 2026-11-10 사용자 요청 — 구형 Herdr CLI를 사용하지 않는 현재 구조로 전환.

## 대상 식별과 읽기

- 터미널 주소는 `HC_TERMINAL_ID`가 단서다. 상속된 값은 낡을 수 있으므로
  `hc get <주소>`의 경로·foreground와 현재 세션을 대조한다. 불일치하면 live 목록에서
  확인하며, 앱의 focused pane을 자기 pane으로 간주하지 않는다.
- pane ID와 terminal 주소는 별개다. 앱에서 확인한 `terminal` 값을 `hc`에 넘긴다.
  원격 주소는 `machine/t7`처럼 전체 값을 유지한다.
- "좌측" 등 방향은 목록 순서만으로 단정하지 않는다. 앱의 목록·상태로 탭과 대상을 좁히고,
  현재 화면이면 `herdr-app shot /tmp/herdr-panes.png`로 위치를 확인한다.
  표시 중이 아닌 탭은 `hc schema`의 `doc.get`을 확인하고 `hc connect`에 JSON-RPC로
  `doc.get`·`{"name":"herdr-app"}`을 보내 저장된 tab의 `root` 분할 트리를 읽을 수 있다.
  조회를 위해 포커스·탭·배치를 바꾸지 않는다. 문서 갱신은 조회 범위 밖이다.
- 상태는 `hc get <주소>`, 현재 화면은 `hc read <주소> --lines 0`,
  최근 내용은 `hc read <주소> --lines 80`으로 읽는다. history 제한·미완전 표시는 core 지침을 따른다.
- 결과는 space/tab·pane ID·terminal 주소·agent·상태와 확인한 모델·effort를 보고한다.
  확인하지 못한 값은 `unknown`으로 적는다.

## 전달과 새 창

- 전달·인계는 사용자가 요청한 대상·범위로 `hc send <주소> "<전달문>"`을 사용한다.
  목표·현재 상태·결정·검증 근거·다음 행동과 공통 `task_id`를 담고,
  기존 세션의 다른 업무 바인딩은 유지한다. timeout 뒤에는 읽어본 후 재전송 여부를 판단한다.
- 새 pane·tab은 사용자가 요청했을 때 앱 명령으로 만든다. 기본은 현재 탭·현재 작업 경로이며,
  대상 pane을 명시하고 방향을 따른다. 정확한 인자는 `herdr-app commands`에서 확인한다.
  생성 응답의 pane과 terminal 주소를 읽고, 실행 상태는 `hc get`으로 확인한다.
- 새 agent의 kind 기본값은 호출한 AI와 같은 쪽이다. 사용자가 지정하면 그쪽을 쓴다.
  모델·effort·시작 로그는 `$TEAM2_HARNESS_PATH/.claude/commands/ad/orchestration.md`
  §3 Model routing을 따른다. Codex는 core 지침에 따라 `--no-daemon`을 포함한다.
- 화면 변경이 필요 없는 worker는 `hc run --bg`를 사용한다. 역할 배정·병렬 분배·반복 리뷰는
  `ad-orchestration`의 범위다. startup·첫 전달·대기·오류 복구는 core 지침을 따른다.
- 기존 터미널 이름·프로세스는 유지한다. 작업 표시용 라벨은
  `$TEAM2_HARNESS_PATH/docs/cmux-herdr-labeling.md`를 따른다.
  승인 UI는 사용자에게 넘기며, 정리는 자신이 만든 터미널·pane만 대상으로 한다.
