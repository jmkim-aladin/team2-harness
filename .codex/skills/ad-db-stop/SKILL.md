---
name: ad-db-stop
description: "[상시·운영 DB] Stop all production DB queries managed by the current Mac user's team2 executor. Use for $ad-db-stop, /ad:db-stop, or an explicit request to stop/cancel running production DB queries."
---

# 운영 DB 조회 취소

`/Users/jm/Documents/workspace/team2/.claude/commands/ad/db-stop.md`를 읽고 실행한다. 이 파일이 중단 절차의 source of truth다.

호출 위치와 관계없이 문서의 절대 경로를 사용한다. 사용자의 중단 요청으로 즉시 실행한다. 이 스킬의 `stop`은 현재 조회를 취소하고 기존 승인을 무효화하는 일시 중단이다. 오류 없는 사용자 취소에서 서버 종료 확인과 `active=null`, `phase=idle`이 확인되면 다음 요청을 자동으로 받을 수 있다. 오류·timeout은 서버 종료 증거가 확인돼도 active 슬롯만 정리하고 차단은 유지한다. 종료 미확인·실행기 재시작도 차단을 유지한다. 차단 해제는 다음 조회의 `preview`(재개 action 포함 검토) → 사용자 명시 승인 → `run`으로 하고, 독립 `resume`은 사용자가 직접 요청할 때만 쓴다. CLI는 command 문서의 운영판 경로(`current/db_prod_client.py`)를 쓰고, 그 경로가 실패할 때만 개발 저장소 CLI로 `stop`을 재시도한다. 지속적인 전체 차단은 command 문서에 적힌 별도 `emergency-stop` 경로를 사용한다. 등록·설명 요청에서는 설치·안내로 범위를 한정한다. 의도: 다른 저장소에서도 같은 전역 중단 상태를 사용하고 요청한 작업 범위를 지킨다.
