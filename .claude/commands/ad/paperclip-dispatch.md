---
description: '[상시·협업] Paperclip 등록 — DEV2 티켓을 로컬 Paperclip Inbox에 넣고 프로젝트로 분류. "paperclip에 넣어줘", "에이전트에 맡겨줘" 류에'
---

# Paperclip 등록 (paperclip-dispatch)

YouTrack DEV2 티켓을 로컬 Paperclip(`http://127.0.0.1:3100`) 이슈로 등록·분류한다. 판정과 쓰기는 `tools/paperclip_import_ticket.py`가 하고 이 스킬은 실행과 보고만 맡는다 — cron·routine도 같은 도구를 부르므로 규칙을 여기 두면 두 경로가 갈린다. 구성 SoT: [templates/paperclip/README.md](../../../templates/paperclip/README.md). 배분 규칙·대상 이름: `templates/paperclip/pilot.json`.

## 사용법

```
/ad:paperclip-dispatch DEV2-8499 [DEV2-…]                     # 등록 — Board 담당 backlog, 규칙 일치 시 프로젝트·정책
/ad:paperclip-dispatch --inbox                               # 내 미해결 DEV2 티켓 일괄 (pilot.json inboxQuery)
/ad:paperclip-dispatch --project "쇼핑 데이터 추출" DEV2-8499   # 분류 — 프로젝트·격리·리뷰→승인 정책 부착
```

## 실행

```bash
TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-$HOME/Documents/workspace/team2}"
python3 "$TEAM2_HARNESS_PATH/tools/paperclip_import_ticket.py" {인자}
```

인자는 사용자가 준 그대로 넘기고, `--dry-run`은 사용자가 미리보기를 원할 때 붙인다. 도구는 YouTrack을 읽기만 하고 Paperclip에만 쓴다. 같은 티켓을 다시 넣으면 skipped·unchanged로 끝나서 재실행이 안전하다.

완료 기준: 티켓마다 `created`·`skipped`·`updated`·`unchanged`·`dry_run`·`error` 중 하나가 나옴.

## 보고

- 티켓당 한 줄: 결과, 이슈 URL(`http://127.0.0.1:3100/ALA/issues/ALA-n`), 배분 프로젝트(불일치면 "프로젝트 없음"), error면 사유
- 다음 행동 안내:
  - 프로젝트 없는 이슈 → 화면 Inbox "Mine"에서 보고, 맡길 것은 `--project "<이름>" {ID}`로 분류한다. 화면에서 프로젝트만 바꾸면 격리·정책이 붙지 않는다
  - 실행 시작 → 화면에서 담당을 SQL Writer로 바꾸고 상태를 todo로 올린다. backlog에서는 할당해도 에이전트를 깨우지 않는다
  - 승인·반려 → API로 보낸다. 코멘트와 상태 변경이 한 요청이어야 해서다 — README §에이전트
- `Paperclip 서버 응답 없음`이면 `launchctl print gui/$(id -u)/com.team2.paperclip`로 서비스 상태를 확인하라고 안내한다
- `YouTrack 토큰 없음`이면 `python3 tools/cred.py set youtrack-token`을 안내한다

ARGUMENTS: $ARGUMENTS
