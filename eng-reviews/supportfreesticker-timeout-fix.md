---
type: concept
title: 'Eng Review: 무료응원 SP 타임아웃 수정'
ingested_via: put_page
ingested_at: '2026-07-16T08:21:03.340Z'
source_kind: put_page
tags:
  - eng-review
  - supportfreesticker-timeout-fix
---

# 무료응원 SP 타임아웃 수정 (2026-07-16)

주 196건 SQL Timeout 원인: 응원 1건당 전체 재계산(NoteSticker COUNT/SUM + 시리즈 집계 JOIN) + 핫로우 락(NoteSortOrder/TobelogSeries) 컨보이 + 이벤트 #76149 non-sargable 스캔.

## 결정 (14건 리뷰 → 전부 반영)
- @IsFree=1 O(1) 증분 경로 전환 + 시리즈 증분/검색큐 확장 (재계산 집계 필터 동일 조건)
- 핵심쓰기(INSERT NoteSticker+차감)만 XACT_ABORT 트랜잭션, 커밋 후 부가처리 실패는 성공 반환+로그 (재시도 이중응원 방지)
- 이벤트 블록 기간가드 선행+sargable 재작성 (V2+유료 SP 동일)
- CustomerSticker_Support 잔량가드+@Deducted OUTPUT(하위호환), 실패 시 1회 재선택 재시도
- 정산 커서 DISTINCT (적립금 중복 지급 차단)
- NoteSortOrder_RecountDaily 야간 배치 신설 (증분 오차 자기치유 복원)
- 배포 순서: Support→Counting→RecountDaily→V2→SupportSticker→SettleJob (tests/DEPLOY.md)
- 성공지표: 배포 후 1주 주간 타임아웃 196→20 미만

## 보류 (TODOS.md)
큐 분리, V1 DROP, 개인사본 정리, ResetDaily 이중발급, StickerId=1 필터 기획확인, 이벤트 종료 시 블록 삭제
