---
name: ad-work-prep
description: "[개발·착수 준비] Use when the user invokes $ad-work-prep, ad work prep, /ad:work-prep, asks to prepare DEV2 ticket work (strength, implementation plan), or asks to close/mark done/finish a DEV2 ticket wiki note once work is done."
---

# `$ad-work-prep`

`/ad:work-prep`의 Codex `$` alias다. 실제 절차의 source of truth는 team2 하네스 command 파일이다.

## 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`.
2. 반드시 `$TEAM2_HARNESS_PATH/.claude/commands/ad/work-prep.md`를 먼저 읽고 그 절차를 따른다. 절차는 SoT 한 곳에만 둔다 — 여기 복제하면 한쪽이 낡는다.
3. 참조 정책, 티켓, 로컬 위키 경로만 추가 확인한다.
4. 위키 노트 생성·갱신·종료 반영은 사용자 확인 없이 진행한다. 개발 DB 조회·DML은 `policies/local-credentials-policy.md` 사전 동의 범위, 그 밖의 YouTrack·git·DB/prod 작업은 SoT 승인 경로를 따른다.
5. cmux/herdr 라벨은 `team2-agent herdr label DEV2-{NNNN} "{제목}"` 한 줄로 붙인다. 스키마 SoT는 `$TEAM2_HARNESS_PATH/docs/cmux-herdr-labeling.md`다 — 여기 재진술하면 낡는다.
6. 검증된 SQL은 위키 노트에 먼저 남기고, `data-requests-dev2` 등록은 별도 단계로 처리한다.
7. 티켓 종료/완료/마감/닫힘 요청 또는 완료 보고 시 로컬 위키에 `ticket_status: done`, 필요 시 `decision_status: resolved`, 종료 기록을 자동 반영한다.
