# Phase 52 맥락 - 기존 SQL 보고서 메시지 한글화

## 배경

사용자는 모든 개발 산출물을 한글로 작성하라고 지시했다. README는 한글화되었지만, `docs/legacy-sql/sample-report.json`의 `messages` 값은 여전히 영어였다.

legacy SQL plan report는 G1/SP 검토와 수동 어댑터 설계의 근거가 되는 개발 산출물이므로, 사람이 읽는 메시지는 한글이어야 한다. enum 값, 설정 키, 클래스명, adapter boundary 이름은 실행 계약이므로 유지한다.

## 목표

- `LegacySqlCallPlanGenerator`가 생성하는 사용자 노출 메시지를 한글로 바꾼다.
- 저장 프로시저, SELECT SQL, 변경 SQL, 알 수 없는 SQL 메시지를 모두 한글로 제공한다.
- 커밋된 legacy SQL sample report를 재생성한다.

## 제외

- enum/status 이름 변경
- 설정 키/CLI 옵션 변경
- readiness 메시지 한글화
- DB/SP/SQL 실행
