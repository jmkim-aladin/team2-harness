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
- PR에는 사용자 영향, 롤백 방법 필수 기재 — 리뷰어는 배포 판단을, 장애 시 당직자는 복구를 PR만 보고 해야 한다
- DB/SP 변경이 포함된 PR은 별도 승인 필수 — DB 변경은 코드 롤백으로 되돌아가지 않는다
- 프로덕션 배포·롤백 첨부물: [release-policy.md](./release-policy.md)

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
- 신규 .NET 서비스 생성 금지 (예외는 팀장 승인 필요) — 팀 방향이 기존 .NET 레거시 탈출이라 신규가 늘면 이관 대상만 늘어난다
- DB 마이그레이션 방식 표준화
- 공통 에러 응답, 인증 필터, trace/correlation 처리 공통화
- API·admin·batch가 같은 repository에 있더라도 artifact·config·secret·deploy·rollback은 애플리케이션별로 분리하고, 실제 사용하는 capability·DB만 선택해 조립한다
- Kotlin/Spring 멀티프로젝트의 Clean/Hexagonal 경계, runtime·persistence·migration·security·observability 선택과 검증 기준은 [Kotlin/Spring 멀티프로젝트 애플리케이션 표준](../docs/kotlin-spring-multi-project-application-standard.md)을 따른다
- BC 4계층 Kotlin 백엔드의 모듈·패키지·이름·의존·TX 경계·DB 계층 규칙과 검사 장치는 [Kotlin 백엔드 구조 표준](../docs/kotlin-backend-structure-standard.md)을 따른다. 포트 위치(`domain.port`), 통합 테스트 위치(`src/test` + 태그), usecase 모듈의 Spring 조립 클래스(`*Configuration` 만 Spring 을 쓴다)는 구조 표준이 위 멀티프로젝트 표준보다 우선한다 — 두 문서가 반대로 지시하는 자리를 여기서 정한다 (근거: 2026-11-11 사용자 결정 — 주문 서비스·StoreFront 구조 표준 Q-STD-1~8 채택, 같은 날 교차검증에서 세 번째 충돌을 확인해 더했다)

### 레거시 서비스
- SP(Stored Procedure)는 레거시 비즈니스 런타임으로 취급
- 신규 코드에서 SP 직접 호출 금지 — 반드시 legacy adapter를 통해 접근
- SP 호출은 legacy adapter repo/service에서만 허용
- 신규 서비스가 레거시 DB를 직접 조회/수정 금지 — adapter/facade 뒤로 숨김

## 공통 라이브러리 배포

여러 서비스가 함께 쓰는 코드의 공유 경로를 정한다 — 사용처가 늘수록 버전 추적·충돌 해결 비용이 공유 방식에 따라 갈린다.

- 기본: 두 개 이상 서비스가 쓰는 JVM 라이브러리(Kotlin·Java)는 GitHub Packages(Maven)에 jar로 배포하고 Gradle 좌표(`group:artifact:version`)로 참조한다 — 쓰는 버전이 빌드 파일 diff에 남고, 버전 충돌은 Gradle이 해석한다
- 기본: 빌드 산출물이 없는 자산(UI 컴포넌트 소스, proto·OpenAPI 스펙, SQL 스크립트)과 사용처가 하나뿐인 초기 공동 개발 코드는 git submodule로 공유한다. 사용처가 둘로 늘면 jar 배포로 옮긴다
- 버전은 semver로 매기고, 호환성이 깨지는 변경은 메이저 버전을 올린다 — 소비 서비스가 버전만 보고 업그레이드 영향을 판단한다
- 배포는 태그 push(`v1.4.2`)에 반응하는 GitHub Actions publish workflow로 한다. 기본: 정식 버전만 배포한다 — SNAPSHOT은 같은 버전 이름의 내용이 바뀌어 빌드 재현이 깨진다
- 배포한 버전의 삭제·덮어쓰기 금지 — 수정은 새 버전으로 낸다. 이미 그 버전을 받은 서비스의 빌드를 지킨다
- 기본: 라이브러리와 서비스를 함께 고칠 때는 Gradle composite build(`./gradlew build --include-build ../{lib}`)로 로컬 소스를 붙여 확인한다 — 배포 대기 없이 개발하고, repo에는 배포 좌표만 남긴다
- 인증: 로컬은 `~/.gradle/gradle.properties`의 `gpr.user`·`gpr.key`(PAT `read:packages`, 배포 담당은 `write:packages`), CI는 `GITHUB_TOKEN`과 패키지 설정의 repository 접근 권한을 쓴다. 토큰은 repo에 두지 않는다 — [로컬 자격증명 정책](./local-credentials-policy.md)

근거: 2026-11-17 사용자 결정 — 공통 라이브러리 공유 방식(GitHub Packages jar vs git submodule) 비교 후 JVM 라이브러리는 jar 배포를 기본으로 채택

## PostgreSQL 구현 원칙

- PostgreSQL 사용자 정의 함수와 트리거를 새로 만들거나 도입하지 않는다. 신규 마이그레이션의 `CREATE FUNCTION`, `CREATE OR REPLACE FUNCTION`, `CREATE TRIGGER`, `CREATE CONSTRAINT TRIGGER`, `CREATE EVENT TRIGGER`도 이 규칙을 따른다 — 설정 변경에 숨은 DB 실행 절차가 개입하지 않도록 한다
- 검증·상태 변경·버전 관리·감사 기록은 애플리케이션의 명시적인 SQL과 트랜잭션으로 처리한다. PK·FK·UNIQUE·CHECK 등 표준 제약은 데이터 정합성을 위해 사용한다
- PostgreSQL 내장 함수와 일반 조회·집계 SQL은 사용할 수 있다. 금지 대상은 서비스가 추가하는 사용자 정의 함수와 트리거다
- 기존 함수·트리거를 정리할 때는 의존 로직과 회귀 영향을 확인하고 새 마이그레이션으로 제거한다. 이미 적용된 마이그레이션은 checksum과 이력 보존을 위해 원본을 유지한다

근거: 2026-10-26 사용자 명시 지시 — "앞으로 postgres용 함수는 만들지 말고 트리거도 만들지마 팀하네스에 적용해줘". DEV2-11846에서 모드 직접 수정이 DB 함수·트리거에 막힌 운영 복잡성을 줄이기 위한 팀 규칙

## ADR (아키텍처 결정 기록)

서비스 repo `docs/adr/`에 기록한다. 다음 셋을 **모두** 충족할 때만 작성한다 — 하나라도 빠지면 ADR이 아니다:

1. **되돌리기 어렵다** — 나중에 바꾸는 비용이 유의미
2. **배경 없이는 의아하다** — 미래 독자가 "왜 이렇게 했지?"를 갖게 됨
3. **실제 트레이드오프가 있었다** — 진짜 대안들 중 이유 있는 선택

예: 공유 DB 제거·이벤트 전환, write owner 지정 = ADR / DTO 추가·메서드 리네임·라이브러리 마이너 선택 = ADR 아님.

## 서비스 소유권

- 서비스마다 owner / backup owner / 배포 권한 / rollback 권한을 명확히 지정
- 서비스 카탈로그(`catalog/`)에 등록 및 관리
