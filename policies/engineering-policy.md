# 개발 2팀 엔지니어링 정책

> 전사 클린 아키텍처 가이드: [REF-A-1958](https://aladincommunication.youtrack.cloud/articles/REF-A-1958) (YouTrack KB)
> 전사 Git Flow: [REF-A-625](https://aladincommunication.youtrack.cloud/articles/REF-A-625) (YouTrack KB)
> 필요 시 `/ad:team2-kb-read {문서ID}`로 조회 가능

## 작업 원칙

- 모든 작업은 YouTrack 티켓에서 시작한다
- 티켓은 5W1H 형식으로 작성한다 (What, Why, Who, Where, When, How)
- 예측 소요시간이 2일을 초과하면 자식 이슈로 분할한다 (목표: 1일 이내 완료 단위)
- In Progress 상태에서 매일 퇴근 전 소요시간을 기록한다

## 코드 변경 규칙

- master 직접 푸시 금지 — `release/*` 또는 `hotfix/*`만 머지 가능
- 모든 변경은 `feature/{이슈ID}` → `develop` → `release/*` → `master` 순서로 진행
- 브랜치명: `feature/{이슈ID}` (예: `feature/DEV2-1234`) — Feature ID, 없으면 Task ID
- 커밋 메시지: `[{이슈ID}] 작업 내용` (예: `[DEV2-1235] 프로필 조회 API 추가`)
- PR에는 사용자 영향, 롤백 방법 필수 기재
- DB/SP 변경이 포함된 PR은 별도 승인 필수
- 프로덕션 배포는 사람 승인 필수

상세: [branching-strategy.md](./branching-strategy.md)

## DB 마이그레이션 컨벤션

- **max-db-script** 레포의 `databases/{DBName}/_migrations/` 에 작성
- Flyway 네이밍: `V{YYYYMMDD}_{HHmm}__{이슈ID}_{설명}.sql`
  - 예: `V20260401_1430__DEV2-5322_fix_settle_month_pk.sql`
  - `V` 접두사 + 타임스탬프 + 더블 언더스코어(`__`) + 이슈ID + 설명
- 멱등성 보장: `IF EXISTS` / `IF NOT EXISTS` 로 반복 실행 안전하게 작성
- `Tables/*.sql`은 자동 생성 참조용 — 직접 수정 금지, 변경은 반드시 `_migrations/`로
- DB/SP 변경 PR은 별도 승인 + 롤백 스크립트 필수

## 기술 스택 원칙

### 신규 서비스
- 백엔드: Kotlin + Spring Boot 3 + JDK 17+ (원칙)
- 신규 .NET 서비스 생성 금지 (예외는 팀장 승인 필요)
- DB 마이그레이션 방식 표준화
- 공통 에러 응답, 인증 필터, trace/correlation 처리 공통화

### 레거시 서비스
- SP(Stored Procedure)는 레거시 비즈니스 런타임으로 취급
- 신규 코드에서 SP 직접 호출 금지 — 반드시 legacy adapter를 통해 접근
- SP 호출은 legacy adapter repo/service에서만 허용
- 신규 서비스가 레거시 DB를 직접 조회/수정 금지 — adapter/facade 뒤로 숨김

## 서비스 소유권

- 서비스마다 owner / backup owner / 배포 권한 / rollback 권한을 명확히 지정
- 서비스 카탈로그(`catalog/`)에 등록 및 관리
