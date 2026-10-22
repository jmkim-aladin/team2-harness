---
description: '[상시·협업] Paperclip 등록 — DEV2 티켓을 로컬 Paperclip Inbox에 넣고 프로젝트로 분류. "paperclip에 넣어줘", "에이전트에 맡겨줘" 류에'
---

# Paperclip 등록 (paperclip-dispatch)

YouTrack DEV2 티켓을 로컬 Paperclip(`http://127.0.0.1:3100`) 이슈로 등록·분류하고, 분석이 승인된 이슈 아래에 다음 일을 하위 이슈로 만든다. 판정과 쓰기는 `tools/paperclip_import_ticket.py`가 하고 이 스킬은 실행과 보고만 맡는다 — cron·routine도 같은 도구를 부르므로 규칙을 여기 두면 두 경로가 갈린다. 구성 SoT: [templates/paperclip/README.md](../../../templates/paperclip/README.md). 프로젝트 정책·대상 이름: `templates/paperclip/pilot.json`.

흐름: 등록 → 자동 분석(새 이슈를 「티켓 분석」·Ticket Prep todo로, `pilot.json` `autoAnalyze`) → 승인 대기 → 사람 승인(done) → `--from`으로 하위 이슈·종료는 사람이 정한다. 내가 만든 티켓(reporter=나)과 자동 분석이 꺼진 경우는 Inbox(프로젝트 없음)로 들어가고 `--project "티켓 분석"`으로 분류한다. `--inbox`는 실행마다 깨움 보정(Ticket Prep 담당 todo 중 실행 없는 것, 최대 `wakeMax`건)도 한다. 멈추려면 화면에서 Ticket Prep을 일시정지한다 — 등록은 계속되고 분석은 재개 후 깨움 보정이 이어 간다.

## 사용법

```
/ad:paperclip-dispatch DEV2-8499 [DEV2-…]                          # 등록 — 자동 분석 대상이면 Ticket Prep todo, 아니면 Board backlog(Inbox)
/ad:paperclip-dispatch --inbox                                    # 나에게 할당된·내가 만들지 않은 최근 14일 Task·Bug 일괄 + 깨움 보정
/ad:paperclip-dispatch --project "티켓 분석" DEV2-12779             # 분류 — 격리 없음·승인 단계만 (Ticket Prep이 work-prep)
/ad:paperclip-dispatch --project "쇼핑 데이터 추출" --from ALA-5      # 하위 이슈 — 승인된 분석 ALA-5 아래, 격리·리뷰→승인
/ad:paperclip-dispatch --project "쇼핑 데이터 추출" --from ALA-5 DEV2-12800  # 사람이 YouTrack에 새 Task를 만든 경우
```

프로젝트별 정책(격리 여부·단계)은 `pilot.json` `projects`에 있다. 거기 없는 프로젝트 이름은 error다.

## 실행

```bash
TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-$HOME/Documents/workspace/team2}"
python3 "$TEAM2_HARNESS_PATH/tools/paperclip_import_ticket.py" {인자}
```

인자는 사용자가 준 그대로 넘기고, `--dry-run`은 사용자가 미리보기를 원할 때 붙인다. 도구는 YouTrack을 읽기만 하고 Paperclip에만 쓴다. 같은 티켓을 다시 넣으면 skipped·unchanged로 끝나서 재실행이 안전하다.

완료 기준: 티켓마다 `created`·`skipped`·`updated`·`unchanged`·`dry_run`·`error` 중 하나가 나옴.

## 보고

- 티켓당 한 줄: 결과, 이슈 URL(`http://127.0.0.1:3100/ALA/issues/ALA-n`), 배분 프로젝트(불일치면 "프로젝트 없음"), 자동 분석 여부(안 했으면 사유), error면 사유
- `--inbox`면 깨움 보정 한 줄: 깨운 수, 실행 중·다음 실행·에이전트 멈춤 건수. `최근 실행 멈춤`이 있으면 그 이슈의 실패 실행을 보고 화면에서 직접 다시 돌리라고 안내한다
- 다음 행동 안내:
  - 프로젝트 없는 이슈 → 화면 Inbox "Mine"에서 보고, 맡길 것은 `--project "티켓 분석" {ID}`로 분류한다. 화면에서 프로젝트만 바꾸면 격리·정책이 붙지 않는다
  - 실행 시작 → 자동 분석 이슈는 이미 시작됐다. 그 밖에는 화면에서 담당을 그 프로젝트 에이전트(SQL Writer·Ticket Prep)로 바꾸고 상태를 todo로 올린다. backlog에서는 할당해도 에이전트를 깨우지 않는다
  - 승인·반려 → API로 보낸다. 코멘트와 상태 변경이 한 요청이어야 해서다 — README §에이전트
  - 분석 승인(done) 후 → 분석 보고의 다음 단계대로 `--project "<프로젝트>" --from ALA-n [DEV2-####]`로 하위 이슈를 만든다
- `이미 done`·`다른 프로젝트 소속` error면 옮기지 않았다고 알리고, 사유에 적힌 `--from` 명령을 안내한다 — 프로젝트를 바꾸면 그 단계의 승인 기록이 초기화된다
- `분석 승인 전: 현재 <status>`면 부모 분석 이슈가 승인(done)된 뒤 다시 하라고 안내한다
- `분석 먼저`면 `--from` 없는 `--project`는 「티켓 분석」만 받는다고 알리고, 분석 분류부터 안내한다
- `Paperclip 서버 응답 없음`이면 `launchctl print gui/$(id -u)/com.team2.paperclip`로 서비스 상태를 확인하라고 안내한다
- `YouTrack 토큰 없음`이면 `python3 tools/cred.py set youtrack-token`을 안내한다
- `담당자 불일치: <login>`이면 그 티켓은 쓰지 않았다고 알린다 — 토큰 사용자가 담당인 티켓만 받는다. 맡길 티켓이면 YouTrack 담당자부터 확인하게 안내한다

ARGUMENTS: $ARGUMENTS
