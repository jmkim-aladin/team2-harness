# Phase 48 Plan - G1 승인 decision 산출물 생성기

## 목표

사용자 승인 내용을 build-only approval decision JSON으로 기록하고, import guard가 이 decision을 받아들이는지 검증한다.

## 작업

1. approval decision runner failing test를 추가한다.
2. approval packet을 읽어 `G1ApprovalDecision`을 생성하는 runner를 구현한다.
3. runner는 `decision-status=APPROVED_READ_ONLY_EXPORT`를 명시하지 않으면 승인 decision을 쓰지 않게 한다.
4. build-only approval decision으로 local DTSX candidate fragment를 guarded import한다.
5. README와 G1 fragment guide를 한글로 갱신한다.
6. focused G1 tests와 full test suite를 실행한다.

## 검증

- `./gradlew test --tests 'kr.co.aladin.partner.integration.batch.g1.*'`
- actual approval decision runner
- guarded G1 import runner
- `./gradlew test --rerun-tasks`
- `git diff --check`
