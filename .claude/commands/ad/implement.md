---
description: '[개발·구현] 티켓 노트 구현 계획의 슬라이스 하나를 TDD로 구현하고 멈춤 (커밋은 확인 후)'
disable-model-invocation: true
---

# 구현 (implement)

`$TEAM2_HARNESS_PATH/vendor/mattpocock/implement/SKILL.md`를 읽고 그 절차를 따르되, 아래 팀 오버라이드가 우선한다 ([policies/overrides/mattpocock.md](../../../policies/overrides/mattpocock.md)).

## 입력

- spec·완료 조건의 SoT는 YouTrack 티켓 본문(5W1H)이고, 노트 `## 구현 계획`은 그 완료 조건을 관찰 가능하게 구체화한 **실행 계획**이다. 둘이 어긋나면 티켓 본문을 따르고 보고한다 — 완료 조건의 SoT가 둘이면 판정 기준이 갈린다. 노트: `$LOCAL_WIKI_PATH/wiki/processes/tickets/dev2-{nnnn}.md`, 형식 SoT: [work-prep-note-template.md](../../../docs/sprint/work-prep-note-template.md) §구현 계획 기준
- 구현 계획이 없으면 `/ad:work-prep DEV2-{NNNN}`을 먼저 권한다 — 슬라이스·검증 명령이 없으면 seam을 그 자리에서 지어내게 된다. 사용자가 원하면 티켓만으로 진행하되 seam과 검증 명령을 먼저 합의한다
- 대상 슬라이스: 인자로 준 것(`S2`), 없으면 첫 미체크 슬라이스

## 슬라이스 실행 (one slice at a time)

한 번 호출에 슬라이스 하나 — 병렬 슬라이스 구현은 사용자 지시가 있을 때만. 기본 순서 (상황에 맞게 조정 가능):

1. 슬라이스 seam에서 `tdd` red → green. 확인할 AC를 테스트 이름이나 관찰 절차로 옮긴다
2. 구현 계획의 검증 명령을 실행한다 — 타입체크·단일 테스트 파일은 수시로, 전체 테스트는 마지막 슬라이스에서. 빌드 통과는 동작의 증거가 아니다
3. 노트를 갱신한다 — 슬라이스 `[x]`, `## 진행 메모`에 `{YYYY-MM-DD} S{n} 완료 — {검증 명령·결과 한 줄}`, `판단 요약 > 다음 행동`을 다음 슬라이스로
4. 보고하고 멈춘다 — 변경 파일, 검증 결과, 커밋 제안(`[DEV2-{NNNN}] {슬라이스 요약}`), 다음 슬라이스. 다음 진행은 사용자가 지시한다

- 범위 밖 기록: 슬라이스 밖 문제는 `진행 메모`에 `범위 밖: …` 한 줄로 남기고 넘어간다 — 슬라이스 diff에 섞이면 리뷰·롤백 단위가 깨진다
- 노트 `구현 중 신호`에 걸리거나 티켓 전제가 깨지면 그 자리에서 멈추고 보고한다 — 신호별 다음 단계는 노트에 있다
- 마지막 슬라이스면 전체 테스트 결과와 함께 `/ad:code-review-self`(자기 PR) 또는 `/ad:code-review`를 안내한다

근거: 2026-10-21 사용자 결정 — implement는 슬라이스 하나씩, 끝나면 노트 체크 후 멈춘다. 3팩 비교 검토 — Osmani incremental(슬라이스 하나씩·범위 밖은 기록만).

## 팀 오버라이드

- 커밋은 슬라이스 단위로 제안하고 **사용자 확인 후** 실행한다 — 팀 INVARIANT. 형식 `[{이슈ID}] 작업 내용`
- 마감 리뷰는 `/ad:code-review` (내장 `/code-review` 아님) — 사용자 호출이라 시점은 사람이 정한다

ARGUMENTS: $ARGUMENTS
