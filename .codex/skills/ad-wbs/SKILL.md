---
name: ad-wbs
description: "[주기·수시] Use when asked to export a YouTrack issue tree as a WBS or Gantt spreadsheet/HTML. Also /ad:wbs."
---

# `$ad-wbs`

`/ad:wbs`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/wbs.md`를 먼저 읽고 그 절차를 따른다. 절차는 SoT 한 곳에만 둔다 — 여기 복제하면 한쪽이 낡는다.
3. 계산·판정 규칙은 `tools/export_wbs.py`와 `tools/README.md` §export_wbs.py만 추가로 확인한다.
4. YouTrack은 조회만 하고, 티켓 변경은 사용자 승인 후 실행한다.
