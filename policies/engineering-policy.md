# 개발 2팀 엔지니어링 정책

> 전사 클린 아키텍처 가이드: [REF-A-1958](https://aladincommunication.youtrack.cloud/articles/REF-A-1958) (YouTrack KB)
> 전사 Git Flow: [REF-A-625](https://aladincommunication.youtrack.cloud/articles/REF-A-625) (YouTrack KB)
> 필요 시 `/ad:team2-kb-read {문서ID}`로 조회 가능

## 작업 원칙

- 모든 작업은 YouTrack 티켓에서 시작한다
- 티켓은 5W1H 형식으로 작성한다 (What, Why, Who, Where, When, How)
- 작업 단위: Feature ≤ 1주 / Task ≤ 1일 — 초과 시 분할. 상세: [docs/sprint/ticket-guide.md](../docs/sprint/ticket-guide.md)
- Feature 하위 Task는 개발 / 검증 / 배포·운영 반영으로 분리한다 — 해당 여부 판정은 **필수**, 해당하면 별도 Task, 해당 없으면 Feature 본문에 사유를 남긴다
- 단계 판정 대상·검증(테스트/QA) 구분·해당 없음 예시: [ticket-guide.md](../docs/sprint/ticket-guide.md) §2-2
- In Progress 상태에서 매일 퇴근 전 소요시간을 기록한다
- AI 도구(Codex, Claude Code 등)는 YouTrack 티켓/Task 생성, 티켓 상태 변경, 담당자/스프린트/Story points 변경 전에 사용자에게 명시 확인을 받는다

## 코드 변경 규칙

- 브랜치 구조·명명·머지 흐름·커밋 메시지 형식: [branching-strategy.md](./branching-strategy.md)
- 커밋·PR·티켓 본문 품질(AI co-author 푸터 금지 포함): [ai-usage-policy.md](./ai-usage-policy.md) §메시지 작성 품질
- AI 도구는 커밋, 푸시, PR 생성, 머지 전에 사용자에게 명시 확인을 받는다
- PR에는 사용자 영향, 롤백 방법 필수 기재
- DB/SP 변경이 포함된 PR은 별도 승인 필수
- 프로덕션 배포는 사람 승인 필수

## DB 마이그레이션 컨벤션

- **max-db-script** 레포의 `databases/{DBName}/_migrations/` 에 작성
- Flyway 네이밍: `V{YYYYMMDD}_{HHmm}__{이슈ID}_{설명}.sql`
  - 예: `V20260401_1430__DEV2-5322_fix_settle_month_pk.sql`
  - `V` 접두사 + 타임스탬프 + 더블 언더스코어(`__`) + 이슈ID + 설명
- 멱등성 보장: `IF EXISTS` / `IF NOT EXISTS` 로 반복 실행 안전하게 작성
- `Tables/*.sql`은 자동 생성 참조용 — 직접 수정 금지, 변경은 반드시 `_migrations/`로 (근거: 마이그레이션 우선 원칙 — max-db-script CLAUDE.md)
- DB/SP 변경 PR은 별도 승인 필수 — 첨부물 단계 기준: [code-review-policy.md](./code-review-policy.md)(PR)·[release-policy.md](./release-policy.md)(배포)

## 기술 스택 원칙

### 신규 서비스
- 백엔드: Kotlin + Spring Boot 4 + JDK 17+ (원칙)
- 신규 .NET 서비스 생성 금지 (예외는 팀장 승인 필요)
- DB 마이그레이션 방식 표준화
- 공통 에러 응답, 인증 필터, trace/correlation 처리 공통화

### 레거시 서비스
- SP(Stored Procedure)는 레거시 비즈니스 런타임으로 취급
- 신규 코드에서 SP 직접 호출 금지 — 반드시 legacy adapter를 통해 접근
- SP 호출은 legacy adapter repo/service에서만 허용
- 신규 서비스가 레거시 DB를 직접 조회/수정 금지 — adapter/facade 뒤로 숨김

## ADR (아키텍처 결정 기록)

서비스 repo `docs/adr/`에 기록한다. 다음 셋을 **모두** 충족할 때만 작성한다 — 하나라도 빠지면 ADR이 아니다:

1. **되돌리기 어렵다** — 나중에 바꾸는 비용이 유의미
2. **배경 없이는 의아하다** — 미래 독자가 "왜 이렇게 했지?"를 갖게 됨
3. **실제 트레이드오프가 있었다** — 진짜 대안들 중 이유 있는 선택

예: 공유 DB 제거·이벤트 전환, write owner 지정 = ADR / DTO 추가·메서드 리네임·라이브러리 마이너 선택 = ADR 아님.

## 서비스 소유권

- 서비스마다 owner / backup owner / 배포 권한 / rollback 권한을 명확히 지정
- 서비스 카탈로그(`catalog/`)에 등록 및 관리
