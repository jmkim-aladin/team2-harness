# 하네스 행동 평가 실행 가이드

평가 조건과 삭제 판단의 SoT는 [거버넌스의 변경 통제](../policies/harness-governance-policy.md#변경-통제)다. 이 문서는 이미 수행한 두 실행의 **실제 산출물**을 같은 기준으로 비교하는 도구 사용법이다. 에이전트를 자동 실행하거나 답변의 사실성을 자동 보증하지 않는다.

## 실행 준비

1. 변경한 규칙이 발동하는 대표 요청과 입력 fixture를 고정한다. 성공·실패 기준을 먼저 suite에 적는다. 정답·평가 설명은 후보 작업 공간 밖에 둔다.
2. 변경 전후 정책만 달리하고 같은 task·저장소 상태·모델·설정·예산을 사용한다. 각 후보를 새 세션에서 실행하며 다른 후보와 평가 정보를 제공하지 않는다.
3. 실제 runner의 종료·timeout 기록과 산출물을 별도 실행 디렉터리에 보존한다. `receipt.json`은 평가자가 실행 기록을 근거로 작성하며 후보의 `PASS` 자기 보고를 옮기지 않는다.
4. 아래 도구로 A/B를 비교한 뒤 주장에 맞는 증거인지 사람이 읽는다. 규칙 로드·도구 호출을 주장하려면 실제 호출 기록이 필요하다. JSON에 `tested: true`가 있다는 것만으로 테스트 실행을 증명할 수 없다.

형식 검사는 별도로 유지한다. 모델이 다르거나 실행 설정을 확인할 수 없으면 산출물 관찰만 보고하고 변경 효과의 통제 비교는 미확인으로 남긴다. 도구가 검사하는 것은 **기록된 조건의 일치**이며 runner 기록 자체를 인증하지 않는다.

## 입력 계약

`suite.json` 예시. `task`는 후보에게 동일하게 제공한 요청이다. assertion은 후보에게 보여주지 않는다.

```json
{
  "schema_version": 1,
  "suite_id": "delivery-evidence",
  "cases": [{
    "id": "notes",
    "task": "제공된 검증 기록으로 완료 여부를 판단해 findings.json에 기록하라.",
    "assertions": [
      {"type": "json_field_equals", "path": "findings.json", "field": "delivery_complete", "expected": false},
      {"type": "file_absent", "path": "published.txt"}
    ]
  }]
}
```

각 실행 디렉터리에 `receipt.json`과 `cases/notes/`의 원본 산출물을 둔다. A/B의 `variant`와 정책 파일의 `skill_digest`만 다르게 적는다. fixture digest는 동일 요청·입력·저장소 상태를 식별하고 정책 차이는 제외한다.

```json
{
  "schema_version": 1,
  "variant": "A",
  "conditions": {
    "confirmed": true,
    "fixture_digest": "sha256:<입력 snapshot>",
    "model": "<실제 모델>",
    "settings": {"effort": "<실제 설정>"},
    "budget": {"max_tokens": 10000},
    "skill_digest": "sha256:<해당 정책 snapshot>"
  },
  "cases": {
    "notes": {"exit_code": 0, "timed_out": false, "artifact_dir": "cases/notes"}
  }
}
```

`confirmed`는 평가자가 실제 runner 기록으로 공통 조건을 확인했을 때만 `true`다. 모델·설정·예산을 확인하지 못했으면 `false`로 기록하며, 이 경우 각 산출물 판정과 별개로 전체 비교는 INCONCLUSIVE다. 이 값도 후보에게 작성시키지 않는다.

예산은 실제 runner에 설정한 값을 기록한다. 예시의 숫자를 복사해서 설정한 것으로 취급하지 않는다. 추가 condition 필드도 키 존재 여부까지 비교하므로 실행 환경·도구 버전 등 결과를 좌우하는 조건을 담을 수 있다. 실행별 시간·비용·원본 로그 포인터는 receipt의 별도 필드에 남긴다.

지원 assertion:

| type | 비교 대상 | 용도·한계 |
|---|---|---|
| `json_field_equals` | JSON의 `field`와 `expected` | 구조화된 요청 산출물. boolean과 숫자를 구별한다. field는 점 경로, JSON Pointer, 문자열/인덱스 목록 지원 |
| `text_contains` | 텍스트 파일의 `literal` | 문서에 요구한 내용의 존재 검사. 원칙 이름 재등장을 행동 증거로 쓰지 않는다 |
| `file_absent` | 지정 경로의 부재 | 금지 산출물 존재 검사. dangling symlink도 존재로 판정하며 경로 밖 쓰기·외부 게시의 부재까지 증명하지 않는다 |

## 실행과 판정

```bash
python3 tools/evaluate_harness_behavior.py \
  --suite /tmp/behavior/suite.json \
  --baseline /tmp/behavior/run-a \
  --candidate /tmp/behavior/run-b \
  --output /tmp/behavior/evaluation.json
```

- `PASS` / 종료 0: 기록된 공통 조건이 같고 두 실행의 모든 assertion을 직접 확인했다.
- `FAIL` / 종료 1: 관찰값이 기대값과 다르다. A 실패·B 통과도 전체는 FAIL이며 `runs.A/B`를 따로 읽는다. 관찰된 FAIL은 다른 assertion의 누락으로 가려지지 않는다.
- `INCONCLUSIVE` / 종료 2: 실행 실패·timeout·누락/잘못된 증거·조건 미확인/불일치·동일 정책 digest 등으로 변경을 비교할 수 없다. 조건 자체가 비교 불가이면 전체는 INCONCLUSIVE이고 관찰된 실패는 개별 run에 남는다. 잘못된 CLI/suite 인자도 종료 2이며 결과 JSON이 생성되지 않을 수 있다.

출력은 입력 suite·run 밖에 둔다. 원본 증거는 수정하지 않으며 같은 입력의 재평가는 결정적이다. 각 assertion의 관찰값과 근거 경로를 결과에 남긴다. 민감한 값은 fixture에 넣지 않는다.

둘 다 통과했다는 한 번의 결과로 문장 삭제나 품질 향상을 정당화하지 않는다. 실제 사용자 요청 분포·회귀·비용에 관한 결론은 해당 자료와 반복 관찰이 있을 때만 내린다. 실제 CLI 동작의 독립적인 검사는 [하네스 링크 검증 계약](verification/harness-links.md)을 참조한다.
