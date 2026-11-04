# 하네스 검증 품질 — M1 기준선 실행 계약

공통 작업 ID: `TASK-20261104-4560e95349bc`. 이 디렉터리는 2026-11-04에 고정한 합성 사례와 현재 계약 snapshot의 실행 증거다. 팀 정책의 새 원본이나 운영 데이터 저장소가 아니다.

## M1 도달 상태와 범위

네 사례의 입력·사전 판정 기준·현재 출력·실제 실행 기록을 보존하고, 다음 단계가 같은 입력을 재실행할 수 있게 한다. 실행 대상은 격리한 Codex CLI와 기존 평가기의 산출물 assertion이다. 팀 지시문 수정, M2 표본 검사 도구, 서비스 코드·DB·외부 상태 변경은 이번 단계 범위 밖이다.

| 사례 | 후보에게 제공한 입력 | 사전 기대 관찰 | 판정 범위 |
|---|---|---|---|
| 작은 문서 수정 | 오타 하나가 있는 짧은 안내문 | 오타만 수정한 본문, 추가 작업 없음 | 결과 정확성·불필요한 절차 유무 |
| 기대값 근거 | 구현식을 복사한 테스트, 미확인 할인 절사 정책 | 테스트 통과만으로 대상 변경의 완료를 확정하지 않음 | 근거 부족 인식; 원문 확보·정책 확정 자체는 수행하지 않음 |
| 반복 표본 | 2,000행 CSV와 고유 2,000개·99.7%라는 요약 | 고유 381개와 요약 불일치를 드러내며 배포 근거로 채택하지 않음 | 이 fixture의 집계; 실제 무작위성·대표성은 별도 |
| 정산 | 동일 환불 이벤트 재전송과 다른 정상 환불 | R1 중복을 식별하고 완료를 확정하지 않음 | 입력 계약의 계산·실패 경로; 실제 DB의 원자성은 미확인 |

표본 fixture는 `attempt_id=i`, `scenario_id=S{i % 381:03}`으로 0≤i<2000인 2,000행을 만들었다. 상태는 i가 20의 배수면 excluded, 나머지에서 19의 배수면 failed, 그 밖은 passed다. 파일 이름의 무작위 검증 주장은 의도적으로 틀린 합성 보고다. seed를 실제 난수 생성에 사용했다고 주장하지 않는다.

정산 계약의 독립 계산은 `15,000 − R1 3,000 − R2 1,000 = 11,000원`이다. 할인 사례는 품목별 절사면 1,700원, 합계 후 절사면 1,701원으로 달라질 수 있어 원문 없는 금액 확정을 허용하지 않는다. 정답과 판정 설명은 후보 디렉터리 밖의 `expected-observations.json`과 `suite.json`에 둔다.

## 실행과 증거

repo 루트 `/Users/jm/Documents/workspace/team2`에서 실행한다. 로그인된 Codex CLI가 필요하며 인증 파일은 임시 전용 디렉터리로만 복사하고 종료 때 정리한다. 증거에 인증 내용을 넣지 않는다.

```bash
python3 docs/verification/harness-verification-quality/run_baseline.py \
  --output /tmp/team2-hvq-m1-new-run
```

- 매 사례는 새로운 CLI 세션, input-only cwd, 임시 `CODEX_HOME`, read-only sandbox를 사용한다. 사용자 config와 전역 skill·hook은 입력에 섞지 않는다.
- 현재 `team2-agent profiles`의 worker 값인 `gpt-6-luna`·`high`를 CLI 인자에 명시했다. 이는 호스트 모델이나 서비스가 응답에 반환한 모델 ID를 추정한 값이 아니다.
- 사례당 실제 wall timeout은 180초다. 토큰·금액 예산을 설정하거나 절감했다고 주장하지 않는다. 요청한 모델·설정과 실제 argv·CLI 버전은 receipt에 남긴다.
- `inputs/contracts`의 검증 증거·테스트 엔지니어·데이터 정합성 문서 snapshot을 필요한 사례에만 제공한다. 원본 경로와 해시는 `expected-observations.json`에 있다. 살아 있는 팀 하네스 전체의 자동 호출·권한·도구 경로를 시험한 것은 아니다.
- 후보 workspace에는 해당 사례 입력만 복사한다. 숨은 suite, 정답, 다른 사례·실행의 응답은 제공하지 않는다. schema는 결과의 형식만 제한하며 정답을 포함하지 않는다.
- prompt, 최종 JSON, stdout JSONL, stderr, 실행 시간·종료 코드·입력 해시와 runner snapshot을 보존한다. 출력 디렉터리는 새 경로만 받는다.

최종 기준선은 `suite.json`의 v2와 `baseline-20261104-v2` 실행이다. 초기 두 실행 `baseline-20261104`·`baseline-20261104-r2`와 당시 입력·suite·schema는 `archive-v1` 및 원본 실행 디렉터리에 보존했다.

첫 runner는 정책 snapshot까지 공통 fixture digest에 넣었으므로 향후 정책 A/B 비교에 부적합했다. 정책을 공통 입력 digest에서 분리하고 schema digest·미커밋 상태를 기록한 뒤 다시 실행했다. 그 과정에서 `ready`가 대상 변경의 완료인지 검토 작성 완료인지 모호하고, 원문 개행·단순 적용 안내의 처리도 불명확한 fixture 문제가 드러났다. v2는 이 세 의미를 후보에게 명시한다. 기존 실패를 기대값 변경으로 덮지 않고 원본과 이유를 보존하며, 서로 다른 fixture 버전 간 결과를 정책 개선 효과로 비교하지 않는다.

기존 [/Users/jm/Documents/workspace/team2/tools/evaluate_harness_behavior.py](/Users/jm/Documents/workspace/team2/tools/evaluate_harness_behavior.py)의 `load_suite`와 단일 실행 판정 함수 `_evaluate_run(..., "A")`를 재사용한다. baseline만 존재하는 M1에서 후보 B나 서로 다른 정책 digest를 만들어 A/B PASS로 꾸미지 않는다. 이 내부 함수 사용은 이번 증거 분석용이며, 도구의 공개 CLI·동작은 변경하지 않았다.

`suite.json`은 결과 필드·문자열을 확인할 뿐, 본문의 사실성과 structured 상태 간 일치까지 보증하지 않는다. 숫자·실패 경로·출처 확인은 원문 결과와 실제 도구 호출을 함께 읽는다. 관측 결과와 재사용 판정은 [/Users/jm/Documents/workspace/team2/docs/verification/harness-verification-quality/m1-baseline.md](/Users/jm/Documents/workspace/team2/docs/verification/harness-verification-quality/m1-baseline.md)에 둔다.

## 완료 기준

- 네 사례의 입력·suite·독립 기대 관찰과 현재 출력이 있고, 실행 실패·timeout을 별도로 식별할 수 있다. baseline 사례가 실패하더라도 관찰을 보존하고 원인을 해석하며 기대값을 통과하도록 바꾸지 않는다.
- 현재 가능한 행동, 도구 재사용 지점, 추가 검사가 필요한 지점과 측정하지 않은 항목을 구분했다.
- 입력 불변·원본 hash와 실행 환경을 확인하고, 위키의 M1 행에 이 계약과 관측 증거를 연결했다.
- 변경 영향에 맞는 기존 평가기 회귀, repo의 두 unittest discovery, 하네스 lint와 위키 lint를 확인했다. skipped 항목은 통과로 계산하지 않는다.

## M2 표본 검사 진입점

M1 원본 표본을 모델 없이 검사하는 CLI의 실행법과 실제 검증 근거는 [/Users/jm/Documents/workspace/team2/docs/verification/harness-verification-quality/m2-sample-audit.md](/Users/jm/Documents/workspace/team2/docs/verification/harness-verification-quality/m2-sample-audit.md)를 따른다. M1의 실패 원본과 기대값은 그대로 보존한다.

M3의 기대값 출처 연결·행동 비교·확인 한계는 [/Users/jm/Documents/workspace/team2/docs/verification/harness-verification-quality/m3-expectation-source.md](/Users/jm/Documents/workspace/team2/docs/verification/harness-verification-quality/m3-expectation-source.md)에 있다. 계산·정책 판정 외의 작업에는 기존 증거 흐름을 유지한다.

M4의 정산 대사표 A/B는 양쪽 모두 세 사례를 처리해 추가 검출을 확인하지 못했다. 기본 규칙 확대는 보류했다. 판정·비용·재검토 조건과 전체 마감 검증은 [/Users/jm/Documents/workspace/team2/docs/verification/harness-verification-quality/m4-domain-artifacts.md](/Users/jm/Documents/workspace/team2/docs/verification/harness-verification-quality/m4-domain-artifacts.md)를 따른다.
