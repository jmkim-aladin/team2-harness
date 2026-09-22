# cmux/herdr 작업 라벨 규칙

pane·tab 라벨이 "지금 무슨 티켓의 무슨 업무를 누가 처리 중인지" 항상 반영하게 하는 공용 규칙.
cmux/herdr 외부(일반 터미널/tmux/iTerm/VSCode 내장 등)에서는 건드리지 않는다.

## 1순위: CLI로 붙인다

```bash
team2-agent herdr label DEV2-6509 "정산 배치 재처리"                  # lead pane
team2-agent herdr label DEV2-6509 "리뷰" --agent reviewer             # peer/role pane
team2-agent herdr label --no-ticket "훅 디버깅" --agent orch-worker-1  # 티켓 없는 pane
team2-agent herdr label DEV2-6509 "정산 배치 재처리" --pane p-abc123   # 다른 pane 지정
```

수동 `herdr tab rename` / `herdr pane rename` 대신 이 명령을 쓴다 — 스키마가 코드에 있어야 문서와 어긋나지 않는다.
환경 감지·문자열 컷·실패 처리는 `tools/team2_agent.py`(`run_herdr_label`, `pane_label_for`)가 담당한다.

`team2-agent herdr worker|tickets|work|role`로 띄운 pane은 기동 직후 코드가 자동으로 라벨을 붙이므로
사람이 따로 호출하지 않는다 — 지시문 준수에 의존하면 단계가 바뀔 때마다 누수가 난다.

## 라벨 스키마

| 면 | 라벨 | 예 |
|---|---|---|
| tab / cmux surface | 티켓번호(또는 work-id)만, 없으면 `NO-TICKET` | `DEV2-6509` |
| lead pane (ticket-lead / work-lead) | `{티켓} — {제목}` | `DEV2-6509 — 정산 배치 재처리` |
| peer / role / worker pane | `{티켓}/{에이전트명} — {업무}` | `DEV2-6509/reviewer — 리뷰`, `NO-TICKET/orch-worker-1 — 훅 디버깅` |
| herdr agent 이름 | 기존 규약 유지 (`ticket-DEV2-6509`, `orch-worker-1`, `claude0`, `codex1`) | 변경하지 않는다 |

- 제목·업무는 한 줄, 60자에서 말줄임한다 — pane 폭을 넘으면 앞부분까지 잘려 읽을 수 없다.
- 티켓·work-id가 없으면 `NO-TICKET` — 빈 자리를 남기면 무슨 작업인지 못 읽는다.
- tab 라벨은 `ticket_tab_label()` 출력과 정확히 같다 — `herdr close`/`tickets`가 이 문자열로 탭을 찾기 때문에 어긋나면 종료 대상 탭을 못 찾는다.

## agent 이름은 라우팅 주소다

`herdr agent rename`은 라벨 목적으로는 호출하지 않는다 — agent 이름은 `ask`/`route`/`collect`/`close`/`focus`가
대상을 찾는 주소라서(`tools/team2_agent.py`의 `task_lead_name()`·`lead_target_candidates()`·접두 매칭) 덮어쓰면 그 호출들이 전부 대상을 잃는다.
과거 이 문서에 있던 `herdr agent rename "$HERDR_PANE_ID" "$TAB_LABEL"` 한 줄은 이름을 `DEV2-6509`로 덮어써
`ticket-DEV2-6509` 접두 매칭과 orchestration의 `claude0`/`codex1` 주소를 동시에 깨뜨렸으므로 제거했다.

이름이 아예 없는 pane에 최초 1회 이름을 부여하는 경우만 예외다 (`/ad:orchestration` §2) — 이름이 없으면 peer가 접근할 수 없다.

## 갱신 시점

| 시점 | 할 일 |
|---|---|
| 작업 착수 | 티켓·제목이 정해지는 즉시 라벨을 붙인다 (`/ad:work-prep` §9, spawn 경로는 자동) |
| 단계 전환 | 업무가 바뀌면(분석 → 구현 → 리뷰) 같은 명령으로 다시 붙인다 — 첫 라벨이 남아 있으면 현재 단계를 오독한다 |
| 종료 | pane을 닫으면 라벨도 사라지므로 따로 되돌리지 않는다 |

## 감지와 실패 처리

- herdr 판정: `HERDR_ENV` + `HERDR_PANE_ID` + `herdr` 실행 가능. cmux 판정: `CMUX_WORKSPACE_ID` + `CMUX_SURFACE_ID` + `cmux` 실행 가능.
- 둘 다 아니면 조용히 no-op하고 종료 코드 0을 돌려준다 — 라벨은 부수 기능이고 상위 작업(pane 기동)이 본류다.
- 소켓 인증 실패·pane ID 만료 등 실패는 경고만 출력하고 다른 단계를 막지 않는다.
- cmux 워크스페이스 이름(`workspace-action --action rename --title ...`)과 herdr 워크스페이스 이름은 건드리지 않는다 — 사용자가 별도 작업 컨텍스트로 쓰고 있을 수 있다. tab(=surface) 단위만 바꾼다.
- 사용자 확인 없이 기본 진행한다. 변경된 tab/pane 라벨은 stdout에 `tab=` / `pane=`으로 출력된다.

## 참고: 내부 herdr 호출

`run_herdr_label`이 실제로 실행하는 명령 (직접 호출할 일은 없고, 디버깅용 참조).

```bash
herdr pane get "$HERDR_PANE_ID"            # → .result.pane.tab_id
herdr tab rename "$TAB_ID" "DEV2-6509"
herdr pane rename "$HERDR_PANE_ID" "DEV2-6509 — 정산 배치 재처리"
cmux rename-tab --surface "$CMUX_SURFACE_ID" "DEV2-6509"
```
