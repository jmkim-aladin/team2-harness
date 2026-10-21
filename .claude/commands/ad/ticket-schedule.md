---
description: '[주기·주간] 계획 일정 지정 — planned 티켓 시작예정일·완료목표일을 건별 확인 후 코멘트로 일괄 입력'
disable-model-invocation: true
---

# 계획 일정 지정 (ticket-schedule)

팀장의 주간업무 자동 취합(월요일 오후, 하네스 밖)은 티켓 코멘트에서 날짜를 읽는다. 날짜 코멘트가 없는 계획 항목은 일정 칸이 빈 채로 나간다. 이 스킬은 `{YYMM}-planned` 티켓의 **계획 일정**을 한 건씩 확인받아 표준 형식 코멘트로 채운다. 기본: 월요일 오전까지 실행.

- 대상 판정·코멘트 쓰기 = `tools/ticket_schedule.py`(결정적). 날짜 제안·확인 대화 = 이 스킬
- 용어: vault glossary `$LOCAL_WIKI_PATH/wiki/glossary/planned-schedule.md`(계획 일정)·`unscheduled.md`(일정 미지정)

## 사용법

```
/ad:ticket-schedule                # 이번 달 {YYMM}-planned, 팀 전체
/ad:ticket-schedule 2611           # 다음 달 계획 초안 (월 마지막 주)
/ad:ticket-schedule @jmkim @heum2  # 담당자 login으로 좁히기
```

## 규칙

| 대상 | 요구하는 계획 일정 | 코멘트 본문 |
|---|---|---|
| 착수 전(Open) Feature | Feature만 | `시작예정일: YYYY-MM-DD` |
| 진행중 Feature | Feature 자신 | `완료목표일: YYYY-MM-DD` |
| 진행중 Feature의 미해결 하위 Task (태그 무관) | Task 자기 상태 기준 — Open이면 시작예정일, 진행이면 완료목표일 | 위와 같음 |

- 가장 최근 코멘트가 유효하다. 재지정에 사유를 받지 않으며, 지연 판정도 새 날짜 기준이 된다
- 레거시 라벨(`예상 시작일`·`예상 종료일`·`예상 완료일` + ISO 또는 `M월 D일`)은 지정된 것으로 인정한다. 문장형("10월 3주차…")은 형식 불명으로 순회에 넣는다
- 날짜는 사용자가 확인한 값만 쓴다. 근거가 없으면 빈칸으로 묻는다 — 월말·생성일 같은 추정값은 지연 신호를 가린다
- 이 스킬이 YouTrack에 하는 일은 코멘트 추가뿐이다. 상태·필드·태그는 그대로 둔다

## 실행 지침

### 0. 토큰 owner 확인

[youtrack/api-guide.md](../../../youtrack/api-guide.md) §토큰 owner 규칙의 `users/me`로 토큰이 본인 계정인지 확인한다. 코멘트 author가 토큰 owner로 남으므로 불일치하면 중단하고 본인 토큰 교체를 요청한다.

완료 기준: 본인 확인, 또는 중단.

### 1. 스캔

```bash
TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-$HOME/Documents/workspace/team2}"
OUT="${TMPDIR:-/tmp}/ticket-schedule-{YYMM}"   # 업무 데이터라 repo 밖
python3 "$TEAM2_HARNESS_PATH/tools/ticket_schedule.py" scan --month {YYMM} [--assignee {login} ...] --out "$OUT-scan.json"
```

`{YYMM}` 기본값은 오늘이 속한 달이다. 담당자 인자는 `@`를 떼고 `--assignee`에 넘긴다. 결과의 `counts`와, `ok`가 아닌 항목을 담당자별 표(ID·제목·상태·status)로 보여준다. `ok`는 개수만 보여준다.

완료 기준: 순회 대상(`overdue`·`unscheduled`·`unparsed`) 목록 확정. 0건이면 "전부 지정됨"을 보고하고 종료.

### 2. 한 건씩 확인

scan 정렬(담당자 → Feature → 하위 Task) 그대로 한 건씩 묻는다. 질문 규율: 한 번에 하나, 추천안과 함께.

```
[3/12] DEV2-9143 [만권당] 열람제어 — QA · Feature · Open · 김정민
일정 미지정 → 시작예정일 필요
근거: "10월 3주차(19일~22일)에 작업 예정입니다." (10/12 코멘트)
```

- **제안 날짜**: 근거가 있을 때만 만든다. 우선순위는 `hints`의 문장형 날짜 → `when`(5W1H When 절) → 형제 Task의 순서다. 기간 표현이면 start는 첫날, due는 끝날을 쓴다
- **overdue**: 기존 날짜와 경과일을 보여주고 새 날짜를 묻는다. 실제로 착수했는데 상태가 Open인 경우처럼 상태 갱신이 필요해 보이면 결과 보고에 모은다
- **선택지**: `제안일 수락(추천)` · `건너뛰기` · `여기서 멈추고 미리보기`. 직접 입력은 Other로 받는다. `10/22`·`10월 22일` 입력은 대상 월의 연도로 ISO로 바꾼다
- 오늘 이전 날짜를 시작예정일로 받으면 "바로 지연으로 표시됨"을 한 줄 알리고 그대로 받는다

완료 기준: 순회 대상 전부에 답(지정·건너뜀)이 있거나 사용자가 멈춤을 고름.

### 3. 미리보기 → 승인 게이트

지정한 항목으로 `$OUT-plan.json`(`{"entries":[{"id","kind","date"}]}`)을 쓰고 `apply --plan "$OUT-plan.json" --dry-run` 결과를 표(ID·제목·담당·코멘트 본문)로 보여준 뒤 한 번 승인받는다 — 작성 / 수정 / 취소. 근거: YouTrack 쓰기는 사용자 확인 후 수행한다(CLAUDE.md 핵심 규칙).

완료 기준: 승인, 또는 취소(아무것도 쓰지 않고 종료).

### 4. 작성

```bash
python3 "$TEAM2_HARNESS_PATH/tools/ticket_schedule.py" apply --plan "$OUT-plan.json"
```

도구가 이슈 상태를 다시 읽는다. 그 사이 상태가 바뀌어 요구 라벨이 달라진 항목은 `skipped: state_changed`, 같은 날짜가 이미 최신 라벨인 항목은 `skipped: already_set`으로 건너뛴다. 코멘트 POST는 재시도하지 않으므로 `error` 항목은 결과를 확인한 뒤 다시 실행한다 — `already_set`이 중복 작성을 막는다.

완료 기준: 모든 entry에 `posted`·`skipped`·`error` 중 하나가 있음.

### 5. 결과 보고

- posted / skipped / error 건수. skipped·error는 ID와 이유
- 남은 일정 미지정(건너뛴 항목)을 담당자별로
- 상태 갱신이 필요해 보이는 overdue 항목 — 상태 변경은 담당자 몫(`/ad:work-close` 등)
