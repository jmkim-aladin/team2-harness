# Phase 48 요약: G1 approval decision artifact runner

## 결과

사용자 승인 내용을 `approval-packet.json` 기반 build-only `approval-decision` JSON으로 생성하는 runner를 추가했다. committed approval decision template은 계속 `PENDING` 상태로 남기고, 실제 승인 상태는 `build/g1-evidence/approval-decision-approved.json`에만 생성한다.

## 구현 산출물

- `G1ApprovalDecisionCommandLineRunner`
- `G1ApprovalDecisionCommandLineRunnerTest`
- README의 G1 approval decision runner 사용법 한글 설명
- `docs/g1-evidence/import-fragments.md`의 approval decision runner 절차 한글 설명

## 확인된 동작

- `APPROVED_READ_ONLY_EXPORT`는 명시 옵션으로만 생성된다.
- 생성된 decision은 approval packet의 packet id, request id, read-only query ids, forbidden actions를 그대로 반영한다.
- 승인된 build-only decision으로 G1 import approval guard를 통과할 수 있다.
- local DTSX candidate fragment import는 approval guard를 통과하지만, source type이 `LOCAL_REPO_CANDIDATE`이므로 validation conclusion은 계속 `BLOCKED_LOCAL_CANDIDATE`다.

## 남은 일

실제 운영 증거는 아직 없다. 다음 단계는 operator가 제공하는 실제 `READ_ONLY_EXPORT` fragment source-root를 받아 SQL Agent active package, SP definition, golden output, publish/readback, runtime/network evidence를 import하는 것이다.
