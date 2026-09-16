---
name: ad-kb-publish
description: "Use when the user invokes $ad-kb-publish or /ad:kb-publish, or asks to register or post a document or draft in YouTrack KB. Applies during registration, not ongoing KB synchronization or general link maintenance."
---

# `$ad-kb-publish`

`/ad:kb-publish`의 Codex alias다. 절차의 source of truth는 team2 하네스 command 파일이다.

1. `TEAM2_HARNESS_PATH`를 사용하며 미설정 시 `/Users/jm/Documents/workspace/team2`를 사용한다.
2. `$TEAM2_HARNESS_PATH/.claude/commands/ad/kb-publish.md`를 먼저 읽고 등록 절차를 따른다. 절차는 SoT 한 곳에만 둔다 — 여기 복제하면 한쪽이 낡는다.
3. command 파일에서 참조한 정책과 API 가이드는 하네스 기준 경로로 읽는다.
