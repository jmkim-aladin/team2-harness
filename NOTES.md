# Teaching Notes

- 언어: 한국어.
- 선호 방식: 개념 설명보다 실제 명령·기대 결과·판정 기준 중심.
- 안전 기준: dev 읽기 전용 테스트 우선, 실제 쿠폰 발급과 회원 데이터 변경은 제외.
- 현재 실습 사례: DEV2-8628 2026년 9월 멤버십 쿠폰과 DEV2-8924 발급 전 설정 오류 차단.
- 운영 최소 반영: `Coupon_NewMake_MembershipMontly`, `Coupon_NewMake_MembershipMontly_Preflight` 2개.
- 기존 월별 객체 3개는 재배포보다 통합 검수를 우선한다. 합격은 종료 코드 0, 최종 PASS 6개, 쿠폰 건수 무변경이다.
