---
name: ad-granola-sync
description: "Use when the user invokes $ad-granola-sync, ad granola sync, /ad:granola-sync, or asks to import, fetch, sync, or Korean-title Granola meeting notes into the DEV2 wiki/Tolaría."
---

# `$ad-granola-sync`

`/ad:granola-sync`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`로 기준 경로를 잡는다.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/granola-sync.md`를 먼저 읽고 그 절차를 따른다.
3. command 파일이 참조하는 vault 경로, Keychain 정책, title-map 규칙만 추가로 확인한다.
4. Granola API key 값은 출력하지 않는다.
5. Granola 원본은 읽기 전용으로 두고, 회의록 저장/갱신은 `$LOCAL_WIKI_PATH`의 `wiki/processes/meetings/`에 수행한다.
6. `--apply`, daily note 생성, transcript 포함은 사용자 의도 또는 명시 요청이 있을 때만 실행한다.
