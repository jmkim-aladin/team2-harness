# Phase 52 계획 - 기존 SQL 보고서 메시지 한글화

## 계획

1. 테스트 기대값을 한글 메시지로 바꿔 RED를 확인한다.
2. `LegacySqlCallPlanGenerator`의 `messages` 분기만 최소 변경한다.
3. focused legacy 테스트를 통과시킨다.
4. `docs/legacy-sql/sample-report.json`을 재생성한다.
5. 오래된 영문 legacy SQL 메시지가 남지 않았는지 검색한다.
6. 전체 테스트와 공백 검사를 통과시킨다.
7. 로컬 커밋과 Hermes 상태를 남긴다.

## 성공 기준

- 저장 프로시저 메시지가 한글로 생성된다.
- SELECT SQL 수동 검토 메시지가 한글로 생성된다.
- 변경 SQL 부작용/멱등성 검토 메시지가 한글로 생성된다.
- 알 수 없는 SQL 메시지가 한글로 생성된다.
- `docs/legacy-sql/sample-report.json`에 기존 영문 메시지가 남지 않는다.
- 카운트는 Phase51과 동일하게 SQL 46, SP 34, 미해결 12, SELECT 3, 변경 9, 알 수 없음 0을 유지한다.
