# 월별 멤버십 쿠폰 반영과 운영 검수 자료

## Knowledge

- [Microsoft Learn: CREATE PROCEDURE (Transact-SQL)](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-procedure-transact-sql?view=sql-server-ver17)
  `CREATE OR ALTER`, 프로시저 파라미터, 생성 시점 검사 범위를 확인할 때 사용한다.
- [Microsoft Learn: THROW (Transact-SQL)](https://learn.microsoft.com/en-us/sql/t-sql/language-elements/throw-transact-sql?view=sql-server-ver17)
  사용자 정의 오류 번호와 실행 중단 의미를 해석할 때 사용한다.
- [Microsoft Learn: TRY...CATCH (Transact-SQL)](https://learn.microsoft.com/en-us/sql/t-sql/language-elements/try-catch-transact-sql?view=sql-server-ver17)
  테스트에서 오류를 결과 행으로 바꿔 판정하는 방법에 사용한다.
- [Microsoft Learn: sqlcmd utility](https://learn.microsoft.com/en-us/sql/tools/sqlcmd/sqlcmd-utility?view=sql-server-ver16)
  macOS에서 SQL 파일과 조회 쿼리를 dev SQL Server에 실행할 때 사용한다.
- 월별 멤버십 쿠폰 발급 SP: `$SHOP_DB_SCRIPT_PATH/databases/WebCatalog/StoredProcedures/Coupon_NewMake_MembershipMontly.sql`
  `52100~52107` 검증과 실제 쿠폰번호 생성 전 쓰기 게이트의 로컬 source of truth다.
- 월별 멤버십 쿠폰 프리플라이트 SP: `$SHOP_DB_SCRIPT_PATH/databases/WebCatalog/StoredProcedures/Coupon_NewMake_MembershipMontly_Preflight.sql`
  대상 월·기대 NType·만료일·월 문구를 읽기 전용으로 확인하는 로컬 source of truth다.
- 월별 멤버십 쿠폰 통합 검수 SQL: `$SHOP_DB_SCRIPT_PATH/scripts/verify-membership-coupon-month.sql`
  Preflight, 데이터 무변경, 예외 함수, 일반·커피 마스터, 커피 월 매핑, 등급변경 Event를 한 번에 판정한다. DB 배포 객체가 아니라 작업자 실행 스크립트다.
- DEV2-8628 작업 노트: 로컬 Obsidian vault의 `wiki/processes/tickets/dev2-8628.md`
  9월 티켓 요구값, dev 반영 범위, 실제 검증 결과와 남은 조건을 확인할 때 사용한다.

## Wisdom (Communities)

- 개발2팀 DB/SP 리뷰
  공유 WebCatalog 객체 변경과 운영 반영 전에 서비스 owner·팀장에게 영향 범위와 검증 근거를 검토받는 실무 피드백 경로다.

## Gaps

- dev CouponNType·Event 마스터 데이터의 등록 책임자와 등록 시점은 별도 운영 절차 확인이 필요하다. 정상 경로는 한국어 서버 Collation의 SQL Server 2022 Docker에서 검증했다.
- SQL Agent/SSIS가 실제로 전달하는 실행 파라미터는 배치 운영 환경에서 추가 확인이 필요하다.
