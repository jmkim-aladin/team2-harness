# Phase 48 Context - G1 승인 decision 산출물 생성기

## 배경

사용자가 G1 read-only evidence 수집을 승인했다. 현재 repo에는 `docs/g1-evidence/approval-decision-template.json`이 있지만, 이 파일은 의도적으로 `PENDING`이라 import guard에서 승인으로 인정되지 않는다.

승인 사실을 기록하더라도 committed template을 승인 상태로 바꾸면 실수로 운영 증거가 승인된 것처럼 보일 수 있다. 따라서 approval packet을 입력으로 받아 build-only approval decision artifact를 생성하는 runner가 필요하다.

## 범위

- approval packet 기반 build-only approval decision JSON 생성.
- generated decision으로 guarded import 경로 검증.
- committed template은 `PENDING` 유지.

## 비범위

- 운영 DB/SQL Agent 조회.
- 운영 DTSX/SP/golden output 수집.
- production 변경.
- G1 evidence pass 주장.
