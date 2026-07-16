# Phase 53 계획 - 준비도와 승인 패킷 메시지 한글화

## 계획

1. readiness 테스트의 사용자 메시지 기대값을 한글로 바꿔 RED를 확인한다.
2. `MigrationReadinessEvaluator`의 gate 메시지를 한글화한다.
3. `MigrationReadinessCommandLineRunner` 실패 메시지를 한글화한다.
4. focused readiness 테스트를 통과시킨다.
5. readiness sample report와 approval packet을 재생성한다.
6. 오래된 readiness/approval 영문 메시지가 남지 않았는지 검색한다.
7. 전체 테스트와 공백 검사를 통과시킨다.
8. 로컬 커밋과 Hermes 상태를 남긴다.

## 성공 기준

- `docs/readiness/sample-report.json`의 gate 메시지가 한글 중심으로 생성된다.
- `docs/g1-evidence/approval-packet.json`의 blocking gate 메시지가 한글 중심으로 생성된다.
- readiness gate count는 11개, passed 4개, blocked 7개, failed 0개를 유지한다.
- approval packet은 `APPROVAL_REQUIRED`, blocking gate 7개를 유지한다.
- focused readiness tests, actual readiness runner, approval packet runner, full tests가 통과한다.
