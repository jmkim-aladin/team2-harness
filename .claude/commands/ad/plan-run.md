---
description: 계획 실행 — vault 계획의 internal milestone 하나를 실행하고 진행·근거를 기록
disable-model-invocation: true
---

# 계획 실행 (plan-run)

`/ad:plan`이 만든 vault 계획에서 **internal milestone 하나**를 선택해 구현·검증하고 진행 상태와 evidence를 되쓴다. YouTrack 티켓이 없어도 실행할 수 있다.

## 자리

- vault 계획은 목표·단계·진행 상태의 원장이다.
- 정책·계약·schema·production code의 실행 spec은 대상 repository 규칙을 따른다. `CHG-*` 체계가 있으면 해당 milestone의 canonical change를 만들거나 재사용한다.
- `execution_mode=ticket`인 milestone은 YouTrack 5W1H가 spec이다. 계획에는 링크와 상태만 남기고 `/ad:implement`로 실행한다.
- 이 command는 code와 vault를 변경하므로 사용자가 `/ad:plan-run` 또는 `$ad-plan-run`으로 시점을 정한다.

## 단계 현황 계약

계획에는 다음 표를 둔다.

| 단계 | status | execution_mode | execution_ref | evidence |
|---|---|---|---|---|
| 1. 예시 | planned | internal | - | - |

- `status`: `planned`, `in-progress`, `completed`, `blocked`
- `execution_mode`: `internal`, `ticket`
- `execution_ref`: repository change/spec 또는 `[[dev2-XXXX]]`; 아직 없으면 `-`
- `evidence`: test·acceptance·evidence 문서 링크; 아직 없으면 `-`

기존 계획에 표가 없으면 상세 단계에서 같은 정보를 추출해 표를 먼저 추가한다. 상세 단계와 표의 status를 이중으로 기록하지 않는다.

## 실행 루프

### 1. 계획과 milestone 선택

1. `LOCAL_WIKI_PATH`를 확인하고 인자로 받은 plan 경로·wikilink·제목을 해소한다.
2. milestone 인자가 있으면 그 행을, 없으면 첫 `in-progress`, 그다음 첫 `planned` 행을 선택한다.
3. 한 호출에서 milestone 하나만 실행한다. 완료된 milestone을 다시 실행하려면 사용자가 명시해야 한다.
4. 계획, 연결된 결정·용어집과 대상 repository의 `AGENTS.md`를 읽는다. repository 경로가 없으면 frontmatter의 `service_id`로 `$TEAM2_HARNESS_PATH/catalog/{service_id}.yaml`에서 찾는다.

### 2. 착수 가능성 판정

다음 네 항목이 있으면 착수한다.

- 도달 상태
- 범위와 비범위
- 판정 가능한 acceptance
- 대상 repository 또는 산출 위치

결정이 빠져 결과가 달라지면 구현하지 않고 plan의 `미결`과 해당 행을 `blocked`로 갱신한 뒤 추천안과 질문 하나를 반환한다. 조사로 해소 가능한 사실은 먼저 조회한다.

### 3. 진행 시작 기록

- 선택한 행을 `in-progress`로 바꾼다.
- `execution_ref`에 기존 spec을 연결한다. repository 고유 governance가 필요하면 canonical change 초안을 만든 뒤 연결한다.
- `## 진행 기록`에 날짜, milestone과 착수 판단을 한 줄 추가한다.
- vault 변경 뒤 `tools/lint_vault.py --files ...`를 실행한다.

### 4. 구현과 검증

`$TEAM2_HARNESS_PATH/vendor/mattpocock/implement/SKILL.md`와 `policies/overrides/mattpocock.md`를 읽고 적용한다.

- pre-agreed seam에서 TDD를 사용한다.
- 좁은 test·typecheck를 반복하고 마지막에 대상 repository의 full verification을 실행한다.
- 실패한 가정은 숨기지 않고 plan 진행 기록과 repository change/evidence에 남긴다.
- milestone 밖의 다음 단계는 구현하지 않는다.

### 5. 종료 전이

Acceptance와 full verification이 통과하면:

- 행을 `completed`로 전이한다.
- `execution_ref`와 `evidence`를 실제 canonical artifact로 갱신한다.
- 진행 기록에 결과와 다음 `planned` milestone을 적는다.

같은 blocking condition이 반복돼 사용자 결정이나 외부 상태 없이는 진행할 수 없으면:

- 행을 `blocked`로 전이한다.
- `decision_status: blocked`와 해제 조건을 기록한다.

문서가 실제 상태를 반영한 뒤 vault lint를 다시 실행한다. ticket이 생기면 `execution_mode=ticket`과 `[[dev2-XXXX]]`로 전환하고 상세 구현 내용은 ticket에 넘긴다.

## 게이트

- YouTrack·KB·push·PR·merge·배포와 외부 시스템 변경은 사용자 승인 후 수행한다.
- **커밋 전 사용자 확인**을 받는다. team2 하네스 예외는 `[TEAM2]`, 티켓 작업은 `[DEV2-XXXX]` 형식을 사용한다.
- evidence 없이 `planned` 또는 `in-progress`를 `completed`로 전이하지 않는다.
- plan과 ticket/repository spec에 같은 세부 요구를 이중 유지하지 않는다.
- 마감 리뷰는 사용자가 `/ad:code-review` 시점을 정한다.

ARGUMENTS: $ARGUMENTS
