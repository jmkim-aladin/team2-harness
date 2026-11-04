# 표본 근거 검사 — M2 실행 계약

작업 ID: `TASK-20261104-4560e95349bc`. 범위는 M1 CSV fixture를 모델 호출 없이 집계하고, 주장과 실제 값의 일치 여부를 종료 코드로 제공하는 작은 CLI다. 팀의 완료 정책·스킬·서비스 코드는 변경하지 않는다.

## 공개 경계와 완료 기준

테스트 경계는 `tools/audit_sample_evidence.py`의 실제 CLI다. 입력 파일→stdout JSON·새 증거 디렉터리·종료 코드를 관찰한다. 이 경계는 위키 M2의 실행 검사·입력 식별자·반복 실행 완료 기준을 구체화한다. 내부 함수나 모델 응답을 mock하지 않는다.

- 입력: `--samples` CSV, `--report` JSON, `--output` 새 증거 디렉터리.
- 이 버전의 CSV 계약은 `attempt_id,scenario_id,status`다. 고유성은 명시적으로 `scenario_id`로 센다. attempt_id나 행 전체의 해시는 의미상 고유 표본 수를 대신하지 않는다. ID·status의 양끝 공백을 제거하며 대소문자는 구분한다.
- `status`는 passed/failed/excluded다. 비어 있거나 중복된 attempt_id, 빈 scenario_id, 잘못된 status와 깨진 CSV는 근거 부족으로 반환한다. 다른 입력 형식·업무적 고유성 추론은 이번 범위 밖이다.
- report의 `claimed_unique_scenarios`와 `claimed_pass_rate`를 실제 값과 비교한다. rate는 passed/(passed+failed)이며 제외 건수와 전체 행 기준 비율도 별도로 노출한다. 수치 비교의 절대 오차 허용은 부동소수점 표현 차이를 위한 1e-12이고, 표시용 반올림을 추정하지 않는다.
- JSON의 중복 키·비정상 숫자와 잘못된 claim 타입은 확인 불가다. report가 `data`를 제공하면 보고서 디렉터리 기준으로 해소한 경로가 실제 `--samples`와 같아야 한다. 해당 파일이나 설명의 내용을 명령으로 실행하지 않는다.
- 결과: 전체 시도·고유 표본·중복 시도·통과·실패·제외·실제 비교 대상과 분모, 입력 SHA-256·경로, 제공된 seed·설명. seed는 주장 metadata일 뿐 실제 무작위성의 증거로 판정하지 않는다.
- PASS/0: 유효한 입력에서 주장한 고유 수·비율이 일치하고 실패·제외가 없다. 명시한 고유 수와 일치하는 반복 측정은 허용하며 중복 수는 숨기지 않는다.
- FAIL/1: 유효한 입력에서 주장 불일치 또는 실제 실패가 관찰됐다. 이 경우 제외 건수가 있더라도 관찰된 실패를 보존한다.
- INCONCLUSIVE/2: 누락·잘못된 입력, 0건·비교 대상 0건, 또는 다른 실패가 없더라도 제외가 남아 전체 검사를 확인하지 못했다. 이는 배포 승인 판정이 아니라 이 도구의 표본 근거 판정이다.
- 원본 입력은 읽기만 한다. 출력 디렉터리는 새로 만들고 기존 증거를 덮어쓰지 않는다. 같은 입력·도구로 반복하면 같은 집계·판정을 내며, 실행 시점·argv는 별도 receipt로 남긴다.

## 검증 사례

M1의 `2,000회 / 고유 381개 / passed 1,800 / failed 100 / excluded 100` 입력은 FAIL이어야 한다. 서로 다른 2,000개가 전부 통과하고 주장도 일치하는 입력은 PASS여야 한다. 손으로 확인 가능한 작은 사례로 실패·제외·입력 누락과 의도적인 반복을 확인한다.

회귀는 실제 subprocess CLI로 실행하고, 원본·이전 증거 보존과 반복 실행을 확인한다. 현재 M1 출력과 fixture는 수정하지 않는다.

## 실행법

repo 루트 `/Users/jm/Documents/workspace/team2`에서 실행한다. 출력은 아직 없는 경로를 지정한다.

```bash
python3 tools/audit_sample_evidence.py \
  --samples docs/verification/harness-verification-quality/inputs/repeated-samples/samples.csv \
  --report docs/verification/harness-verification-quality/inputs/repeated-samples/report.json \
  --output /tmp/team2-sample-audit-new
```

이 원본은 결함을 심은 합성 fixture이므로 기대 종료는 **1/FAIL**이다. stdout과 출력 디렉터리의 `result.json`에 같은 결과를 남기고, `receipt.json`에는 시점·cwd·argv·Python·도구 SHA-256을 남긴다. `--output`이 이미 존재하면 원래 증거를 수정하지 않고 종료 2를 반환한다.

CLI 회귀는 다음 명령으로 실행한다.

```bash
python3 -m unittest discover -s tests -p test_audit_sample_evidence.py -v
```

## 2026-11-04 실행 결과

HEAD `63668bbdf1f5f95dda98fc3b5ac4eae92c99873f`, 브랜치 `team2/harness-verification-quality`의 로컬 변경을 검증했다. 소스·테스트 파일 SHA-256과 실제 argv·입력 hash·종료 코드는 [/Users/jm/Documents/workspace/team2/docs/verification/harness-verification-quality/m2-execution/acceptance.json](/Users/jm/Documents/workspace/team2/docs/verification/harness-verification-quality/m2-execution/acceptance.json)에 있다.

| 입력 | 기대·실제 종료 | 실제 관찰 |
|---|---|---|
| M1 원본 | 1 / FAIL | 2,000회·고유 381개·중복 1,619회·실패 100·제외 100, 비교 분모 1,900·통과율 약 94.7368% |
| 고유 2,000개 전부 통과 | 0 / PASS | 고유 2,000·중복 0·실패 0·제외 0, 분모 2,000·통과율 100% |
| 같은 정상 입력 반복 | 0 / PASS | result JSON 동일, 입력과 앞선 증거 불변 |
| 0건 | 2 / INCONCLUSIVE | 시도 0·분모 0, 통과율 null |
| 정상 1 + 제외 1 | 2 / INCONCLUSIVE | 비교 통과율 100%여도 전체 검사는 미확인 |
| 정상 1 + 실패 1 | 1 / FAIL | 보고서의 50%와 일치해도 실제 실패 보존 |
| 입력 파일 누락 | 2 / INCONCLUSIVE | 성공률을 만들지 않고 입력 오류 기록 |
| 기존 출력 경로로 재실행 | 2 / INCONCLUSIVE | 기존 result hash 유지 |

고유 2,000개 입력은 `scenario_id=S0000..S1999`로 만든 별도 합성 대조 입력이다. 실제 서비스의 생성기를 고쳤거나 무작위성을 입증한 결과가 아니다. 증거는 `m2-execution/inputs`, 각 실행의 `result.json`·`receipt.json`과 stdout·stderr에 보존했다.

테스트는 실제 CLI를 호출하는 11개 회귀를 추가했다. 위 사례 외에 빈 키·중복 attempt·잘못된 status·CSV 열 수·JSON 타입/숫자/중복 키·다른 파일 참조·선언한 반복 측정을 확인한다. 7회의 red→green 기록과 최종 전체 실행 로그는 `m2-execution/checks`에 있다.

- 전체 root 테스트: 476건 OK(새 회귀 11개 포함).
- 전체 tools 테스트: 279건 OK, 1건 skipped. 합계 754건 실행 통과·1건 미실행이다.
- 기존 M1 입력과 앞선 증거 불변을 확인했고, 하네스·위키 lint 결과를 acceptance에 연결한다. 모델 세션은 이번 단계에서 실행하지 않았다.

기존 도구 목록과 M1 실행 계약에서 이 CLI로 연결했다. 일반 업무에 새로운 필드나 자동 실행을 강제하는 정책·스킬 변경은 하지 않았다. 이후 소스·입력이 바뀌면 receipt의 hash를 대조해 영향받는 범위를 재검증한다.
