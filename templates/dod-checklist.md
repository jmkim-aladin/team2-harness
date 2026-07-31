# Definition of Done (DoD) 체크리스트

> Feature 하위 Task는 개발 / 검증 / 배포·운영 반영으로 분리한다 ([티켓 가이드 2-2항](../docs/sprint/ticket-guide.md)).
> 아래 "배포 후" 항목은 **배포·운영 반영 Task의 완료 조건**이며, 개발 Task의 체크리스트로 흡수하지 않는다.
> 검증(내부 테스트 또는 시너지팀 QA)이 필요한 Feature는 해당 Task 종료 없이 개발 Task만으로 Done 처리하지 않는다.

## 필수 항목

- [ ] 코드 변경 완료 및 테스트 통과
- [ ] PR 체크리스트 작성 (영향 범위, 롤백 방법)
- [ ] 코드 리뷰 승인 (최소 1명)
- [ ] (DB/SP 변경 시) 별도 승인 완료
- [ ] (DB/SP 변경 시) 롤백 스크립트 첨부

## 하네스 갱신 확인

아래 변경이 있었다면 해당 하네스 파일을 갱신:

| 변경 유형 | 갱신 대상 |
|-----------|-----------|
| 신규 외부 연동 추가 | AGENTS.md (의존 시스템) |
| 주요 API 경로 변경 | AGENTS.md (엔드포인트) |
| 배포/롤백 절차 변경 | RUNBOOK.md |
| DB/SP 영향 범위 변경 | LEGACY_BOUNDARY.md |
| 서비스 책임 이동 | service-manifest.yaml |
| 장애/위험 포인트 발견 | AGENTS.md (주의사항) |
| 현대화 진행 상태 변경 | modernization-plan.md |
| 금지 패턴 추가 | AGENTS.md (금지 사항) |

## 배포 후

- [ ] smoke test 수행 및 통과
- [ ] 이상 없음 확인
- [ ] YouTrack 티켓 상태 갱신
- [ ] 소요시간 기록
