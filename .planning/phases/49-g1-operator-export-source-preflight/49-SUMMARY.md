# Phase 49 요약: G1 operator export source preflight

## 결과

G1 operator source-root를 import 전에 검사하는 preflight checker와 command runner를 추가했다.

## 구현 산출물

- `G1OperatorExportPreflightReport`
- `G1OperatorExportPreflightConclusion`
- `G1OperatorExportPreflightChecker`
- `G1OperatorExportPreflightCommandLineRunner`
- preflight checker/runner 테스트
- README와 `docs/g1-evidence/import-fragments.md` 한글 절차 추가

## 확인된 동작

- 완성된 `READ_ONLY_EXPORT` fragment는 `PASSED_READY_TO_IMPORT`로 통과한다.
- placeholder가 남은 template은 `BLOCKED_TEMPLATE_PLACEHOLDER`로 차단한다.
- local DTSX 후보 fragment는 `BLOCKED_LOCAL_REPO_CANDIDATE`로 차단한다.
- 필수 fragment가 누락되면 `FAILED_MISSING_FRAGMENT`로 실패한다.

## 실제 로컬 실행

- `build/g1-evidence/fragment-template-cli-preflight-report.json`: `BLOCKED_TEMPLATE_PLACEHOLDER`
- `build/g1-evidence/local-dtsx-candidates-preflight-report.json`: `BLOCKED_LOCAL_REPO_CANDIDATE`

## 남은 일

실제 operator `READ_ONLY_EXPORT` fragment source-root가 아직 없다. source-root가 제공되면 preflight 통과 후 approval-guarded import와 G1 validation을 실행해야 한다.
