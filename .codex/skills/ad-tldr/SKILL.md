---
name: ad-tldr
description: "Use when the user invokes $ad-tldr, ad tldr, /ad:tldr, or asks for a one-page TL;DR architecture overview of a repository or project."
---

# `$ad-tldr`

`/ad:tldr` Codex alias. 실제 절차는 team2 하네스 command 파일이 source of truth다.

## 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/tldr.md`를 먼저 읽고 그 절차와 섹션 규격을 따른다.
3. 고도를 아키텍처에 고정한다. 코드 예시, 디렉토리 트리, 진행 상태는 넣지 않는다.
4. mermaid 2개를 쓴다 — 구성 `graph TB`, 프로세스 `flowchart TD`. 다이어그램이 갈라놓은 분기를 표로 반복하지 않는다.
5. 기본 산출 위치는 대상 저장소의 gitignore된 경로다. `--keep`일 때만 커밋 대상 `docs/`에 쓴다.
6. YouTrack, KB, vault, git 커밋, 배포는 수행하지 않는다.
