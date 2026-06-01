---
name: ad-new-note
description: "Use when the user invokes $ad-new-note, ad new note, /ad:new-note, or asks to create a new DEV2 operations wiki note."
---

# `$ad-new-note`

`/ad:new-note`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/new-note.md`를 먼저 읽고 그 절차를 따른다.
3. command 파일이 참조하는 로컬 위키 경로, 문서명, 언어 정책만 추가로 확인한다.
4. 운영 위키 노트는 기본적으로 `$LOCAL_WIKI_PATH`에 둔다.
5. 파일 생성, 이동, 삭제와 KB 변경은 사용자 승인 후 실행한다.
