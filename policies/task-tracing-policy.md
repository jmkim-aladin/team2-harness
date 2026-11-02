# 공통 작업 식별과 Langfuse 관측

작업을 여러 터미널·에이전트에서 이어도 같은 업무로 조회하기 위한 계약이다.
관측용 식별자는 YouTrack 티켓·승인·완료 판정을 대신하지 않는다.
근거: 2026-10-30 사용자 요청 — 티켓 없는 작업에도 하네스에서 공통 task_id를 발급하고 사용.
북극성 원칙 1·4·6: 문구에만 의존하지 않고 자동 발급·동시성 검사·영속 등록부로 연결한다.

## 식별 기준

- `task_id`는 업무 단위다. 처음부터 티켓이 정해졌으면 `DEV2-숫자`, 없으면
  `TASK-YYYYMMDD-고유값`을 발급한다. 뒤에 티켓이 생기면 기존 ID를 유지하고
  `ticket_id`를 연결한다 — 이미 저장된 실행과의 연결을 유지하기 위해서다.
- `session_id`는 대화 단위이며 에이전트가 발급한 값을 보존한다. 같은 task_id를
  여러 세션에서 공유해도 세션 ID를 합치지 않는다 — 원래 대화와 실행 경계를 보존한다.
- 작업 이름은 사람이 알아보는 제목이다. repo·branch·agent는 실행 위치/도구이며
  작업 ID의 대체물이 아니다. 같은 저장소에서 병렬로 하는 별개 업무는 별도 ID다.
- 같은 업무의 후속 질문·구현·리뷰·위임·handoff는 기존 task_id를 사용한다.
  다른 업무로 전환할 때는 새 세션을 사용한다 — 플러그인이 미전송 대화를 뒤늦게
  수집할 수 있으므로 한 세션에 여러 작업의 식별값을 뒤섞지 않기 위해서다.
- 공통 ID는 환경의 `TEAM2_TASK_ID`, 명시적인 handoff의 `task_id: ...`, 기존
  세션 바인딩으로 전달한다. 신규 세션에 명시적 ID가 없으면 자동 발급한다.
  저장소·제목 유사성으로 다른 세션의 작업에 자동 합류하지 않는다 — 오결합 방지.

## 에이전트 사용

작업 시작 시 주입된 task_id를 확인하고, 제목/티켓을 알게 되면 아래 명령으로
등록부를 보완한다. 명시적 티켓이 없는 조사·질문도 동일하게 처리한다.

```sh
team2-task ensure --title 'Langfuse 작업 구분 설정'
team2-task ensure --ticket DEV2-12345 --title '로그인 오류 수정'
```

Codex는 현재 thread ID, Claude Code는 SessionStart에서 전달한 세션 ID로 기존
바인딩을 재사용한다. 일반 셸에서 `ensure`는 세션 없는 작업을 발급한다.

위임·인계에는 `task_id: <기존 ID>`를 명시한다. 새로운 외부 에이전트를 띄울 때는
아래 launcher가 같은 ID를 환경에 전달한다. 부모의 session_id는 복제하지 않는다.

```sh
team2-task run DEV2-12345 -- codex
team2-task run DEV2-12345 -- claude
team2-task show DEV2-12345
```

처음부터 공통 ID가 있는 새 세션은 첫 요청에 아래 한 줄을 포함해도 된다.
여러 task_id를 동시에 나열하면 자동 선택하지 않고 별도 ID를 발급한다.

```text
task_id: TASK-20261030-012345abcdef
이 작업의 구현 결과를 리뷰해줘.
```

`/ad:... DEV2-숫자` 또는 요청 맨 앞의 `DEV2-숫자`도 최초 ID로 인식한다.
요청 중간에 참고로 언급한 티켓과 git branch에서 업무 ID를 추측하지 않는다.
관측용 TASK 발급은 제품 코드 개발의 YouTrack 티켓 요구를 면제하지 않는다.

### 교차 오케스트레이션과 서브에이전트

- `team2-agent herdr`는 실행 프롬프트·ask·route·ticket/work lead·role 전달문에
  `task_id: ...`를 자동 삽입한다. ticket 경로는 티켓의 등록 ID를, 비티켓 work 경로는
  `(service, work_ref)`에 등록된 공통 TASK ID를 재사용한다.
- Herdr CLI를 직접 사용하는 `/ad:orchestration`은 첫 dispatch 전에 `ensure`로 ID를
  확정하고 opening envelope에 독립된 `task_id:` 행으로 전달한다. 같은 업무의 핑퐁은
  같은 ID를 사용하고, 다른 업무는 새 peer 세션을 연다.
- 두 엔진의 `SubagentStart` 훅은 부모 session_id의 task_id를 조회하고, child agent_id를
  같은 작업에 바인딩한 뒤 자식 컨텍스트에 주입한다. 부모 등록이 없으면 한 번 발급한다.
  내장 서브에이전트의 실행 기록 수집은 원본 플러그인의 부모/자식 transcript 변환을 이용한다.
- 기존 세션을 다른 작업 ID로 덮어쓰는 대신 새 세션을 사용한다 — 미전송 기록의 오결합을 막는다.

## 저장·조회와 운영

- 명령: `bin/team2-task` → `tools/task_tracing.py`.
- 등록부: `~/.local/state/team2/task-tracing/tasks.sqlite3`.
  SQLite 트랜잭션으로 동시 발급과 세션 바인딩을 보호한다. 시크릿·대화 본문은 저장하지 않는다.
- 훅 어댑터는 원본 플러그인의 변환 스크립트를 호출한다. 설치된 vendor 파일은 보존하고,
  원본 플러그인의 자동 훅은 비활성화하여 중복 수집을 막는다.
- 로컬 연결 경로: `~/.langfuse-team2/task-tracing.json`.
  Codex의 기존 보호된 연결 설정과 Claude용 기존 `client.env`를 사용한다.
- 두 엔진 공통 검색 태그: `task_id:...`, `task_name:...`, `repo:...`, `agent:...`,
  `branch:...`, 선택적 `ticket_id:...`. Codex는 같은 값을 metadata에도 기록한다.
  Claude의 원본 변환기는 사용자 지정 metadata 입력을 제공하지 않아 공통 태그로 조회한다.
- Langfuse Tracing/Sessions에서 `task_id:<ID>` 태그를 필터링하면 해당 작업의 여러
  에이전트·세션을 함께 볼 수 있다. 모든 observation에 같은 ID를 강제로 붙여 세션을 합치지 않는다.
- 외부 전송 오류는 실제 작업을 차단하지 않는다. 어댑터 오류는 등록부 옆
  `hook-errors.log`에 오류 종류만 남긴다. 전송 여부는 서버 조회로 판정한다.
- 플러그인 업데이트 후에는 어댑터가 가리키는 설치 경로와 합성 기록 전송을 검증한다.
  설정의 경로를 자동 추측해 다른 버전 코드를 실행하지 않는다 — 검증한 코드 경계를 유지한다.

검증: `python3 -m unittest discover -s tests -p test_task_tracing.py -v`.
동일 세션 동시 발급·별개 작업 격리·엔진 간 ID 공유·worktree repo 식별·전송 실패 격리를 검사한다.
