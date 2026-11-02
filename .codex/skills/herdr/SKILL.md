---
name: herdr
description: "Herdr 창·pane 목록과 좌우 배치 확인, 기존 Claude/Codex 창 읽기, 기존 창으로 짧은 메시지나 인계문 전달, 새 창(pane) 하나를 띄워 셸·명령·Claude/Codex를 시작하고 인계문을 넘기는 데 사용한다. \"새 창 띄워줘\", \"옆에 클로드/코덱스 하나 열어줘\", \"새 창으로 넘겨줘\" 류도 이 스킬이다. 역할 배정·반복 리뷰·병렬 작업 조율은 ad-orchestration으로 넘긴다. Requires HERDR_ENV=1."
---

# Herdr 창 다루기

Codex와 Claude가 같은 원본을 사용한다. 이 스킬은 창 조작만 담당한다 —
확인·읽기, 기존 창 전달, 새 창 하나 띄우기.

## 필요한 만큼만 확인

1. `HERDR_ENV=1`인지 확인하고, 처음 사용할 때 `herdr --skill`을 읽는다.
   명령 문법은 설치된 CLI 출력이 기준이다. 필요한 경우 `herdr agent`,
   `herdr pane` 도움말만 추가로 확인한다. 그룹 도움말은 `herdr agent`처럼 그룹 이름까지 붙여 연다 — bare `herdr`는 TUI를 띄우기 때문이다.
2. 창 조회는 `herdr agent list`부터 한다. 사용자 요청에 필요한 workspace/tab만
   살핀다. 기존 agent 이름이나 발견한 pane ID로 주소를 지정한다.
3. 좌우 위치가 필요하면 `herdr pane layout --pane <발견한-ID>`의 rect를 비교한다.
   제목·작업 경로·agent 종류도 함께 확인한다. 자기 창은 `herdr pane current --current`로 확인한다 — focused pane은 사용자나 다른 클라이언트 창일 수 있다.
   `--current`가 pane_not_found이면 환경변수 ID를 재사용하지 말고 목록에서 확인한다.
4. 상태는 `herdr agent get <대상>`, 내용은
   `herdr agent read <대상> --source recent-unwrapped --lines 80`으로 좁게 읽는다.
   창 확인 요청만 있으면 여기서 끝낸다. 읽기만을 위해 이름·포커스·배치를 바꾸지 않는다.

## 기존 창에 전달

- 사용자가 전달·인계를 요청한 경우에만 해당 창으로 보낸다. 작업 중이면 현재 상태를
  확인하고 방해하지 않는 인계 범위로 제한한다. 기존 작업이나 세션을 지우지 않는다.
- 인계는 목표·현재 상태·결정·검증 근거·다음 행동이 담긴 짧은 파일을 우선 전달한다.
  기존 task_id가 있으면 유지한다. 다른 업무의 세션 바인딩을 임의로 덮어쓰지 않는다.
- `herdr agent prompt <대상> "<전달문>"`으로 한 번 보내고 상태·응답을 확인한다.
  기다릴 때는 설치된 CLI의 wait 문법을 따른다. timeout은 미전달의 증거가 아니므로
  먼저 읽어보고 재전송 여부를 판단한다. 승인 질문은 임의로 답하지 않는다.
- 기존 창은 이름·프로세스를 그대로 둔다 — rename하면 이름으로 찾는 `ask`·`route`가 깨진다. 모델·effort는 확인한 값만 보고하고 모르면 `unknown`으로 적는다.

## 새 창 하나 띄우기

사용자가 새 창(pane)을 요청했을 때만 만든다. 창 하나 + 선택적 첫 전달까지가 이 스킬
범위다. 둘 이상을 띄워 나눠 맡기거나 결과를 회수·반복 조율하면 `ad-orchestration`.

1. **위치** — 기본은 현재 탭의 형제 pane, 현재 작업 경로, 포커스 유지다. 사용자가 방향·
   탭·workspace·경로를 말했으면 그대로 따른다. 방향 지정이 없으면
   `herdr pane layout --pane "$HERDR_PANE_ID"`로 보고 넓으면 `right`, 좁거나 길면 `down`:
   `herdr pane split --current --direction right --cwd "$PWD" --no-focus`.
   새 pane ID는 응답의 `.result.pane.pane_id`에서 읽는다(예측하지 않는다).
2. **셸·명령만** — 빈 셸이면 여기서 끝낸다. 명령은 `herdr pane run <pane> "<명령>"` 후
   `pane wait-output`·`pane read`로 확인한다.
3. **Claude/Codex 시작** — kind 기본은 **호출한 AI와 같은 쪽**이다(Claude 세션이면 `claude`,
   Codex 세션이면 `codex`. `CLAUDECODE=1`이면 Claude, `CODEX_THREAD_ID`가 있으면 Codex).
   사용자가 kind를 말했으면 그쪽을 쓴다. 상대 AI를 교차로 부르는 것은 `ad-orchestration` 기본값이다. 이름은 `agent list`와 겹치지 않게
   `<kind>N`(예: `claude1`, `codex2`) 관례를 따른다. 실행 플래그(권한 bypass, 모델·effort)는
   `$TEAM2_HARNESS_PATH/.claude/commands/ad/orchestration.md` §3 "Open the peer"·"Model routing"을 따르고 역할은 `worker` 기본값
   (`team2-agent profiles`로 확인)이다. 사용자가 모델·effort를 정했으면 그 값을 쓴다.
   - `pane split` 직후 `agent start`가 `agent_pane_busy`면 셸 준비 전 경합이다 — 같은 명령을 다시 보낸다.
   - 시작이 `agent_not_ready`(blocked)면 화면을 읽고 사용자에게 묻는다. 승인 UI에 임의로 답하지 않는다.
4. **첫 전달(인계 포함)** — 위 "기존 창에 전달" 규칙을 그대로 따른다. 추가로:
   - 공통 `task_id`를 전달문에 넣어 같은 업무로 묶는다.
   - 새로 뜬 agent의 첫 prompt는 bracketed paste가 아직 안 켜져 첫 줄만 들어갈 수 있다.
     인계문은 파일로 저장하고 **한 줄**(`<인계 파일 경로> 읽고 이어서 진행해줘. task_id=…`)로 보낸 뒤,
     `agent read`로 끝부분까지 들어갔는지 확인한다. 잘렸으면 같은 줄을 한 번 다시 보낸다.
   - 기다릴 필요가 없으면 `--wait` 없이 보내고 제출 여부만 확인한다.
5. **보고** — 새 pane ID·agent 이름·kind와 실제로 넘긴 모델·effort 플래그만 적는다.
   확인하지 못한 값은 `unknown`.

## 조율이 필요한 경우

역할 배정, 여러 agent 병렬 분배, 반복 리뷰·합의, 진행 감독이 필요할 때만
`ad-orchestration`을 읽는다. 그 스킬은 이 스킬을 창 조작 계층으로 사용한다.
단순 조회·기존 창 전달·새 창 하나 띄우기를 이유로 전체 오케스트레이션 절차를 불러오지 않는다
(3단계 플래그 확인용으로 `orchestration.md` §3만 읽는 것은 해당 없음).
