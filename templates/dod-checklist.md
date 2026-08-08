# Definition of Done (DoD) 체크리스트

> Feature 하위 Task는 개발 / 검증 / 배포·운영 반영으로 분리한다 ([티켓 가이드 2-2항](../docs/sprint/ticket-guide.md)).
> 아래 "배포 후" 항목은 **배포·운영 반영 Task의 완료 조건**이며, 개발 Task의 체크리스트로 흡수하지 않는다.
> 검증(내부 테스트 또는 시너지팀 QA)이 필요한 Feature는 해당 Task 종료 없이 개발 Task만으로 Done 처리하지 않는다.

## 필수 항목

- [ ] 코드 변경 완료 및 테스트 통과
- [ ] PR 체크리스트 작성 (영향 범위, 롤백 방법)
- [ ] 코드 리뷰 승인 (최소 1명)
- [ ] (DB/SP 변경 시) 별도 승인 완료 + 단계별 첨부물 완비 (PR: code-review-policy / 배포: release-policy)

## 하네스 갱신 확인

- [ ] 변경 유형별 갱신 대상 확인 — SoT: [docs/harness-guide.md](../docs/harness-guide.md) §하네스 갱신 트리거

## 배포 후

- [ ] smoke test 수행 및 통과
- [ ] 이상 없음 확인
- [ ] YouTrack 티켓 상태 갱신
- [ ] 소요시간 기록
