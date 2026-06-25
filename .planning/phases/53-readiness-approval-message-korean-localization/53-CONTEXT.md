# Phase 53 맥락 - 준비도와 승인 패킷 메시지 한글화

## 배경

Phase 52에서 legacy SQL plan report 메시지를 한글화했지만, `docs/readiness/sample-report.json`과 `docs/g1-evidence/approval-packet.json`의 gate 메시지는 여전히 영어였다.

approval packet은 readiness gate 메시지를 그대로 담아 운영자/승인자에게 전달되는 산출물이므로, 개발 산출물 한글화 기준에 맞춰야 한다.

## 목표

- `MigrationReadinessEvaluator`가 생성하는 gate 메시지를 한글 중심으로 바꾼다.
- `MigrationReadinessCommandLineRunner`의 실패 메시지도 한글로 바꾼다.
- readiness sample report와 G1 approval packet을 재생성한다.
- enum/status/CLI option 같은 실행 계약은 유지한다.

## 제외

- EquivalenceGate 자체 report 메시지 한글화
- Local smoke/publish/readback runner 자체 오류 메시지 한글화
- DB/SP/운영 접근
