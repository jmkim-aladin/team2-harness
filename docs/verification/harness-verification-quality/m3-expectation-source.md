# 기대값 근거 연결 — M3 실행·검증 계약

공통 작업 ID: `TASK-20261104-4560e95349bc`. M1·M2 산출물을 보존하고, 기대값의 출처를 기존 완료·인계 증거에 연결한다. 실행 상태는 위키 계획이 원장이다.

## 범위와 완료 기준

- 현재 테스트 엔지니어 기준이 이미 구현식을 복제한 assertion을 지적한다는 M1 관찰을 재사용한다. 새로운 스킬·공개 도구·전 작업 필수 필드를 추가하지 않는다.
- 계산·정책 판정에 해당할 때 기대값의 근거를 기존 완료 조건·검증 증거에 연결하는 짧은 정의를 공통 증거 계약에 둔다. 구현 계획 양식에는 그 정의로 가는 참조만 둔다.
- 완료 기준: 기대값→출처·버전→독립 확인 방법→실제 관찰 결과가 추적되는 합성 사례가 있고, 원문 부재와 구현식 복제를 독립 근거로 승인하지 않는다. 작은 문서 수정에는 추가 검증을 요구하지 않는다.
- 변경 전후의 입력·schema·모델·설정·예산은 M1 최종 v2에 고정한다. 기존 baseline을 재사용하고, 후보에게는 같은 사례와 갱신한 공통 증거 계약만 제공한다. 원본 baseline·입력·suite는 수정하지 않는다.
- 단일 실행의 일치·차이를 품질 향상으로 일반화하지 않는다. 조건 불일치나 모델 출력의 기존 실패는 숨기지 않고 개별 관찰과 비교 한계를 남긴다.
- 문구 존재를 확인하는 새 단위 테스트는 만들지 않는다. 실제 산출물·도구 호출의 행동 비교, 출처 추적 예제와 기존 전체 검사로 검증한다.

## 변경 지점

- 정의: [/Users/jm/Documents/workspace/team2/docs/agents/verification.md](/Users/jm/Documents/workspace/team2/docs/agents/verification.md) §기대값의 근거.
- 참조: [/Users/jm/Documents/workspace/team2/docs/sprint/work-prep-note-template.md](/Users/jm/Documents/workspace/team2/docs/sprint/work-prep-note-template.md) §구현 계획 기준.
- 기존 검출 기준은 [/Users/jm/Documents/workspace/team2/docs/code-review/personas/test-engineer.md](/Users/jm/Documents/workspace/team2/docs/code-review/personas/test-engineer.md)를 재사용한다.

## 증거 구성

`m3-execution`에 실제 후보 prompt·출력·CLI 기록, 기존 평가기의 비교 결과와 독립 출처 추적을 남긴다. 후보용 복제 runner에서 repo 경로와 중립 라벨 B만 바꾸고, 실행 절차는 M1과 동일하게 유지한다. fixture digest에는 정책 snapshot을 제외하고, policy digest에는 변경된 공통 증거 계약을 포함한다.

범위가 정해진 합성 할인 사례에서 정책 원문이 없으면 1,700원·1,701원 중 어느 값을 채택할지 확정하지 않는다. 별도로 명시한 합성 원문과 손계산을 연결해 기대값·관찰값 대조를 보여 준다. 이 예제는 실제 서비스 정책이나 구현의 검증 결과가 아니다.

## 2026-11-04 검증 결과

공통 증거 계약에 조건부 정의를 추가하고 구현 계획에 참조 한 줄을 연결했다. 기존 테스트 엔지니어 기준·완료 조건의 원장은 유지했다. 새 필드·스킬·전 작업 필수 검사는 추가하지 않았다.

현재 브랜치는 `team2/harness-verification-quality`, HEAD는 `63668bbdf1f5f95dda98fc3b5ac4eae92c99873f`다. M1 최종 v2의 기존 A와 갱신한 공통 계약을 받은 B를 비교했다. 입력·schema·CLI·모델·설정·예산의 기록 조건은 일치하고 policy digest만 달랐다. 네 prompt를 직접 대조해 공통 계약 본문 외의 요청·자료 안내가 같음을 확인했다.

| 사례 | A / B 사전 assertion | 추가 확인 |
|---|---|---|
| 작은 문서 수정 | PASS / PASS | B의 추가 작업은 빈 배열이고 오타·개행만 수정함 |
| 할인 기대값 출처 부재 | PASS / PASS | B도 구현식을 복사한 1,701원을 독립 근거로 승인하지 않고 절사 정책 부재를 명시함 |
| 반복 표본 | FAIL / PASS | A의 본문·ready 모순은 보존함. 한 번의 변화로 개선 효과를 주장하지 않으며 실제 집계는 M2 도구로 확인함 |
| 정산 | PASS / PASS | 기존 assertion은 ready·R1 언급만 검사한다. 아래의 계산 범위 오류는 이 PASS에 가려졌음 |

기존 평가기의 전체 비교는 **FAIL/종료 1**이다. baseline의 실패를 보존하는 도구 규약에 따른 결과이며 B가 4개 assertion을 충족했다는 이유로 전체 PASS로 바꾸지 않았다. 원본 결과는 `comparison.json`, 실제 실행 로그는 `candidate/cases`에 있다.

독립 수동 확인에서는 B 정산 응답이 O1 잔액 6,000원을 aggregate `current_net_won`과 비교하면서 O2의 5,000원을 합계에서 누락한 것을 발견했다. 두 주문 합계는 `15,000 − 3,000 − 1,000 = 11,000원`이다. 해당 출력과 오류를 `observations.json`에 보존했고, M4에서 주문별·전체 합계가 드러나는 산출물의 유용성을 판정할 입력으로 넘긴다. 이 오류를 정책 변경의 회귀나 전체 모델 오류율로 단정하지 않는다.

### 출처 추적 예제

`source-trace.json`은 입력·정책 원문·검사 스크립트의 hash와 방법·관찰값을 연결한다.

| 구분 | 기대값·출처 | 관찰과 판단 |
|---|---|---|
| M1 원문 부재 | 기대값 미확인, source_documents 빈 목록 | 기록된 1,701원과 테스트 종료 0을 승인 근거로 쓰지 않고 INCONCLUSIVE 유지 |
| 별도 합성 정책 적용 | synthetic-discount-v1의 품목별 절사 + 손계산·Decimal → 1,700원 | 기존 fixture의 복제 기대값 1,701원과 달라 FAIL |
| 손계산 정답 예제 | 같은 합성 원문·버전과 독립 계산 → 1,700원 | 예제로 제공한 고정값 1,700원과 일치해 PASS. 애플리케이션 실행 결과는 아님 |

합성 정책은 실제 서비스의 미확인 원문을 대신하지 않는다. 재현은 새 출력 경로로 실행한다.

```bash
python3 docs/verification/harness-verification-quality/m3-execution/check_source_example.py \
  --output /tmp/team2-expectation-trace-new.json
```

후보 재현과 비교도 기존 원본을 덮어쓰지 않고 실행한다.

```bash
python3 docs/verification/harness-verification-quality/m3-execution/candidate-input/run_baseline.py \
  --output /tmp/team2-m3-candidate-new
python3 tools/evaluate_harness_behavior.py \
  --suite docs/verification/harness-verification-quality/m3-execution/candidate-input/suite.json \
  --baseline docs/verification/harness-verification-quality/baseline-20261104-v2 \
  --candidate /tmp/team2-m3-candidate-new --output /tmp/team2-m3-comparison-new.json
```

### 검증 범위와 한계

- 전체 root 테스트 476건 OK, tools 테스트 279건 OK(1건 skipped). 실행 통과 754건과 미실행 1건을 구분한다. 새 문구만 확인하는 단위 테스트는 추가하지 않았다.
- 조건·소스·입력 hash·완료 기준과 하네스·위키 lint 결과는 [/Users/jm/Documents/workspace/team2/docs/verification/harness-verification-quality/m3-execution/acceptance.json](/Users/jm/Documents/workspace/team2/docs/verification/harness-verification-quality/m3-execution/acceptance.json)에 연결한다. M1·M2 원본 입력과 서비스 코드는 변경하지 않았다.
- M3의 완료는 출처 연결과 해당 경로의 제한된 행동 확인이다. 기존에도 근거 부재를 검출했으므로 검출력 향상을 입증하지 않았다. 단일 후보·기록된 설정의 비교이며 실제 서비스 정책·구현·업무 전체의 정확성을 보증하지 않는다.
- 자동 assertion과 실제 의미의 정확성은 다르다. 수동으로 찾은 정산 범위 오류는 실패 관찰로 남긴다. 모델 호출의 시간·토큰 절감을 주장하지 않는다.
