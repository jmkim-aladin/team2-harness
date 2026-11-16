# Herdr 작업 라벨 규칙

작업 표시가 "지금 무슨 티켓의 무슨 업무를 누가 처리 중인지"를 반영하게 한다.
현재 구조는 `herdr-app`(space·tab·pane)과 `hc`(terminal)다.
설치 지침과 대상 확인은
[공유 Herdr 스킬](../.codex/skills/herdr/SKILL.md)을 따른다.

## 현재 구조

`hc ls --json`과 `herdr-app ls`에서 terminal 주소와 tab ID를 확인한다.
작업 표시용 `where` 라벨은 terminal 이름과 별개다.

```bash
hc label <확인한-terminal주소> where="DEV2-6509/reviewer — 리뷰"
herdr-app do tab.rename --id <확인한-tab-ID> --name "DEV2-6509 - 정산 배치 재처리"
```

이 명령들은 작업 착수·단계 전환 때 사용한다. 단순 조회·읽기 요청은 라벨이나
탭을 바꾸지 않는다. 확인한 대상이 없으면 라벨 갱신을 생략하고 본 작업을 계속한다.

`where`는 core의 사람이 읽는 목록에 사용된다. 앱 헤더의 실제 표시는 layout에
따라 달라질 수 있으므로 terminal 이름을 바꿔 표시를 맞추지 않는다.
앱의 space 이름도 기존 작업 컨텍스트이므로 유지한다.

## 라벨 스키마

| 면 | 라벨 | 예 |
|---|---|---|
| tab | `{티켓} - {제목}`, 티켓이 없으면 `{제목}` | `DEV2-6509 - 정산 배치 재처리` |
| lead terminal의 where | `{티켓} — {제목}` | `DEV2-6509 — 정산 배치 재처리` |
| peer terminal의 where | `{티켓}/{에이전트명} — {업무}` | `DEV2-6509/reviewer — 리뷰` |
| terminal 이름 | live 주소로 쓰는 기존 이름 유지 | `claude1`, `codex1` |

제목·업무는 한 줄, 60자에서 말줄임한다. 티켓이 없으면 `NO-TICKET`을 쓴다.
메시지는 기존 terminal 주소·이름으로 보내며, 표시용 라벨은 주소를 대체하지 않는다.

## 화면 표시와 background worker

사용자가 보이는 새 pane·tab을 요청했을 때만 앱 명령으로 만든다.
화면 변경이 필요 없는 worker는 `hc run --bg`로 실행한다.
`herdr.space`·`herdr.tab`은 worker를 화면에 표시하는 연결 라벨이므로,
단순 작업 표시 목적으로 추가하지 않는다. 앱이 관리 중인 연결 라벨은 유지한다.

종료는 자신이 만든 terminal만 대상으로 한다. pane 닫기는 terminal을 종료할 수
있으므로 라벨 정리만을 위해 pane을 닫지 않는다.

## 구형 도구와의 경계

`tools/team2_agent.py`의 `run_herdr_label`·`pane_label_for`와
`team2-agent herdr label`은 구형 Herdr CLI/cmux 감지에 연결된 기존 구현이다.
현재 core의 라벨 갱신은 위 `hc label`·`herdr-app do tab.rename` 경로를 사용한다.
구형 환경변수 부재나 wrapper의 no-op을 현재 Herdr 연결 실패로 판단하지 않는다.

근거: 2026-11-10 사용자 요청 — 기존 Herdr CLI를 사용하지 않는 현재 구조로 지침 전환.
