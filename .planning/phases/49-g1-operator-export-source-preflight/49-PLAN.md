# Phase 49 계획: G1 operator export source preflight

## 목표

operator가 제공한 G1 fragment source-root를 import하기 전에 preflight report로 판정한다.

## 작업

1. preflight checker 테스트를 먼저 추가한다.
   - complete `READ_ONLY_EXPORT`는 `PASSED_READY_TO_IMPORT`
   - template placeholder는 `BLOCKED_TEMPLATE_PLACEHOLDER`
   - local repo 후보는 `BLOCKED_LOCAL_REPO_CANDIDATE`
   - 필수 fragment 누락은 `FAILED_MISSING_FRAGMENT`

2. preflight checker와 report model을 구현한다.
   - source-root 절대 경로
   - conclusion
   - sourceType
   - evidencePackId
   - fragment count
   - missing/placeholder fragment 목록

3. command runner를 추가한다.
   - `--partner.integration.g1-operator-preflight.enabled=true`
   - `--partner.integration.g1-operator-preflight.source-root`
   - `--partner.integration.g1-operator-preflight.report`
   - `--partner.integration.g1-operator-preflight.fail-on-not-ready`

4. 실제 로컬 template/local candidate source-root에 runner를 실행한다.

5. README와 G1 fragment import guide를 한글로 갱신한다.

## 검증

- focused preflight tests
- 실제 template/local candidate preflight runner
- G1 focused tests
- full `./gradlew test --rerun-tasks`
