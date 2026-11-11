# Kotlin 백엔드 구조 표준

BC 4계층 구조(`contexts/<bc>/{api,domain,usecase,data}`)를 쓰는 개발2팀 Kotlin 백엔드의 모듈·패키지·이름·의존·트랜잭션 경계·DB 계층·크기 규칙과 그 검사 장치다. 주문 서비스(order-platform)와 StoreFront(storefront-server)가 첫 적용 대상이고, 같은 구조로 시작하는 새 서비스는 처음부터 따른다.

[Kotlin/Spring 멀티프로젝트 애플리케이션 표준](./kotlin-spring-multi-project-application-standard.md)(이하 "멀티프로젝트 표준")이 앱별 배포·런타임·보안·관측 기준을 정한다. 이 문서는 그 문서가 예시로 남긴 모듈·패키지·이름을 구체 규칙으로 정한다. 두 문서가 다른 곳은 §2 에 있다.

근거: 2026-11-11 사용자 결정 — 주문 서비스·StoreFront 의 구조 실태 조사(불일치 15개), 표준 초안, 독립 반증 검토를 거쳐 결정 질문 Q-STD-1~8 을 채택했다. 결정 기록(선택지·근거)과 두 저장소의 이행 계획·건수는 Obsidian vault 의 `wiki/projects/order-platform/backend-structure-standard-draft-2026-11-11.md` 에 있다.

## 적용 강도와 규칙 ID

| 표기 | 의미 |
|---|---|
| **필수** | [지시 강도](../policies/instruction-precedence-policy.md)의 policy 등급이다. §11 의 검사로 강제한다. 다르게 하려면 이 문서를 먼저 고친다 |
| **기본** | heuristic 등급이다. 검사가 없다. 더 나은 방법이 있으면 바꾸고 이유를 PR 이나 설계 문서에 남긴다 |

멀티프로젝트 표준의 `MUST` 가 필수에, `SHOULD` 가 기본에 대응한다.

규칙마다 ID 가 있다 — `M`(모듈)·`P`(패키지)·`N`(이름)·`D`(의존)·`T`(트랜잭션 경계)·`DB`(DB 계층)·`S`(크기)·`C`(설정)·`X`(문서). 아키텍처 테스트의 규칙 주석에 같은 ID 를 적어 문서와 검사를 잇는다. 번호는 다시 쓰지 않는다(`M-5` 는 `M-4` 에 합쳐져 비어 있다).

## 1. 원칙

1. **구조로 강제하고 테스트로 감사한다.** 필수 규칙은 §11 에 검사가 있고, 검사를 만들 수 없는 규칙은 기본으로 적는다 — 문장만 있는 규칙은 지켜지지 않는다.
2. **세 축을 겹치지 않게 쓴다.** 경계는 Gradle 모듈(BC × 계층)이, 탐색은 패키지(업무 기능)가, 뜻은 이름(역할 접두·접미)이 맡는다. 모듈이 이미 계층을 나누므로 패키지에서 계층·역할을 다시 나누지 않는다.
3. **이름 하나에 뜻 하나.** 접두·접미는 닫힌 목록에서 고르고, 접미의 뜻은 기계가 판정할 수 있는 효과(읽기만 하는가, 멱등 기록을 남기는가)로 정한다.
4. **저장소의 기존 원칙은 전제다.** BC 4계층, 다른 BC 는 `:api` 만, TX 는 usecase 에서 TX 포트로만, 스코프 격리, 이벤트 봉투·아웃박스, 다중 루트 등록부는 이 표준이 바꾸지 않는다. 금융 잠금은 "한 TX 가 영향 주문 전체를 첫 금융 쓰기 전에 한 번, 정해진 순서로 잠근다"는 규약이 전제이고, 그 규약을 무엇으로 구현하는가는 원칙 6 을 따른다.
5. **표준은 공통 뼈대만 정한다.** §3 의 기준에 드는 차이는 저장소 문서에 "표준과 다른 점"으로 남긴다.
6. **DB 에는 선언만 둔다.** DB 에는 표준 선언적 제약(PK·FK·UNIQUE·NOT NULL·CHECK)과 권한만 두고, 함수·트리거 같은 절차 로직은 두지 않는다. 검증·상태 변경·잠금·번호 발급·운영 명령·원장 점검은 앱이 맡는다(§7.3). [engineering-policy.md](../policies/engineering-policy.md) §PostgreSQL 구현 원칙과 같은 방향이라 예외 조항을 두지 않는다.

## 2. 멀티프로젝트 표준과의 관계

| 헥사고날 용어 | 이 표준의 자리 | 멀티프로젝트 표준의 자리 |
|---|---|---|
| 업무 능력 | BC = `contexts/<bc>` | `capabilities/<capability>` |
| 들어오는 포트 | `api` 모듈 인터페이스 | `application` |
| 모델·규칙 | `domain` 모듈 | `domain` |
| 나가는 포트 | `domain.port` 패키지 | `application` |
| 유스케이스·TX 경계 | `usecase` 모듈 | `application` |
| 나가는 어댑터 | `data`(자기 DB), `integrations/<system>`(외부) | `adapters/outbound-<technology>` |
| 들어오는 어댑터·조립 | `apps/<app>` | `adapters/inbound-<runtime>` + `apps/` |

의존 방향은 같다: 앱 조립 → 어댑터 → 유스케이스 → 도메인.

**이 문서가 우선하는 항목은 둘이다.**

| 항목 | 멀티프로젝트 표준 | 이 표준 | 이유 |
|---|---|---|---|
| 나가는 포트의 자리 | 예시 트리에서 `application` | `domain.port` 패키지 | 두 적용 저장소의 아키텍처 테스트(TX 안 외부 연동 금지, 어댑터의 domain 의존 허용 목록)가 이 패키지를 기준으로 삼는다. 멀티프로젝트 표준도 "트리는 예시이고 고정하는 것은 의존 방향"이라고 적는다 |
| 통합 테스트의 자리 | `src/integrationTest` JVM Test Suite | `src/test` + `@IntegrationTest` 태그(`-PskipIntegration` 으로 태그째 뺀다) | 두 적용 저장소의 빌드 규약과 픽스처가 태그 방식이다. 옮겨서 얻는 것이 없다 |

그 밖은 멀티프로젝트 표준을 그대로 따른다 — 앱별 artifact·config·secret 분리, 런타임 선택, config·secret·health, 마이그레이션 실행 주체, 인증·인가, 관측성, 배포 책임 계약.

영속 기술과 런타임은 멀티프로젝트 표준의 "애플리케이션별 선택 항목"이다. 이 문서의 `Exposed*`·`ScopedTable` 같은 이름은 첫 적용 저장소의 선택(Exposed R2DBC, WebFlux)을 예로 든 것이다. 다른 영속 기술을 고른 저장소는 구현 접두만 그 기술 이름으로 바꾼다.

## 3. 공통과 저장소별 차이

배포·데이터 구성에서 오는 차이, 도메인 어휘, 이미 저장소 밖으로 나간 계약은 저장소별로 남긴다. 그 밖은 공통이다.

- 저장소별로 남기는 것: 배포 단위 수와 TX 단계, 스코프 모델, 앱 수, 선택 모듈(`processes`·`query`), 마이그레이션 디렉터리 배치, 설정 키·환경변수 접두, 이벤트 type 접두·확장 속성, 업무 명사.
- 공통으로 정하는 것: 모듈 종류와 의존 방향, 패키지 축, 이름 문법, TX 경계 표기, DB 에 두는 것, 크기 한계, 설정 바인딩 방식, 테스트 배치, 문서 관례, 검사 장치.
- 계약의 이름은 이 표준 밖이다. TypeSpec·OpenAPI 의 interface·operation 이름은 Kotlin 포트를 개명해도 그대로 둔다 — operationId 가 바뀌면 호출자가 깨진다. 대응은 포트 KDoc 에 계약 이름을 적어 잇는다.

지금 적용 중인 두 저장소의 차이는 §13 에 있다.

## 4. 모듈 구성

| 모듈 | 경로 | 규약 플러그인 | 책임 | 의존해도 되는 것 |
|---|---|---|---|---|
| 공용 언어 | `shared/kernel` | `domain` | 2개 이상 BC 가 쓰는 식별자·금액·오류 분류 | 없음 |
| 기술 포트 | `shared/common` | `domain` | 스코프·TX·시각·이벤트 포트 | kernel |
| 저장 기반 | `shared/persistence-<기술>` | `spring-library` | TX 구현·스코프 테이블·예외 번역·시각 변환 | common |
| 메시징 기반 | `shared/messaging` | `spring-library` | 아웃박스·봉투·릴레이·멱등 소비 | common, persistence |
| BC 얼굴 | `contexts/<bc>/api` | `domain` | 들어오는 포트, 계약 타입, 필요 포트(`api.spi`) | common |
| BC 모델 | `contexts/<bc>/domain` | `domain` | 애그리거트·불변식·나가는 포트 | kernel |
| BC 유스케이스 | `contexts/<bc>/usecase` | `spring-library` | 포트 구현·TX 경계·이벤트 소비 | 자기 domain·api, 다른 BC `:api`, common |
| BC 저장 | `contexts/<bc>/data` | `data` | 저장 포트 구현 | 자기 domain, persistence, common |
| 프로세스(선택) | `processes/<p>/{api,usecase}` | `domain`·`spring-library` | 여러 BC 를 순서대로 부른다. TX 를 열지 않는다 | 참여 BC `:api` |
| 조회(선택) | `query/<surface>` | `query` | 조회 전용 읽기 모델 | kernel |
| 외부 어댑터 | `integrations/<system>/<capability>`(+ `core`) | `kotlin-library` 또는 `spring-library` | 외부 포트 구현, `core` 는 공용 클라이언트 | 대상 BC domain(허용 목록, D-4), common |
| 앱 | `apps/<app>` | `spring-boot-app` | 들어오는 어댑터(HTTP·워커)와 조립 | 각 모듈 `*Configuration`, BC `:api` |
| 구조 검사 | `architecture-test` | — | Konsist·ArchUnit 규칙과 위반 fixture | 전 모듈(테스트) |

- **M-1 (필수)** 모듈 종류는 위 표가 전부다. 새 종류는 이 문서를 먼저 고친다 — 종류가 늘면 의존 규칙과 검사가 따라가지 못한다.
- **M-2 (필수)** BC 목록은 `gradle/contexts.txt` 하나가 정한다. BC 이름은 소문자 영문 한 단어(`[a-z]+`)이고 `contexts/` 디렉터리와 같다.
- **M-3 (필수)** 모듈 이름은 소문자 영문·하이픈이다. `integrations` 는 `<system>/<capability>` 두 단계이고, 능력이 둘 이상 같은 클라이언트를 쓸 때만 `core` 를 둔다.
- **M-4 (필수)** 규약 플러그인은 `<service>.{kotlin-library, domain, spring-library, data, spring-boot-app, runtime-boundary, migrations}` 일곱이 공통이고 `query` 는 선택이다. 모듈은 위 표의 플러그인만 쓴다. `runtime-boundary` 는 다른 서비스의 아티팩트·소스 빌드를 거절하고, `migrations` 는 마이그레이션 파일을 검사한다(DB-1).
- **M-6 (필수)** 모든 의존은 `implementation()` 이다. `api()` 는 kernel·common 재노출에만 쓴다 — 전이 노출이 늘면 BC 의 얼굴(`:api`) 밖 타입이 새어 나간다.

## 5. 패키지 배치

루트 패키지는 `kr.co.aladin.<service>` 아래에 모듈 종류별로 둔다: BC 계층 `<bc>.<layer>`, shared `shared.<module>`, integrations `integration.<system>.<capability>`, processes `process.<p>.<layer>`, apps `app.<app>`.

- **P-1 (필수)** 계층 모듈은 단일 패키지로 시작한다. 한 패키지의 main 파일이 15개를 넘으면 **업무 기능** 하위 패키지로 나눈다. api 모듈도 같고, api 의 기능 패키지 이름은 그 BC usecase 의 기능 패키지와 같게 짓는다.
- **P-2 (필수)** 기능 패키지 이름은 소문자 한 단어 업무 명사다. 다른 BC 이름을 단독으로 쓰지 않는다 — BC 와 그 BC 를 다루는 기능이 이름으로 구분되지 않는다. 다른 BC 와 맞닿은 기능은 `{상대 BC}{행위}` 한 단어로 짓는다(`paymentrequest`·`fulfillmentrelease`). **기본:** 이름을 그 저장소 설계 문서의 책임 이름과 맞춘다.
- **P-3 (필수)** 역할 패키지를 만들지 않는다 — `command`·`handler`·`assembler`·`codec`·`policy`·`model`·`service`·`error`·`repository`·`table`·`configuration`. 역할은 모듈과 이름 접미가 이미 말한다. 파일이 하나뿐인 패키지도 만들지 않는다(P-4 의 고정 패키지는 예외). `query` 는 예외로 허용한다 — `*Query` 포트 구현만 담는 패키지 하나. 조회는 여러 기능의 사실을 한 읽기 모델로 합쳐서 기능 하나에 속하지 않는다.
- **P-4 (필수)** 고정 패키지는 둘이다. `domain.port` 에는 그 BC 의 나가는 포트 인터페이스(저장 포트·외부 포트)를 전부 둔다. `api.spi` 에는 다른 BC 가 구현하는 필요 포트를 둔다(D-3). 이 둘은 기능이 아니라 모듈의 경계라서 검사가 패키지를 기준으로 삼는다.
- **P-5 (필수)** 조립 클래스(`*UseCaseConfiguration`·`*DataConfiguration`)는 계층 루트 패키지에 둔다.
- **P-6 (필수)** apps 는 들어오는 어댑터의 종류로 나눈다: `http`(핸들러·라우트·오류 응답), `worker`(주기 실행 진입점과 그 조립), `access`(인증·호출자·스코프 결정), 루트(Application·health·공통 조립). apps 는 인바운드 어댑터 모음이라 어댑터 종류가 곧 변경 이유다. 파일이 15개 이하인 앱은 평면으로 둔다.
- **P-7 (기본)** integrations 는 `integration.<system>.<capability>` 평면, shared 는 `shared.<module>.<기술 주제>` 로 둔다. 15개를 넘으면 P-1 을 따른다.
- **P-8 (필수)** 테스트 클래스의 패키지는 대상 클래스의 패키지와 같다.
- **P-9 (필수)** `testFixtures` 의 패키지는 모듈 루트 패키지 + `.test` 다.

## 6. 이름 규칙

### 6.1 포트와 구현

| 대상 | 규칙 | 예 | 쓰지 않는 것 |
|---|---|---|---|
| 들어오는 포트 | `{업무 명사}` + 접미 넷 중 하나(아래 표) | `OrderCancellationIntake`, `OrderQuery` | 행위자 명사(`OrderPlacer`), 접미 없는 복수 명사, `*Monitor`·`*Finder`·`*Reader`·`*Directory` |
| 저장 포트 | 애그리거트 루트는 `{Root}Repository`. 루트가 아닌 읽기·기록은 `*Directory`(등록부 조회)·`*Catalog`(기준 정보)·`*Log`(추가 전용 기록) | `OrderRepository`, `TenantDirectory` | `*Service`, 접미 없는 복수 명사 |
| 외부 포트 | `{대상}Port`, `domain.port` 에 둔다. 구현이 여럿이면 `supports(code)` | `PaymentGatewayPort` | |
| 구현 선택기 | `{포트에서 Port 를 뺀 이름}Registry`, usecase 에 둔다 | `PaymentGatewayRegistry` | 테이블 객체에 `*Registry` |
| usecase 구현 | `Default{포트 이름}`, 포트 하나에 구현 하나 | `DefaultOrderIntake` | 다른 접두, 포트 이름과 다른 `Default*` |
| data 구현 | `internal class Exposed{포트 이름}` | `ExposedOrderRepository` | |
| shared·integrations 구현 | `{기술·시스템}{포트에서 Port 를 뺀 이름}` | `SqsEventPublisher` | `*Adapter`, `*Impl` |
| main 의 대역 구현 | `Simulated{…}` | `SimulatedPaymentGateway` | `Stub*`·`Mock*` |
| 외부 API 호출 클래스 | `{System}{대상}Client` | `OrderPlatformClient` | |
| 한 포트의 구현이 여럿 | `{변형}{포트 이름}` | `{사건}EventHandler` | |

접미의 뜻은 호출자가 아니라 **효과**로 정한다 — 호출자 기준은 같은 포트가 두 접미에 걸치고, 효과는 검사할 수 있다.

| 접미 | 뜻 | 검사 |
|---|---|---|
| `*Query` | 읽기 TX 만 연다 | 구현이 읽기 전용 TX 만 쓴다 |
| `*Intake` | 요청 멱등 키를 받아 멱등 기록에 결과를 남기는 쓰기. 호출자가 밖인지 안인지는 따지지 않는다 | 구현이 그 저장소의 멱등 기록 포트에 의존한다 |
| `*Commands` | 그 밖의 쓰기 | — |
| `*Listener` | 반환값이 없는 통지 | 모든 메서드가 `Unit` 을 돌려준다. 결과를 돌려주면 `*Commands` 다 |

- **N-1 (필수)** 위 두 표. 읽기와 쓰기가 한 인터페이스에 섞인 포트는 쪼갠다. `Default` 는 usecase 의 포트 구현에만 쓴다.
- **N-2 (필수)** domain 안에는 `Default*` 구현을 두지 않는다. 도메인 서비스는 구체 클래스나 `object` 다.
- **N-3 (기본)** 저장 포트의 읽기 메서드 접두는 `get`(없으면 예외)·`find`(null)·`list`·`count`·`is` 로 닫는다. 쓰기 메서드는 상태 전이를 드러내는 동사(`open`·`mark`·`record`·`create`)를 쓴다 — `save` 하나로 모으면 어떤 전이인지 이름에서 사라진다.

### 6.2 조립·설정·진입점

| 접미 | 뜻 | 위치 |
|---|---|---|
| `*Configuration` | `@Configuration` 조립. 계층 모듈은 `{Bc}{Layer}Configuration` | 모듈마다, 앱이 `@Import` |
| `*Properties` | `@ConfigurationProperties` 로 묶는 클래스와 그 중첩 값 | apps, 자기 설정을 가진 shared 기술 모듈 |
| `*Settings` | 설정 어노테이션이 없는 순수 값. usecase·domain 이 생성자로 받는다 | usecase·shared |
| `*Handler` | HTTP 요청 하나를 처리한다. `{동사}{대상}Handler` | apps `http` |
| `*RouterConfiguration` | 라우터 빈만 둔다. 경로 → 핸들러 메서드, 로직 없음 | apps `http` |
| `*Worker` | 주기 실행 진입점(`SmartLifecycle`). 로직은 usecase·shared 의 접미 없는 업무 명사가 갖는다 | apps `worker` |
| `*EventHandler` | 사건 소비자 | usecase |

- **N-4 (필수)** 위 표. `*Scheduler` 와 shared 의 `*Worker` 는 쓰지 않는다. `*Handler` 는 HTTP 전용이고 사건 소비는 `*EventHandler` 다 — 같은 접미가 두 뜻이면 이름으로 역할을 찾을 수 없다.

### 6.3 이벤트·오류·타입

- **N-5 (필수)** CloudEvents type 은 `kr.aladin.<service>.<producer_bc>.<event-type>.v<n>` 이고 `<event-type>` 은 kebab-case 과거형 사실이다(`payment-failed`). 이미 등록된 타입은 계약이라 그대로 두고 판을 올릴 때 바꾼다.
- **N-6 (기본)** 발행 사건을 만드는 타입은 `{과거형 사실}Event`, 묶음은 `{주제}Events`, 소비 쪽 type 상수는 `{Producer}EventTypes` 로 짓는다.
- **N-7 (필수)** 오류 코드는 `enum class {주제}ErrorCode`, 상수는 `UPPER_SNAKE`, 파일은 `{주제}ErrorCode.kt` 단독이다. 접미 `*ConflictCode` 는 저장 시점의 유일성 충돌 전용이다 — data 가 유일 제약 위반을 바꿔 던지고 usecase 가 잡아 거래 거절로 옮기는 코드다.
- **N-8 (필수)** 오류 코드의 위치는 던지는 쪽과 잡는 쪽이 모두 볼 수 있는 가장 낮은 계층이다. 도메인이나 data 가 던지면 `domain`(usecase 는 data 를 볼 수 없다), 유스케이스가 던져 다른 BC·앱이 계약으로 보면 `api`, apps·integrations·shared 자신의 오류는 자기 모듈. usecase 모듈에는 오류 코드를 두지 않는다.
- **N-9 (기본)** 예외 클래스는 계층별 셋(`DomainException`·`UseCaseException`·`DataException`)과 오류 코드로 구분한다. HTTP 상태는 apps 한 곳에서 오류 분류로 정한다.

| 접미 | 뜻 |
|---|---|
| `*Request` / `*Input` | 들어오는 포트의 최상위 입력 / 그 안의 중첩 입력 값 |
| `*View` | 조회 결과(읽기 모델) |
| `*Outcome` / `*Result` | 포트 반환의 분기(sealed) / 한 분기 안의 결과 값(data class, 저장·재생 대상) |
| `*Command` | 나가는 외부 포트에 넘기는 실행 명령 |
| `*Dto` | 외부 시스템의 요청·응답 모양 |
| `*Id` | value class 식별자 |
| `*Status` / `*Kind` | 저장되는 수명 주기 상태 / 바뀌지 않는 분류 |

- **N-10 (필수)** `*Dto` 는 integrations 안에서만 쓴다 — 외부 모양이 BC 안으로 번지지 않게 한다. **기본:** 나머지 접미는 위 뜻으로만 쓴다.
- **N-11 (필수)** 테이블 객체는 `internal object {복수 명사}` 다. `Table` 접미는 기반 클래스만 쓴다.

### 6.4 파일·테스트·중복

- **N-12 (필수)** 파일 이름은 그 파일의 주 선언(포트 인터페이스·애그리거트·구현 클래스) 이름이다. 그 포트만 쓰는 요청·결과 타입은 같은 파일에 둘 수 있다(§8 한계 안). 둘 이상의 포트가 쓰는 타입은 자기 파일을 갖는다.
- **N-13 (필수)** 묶음 파일 접미는 셋뿐이다: `*Tables.kt`(테이블 객체), `*Vocabulary.kt`(작은 enum·value class), `*Fakes.kt`(테스트 대역). `*Api.kt`·`*Ports.kt`·`*Enums.kt`·`*Values.kt` 는 쓰지 않는다 — 파일 이름으로 선언을 찾을 수 없다.
- **N-14 (필수)** 테스트 클래스는 `{대상}Test`, apps 의 HTTP 통합 테스트는 `{기능}HttpTest`, 메서드는 백틱 한국어 문장이다. 통합 표식은 픽스처 어노테이션 `@IntegrationTest` 만 쓴다. 대역 접두는 `Fake*`(동작하는 인메모리 구현)·`Recording*`(호출 기록)·`Fixed*`(고정 값), 환경 픽스처는 `*Fixture`, 표본 데이터는 `*Samples` 다.
- **N-15 (필수)** 같은 BC 안(api·domain·usecase·data)에서 최상위 선언의 단순 이름은 겹치지 않는다. api 타입은 접미를 갖고 domain 은 접미 없는 명사를 쓰므로 겹칠 이유가 없다.
- **N-16 (기본)** BC 가 다르면 같은 이름을 각자 가질 수 있다. 뜻과 값이 같고 둘 이상의 BC 가 쓰면 kernel 승격을 검토한다.
- **N-17 (기본)** 업무 명사는 그 저장소 도메인 모델 문서의 용어(`name`·`aliases`)에서 가져온다. 새 명사는 용어에 먼저 올린다.

## 7. 의존·경계 규칙

### 7.1 모듈 의존

- **D-1 (필수)** 계층 의존은 §4 표의 "의존해도 되는 것" 열이 전부다. domain·api·kernel·common 은 Spring·영속 프레임워크·Reactor 를 모른다.
- **D-2 (필수)** 다른 BC 는 `:api` 만 본다. domain·api 모듈은 다른 컨텍스트 모듈에 의존하지 않는다.
- **D-3 (필수)** BC 의존 그래프(usecase → 다른 BC api)에는 순환이 없다. 역방향으로 알리거나 물어야 하면, 부르는 쪽 BC 가 자기 `api.spi` 에 필요 포트를 선언하고 상대 BC 의 usecase 가 구현한다. 필요 포트의 접미도 §6.1 의 넷이다. 호출은 같은 프로세스 안의 동기 호출이라 한 TX 합류와 잠금 순서는 달라지지 않는다. 구현하는 BC 는 `api.spi` 의 타입을 자기 사건의 payload 로 그대로 쓰지 않고 자기 payload 타입에 옮겨 담는다 — 남의 계약 타입이 자기 사건 계약이 되면 소유가 뒤섞인다.
- **D-4 (필수)** contexts 밖 모듈(apps·integrations·shared·processes·query)의 컨텍스트 domain 의존은 허용 목록에 이유와 함께 있는 것만 된다. 이유는 둘뿐이다 — 어댑터가 그 BC 의 domain 포트를 구현한다, 앱이 그 포트 타입을 빈으로 등록한다. 쓰지 않는 허용 항목도 실패한다. 앱이 응답·화면에 쓰는 값은 api 타입으로 받는다.
- **D-5 (필수)** usecase 는 integrations 패키지를 모른다. 외부 호출은 `domain.port` 의 `*Port` 로만 하고 TX 람다 밖에서 부른다. 검사가 외부 연동으로 보는 대상은 integration 패키지, `domain.port` 의 `*Port` 전부, `*Registry`·`*Client` 다.
- **D-6 (필수)** shared 는 contexts 를 모른다. kernel 은 의존이 없고 common 은 kernel 만 본다.
- **D-7 (필수)** 테스트 의존도 §4 표와 D-2 를 따른다. 다른 BC 의 usecase·data 를 `testImplementation` 으로 무는 것은 조립을 검사하는 apps 테스트만 된다. data 테스트는 자기 BC 의 usecase 도 물지 않는다. 공용 대역·픽스처는 `testFixtures` 로 나눈다.
- **D-8 (필수)** 다른 서비스의 아티팩트·소스 빌드에 의존하지 않는다(`runtime-boundary`).

### 7.2 트랜잭션 경계

포트와 구현을 나누는 일은 "TX 를 열기 전에 판정하고, 첫 문장에서 영향 주문 전체를 잠근다"는 전제를 깨기 쉽다. 바깥 TX 가 주문 하나만 잠근 채 더 큰 집합을 잠그는 경로를 부르면 안쪽 잠금이 거절되고, 이 실패는 그 경로에서만, 실행 중에만 드러난다.

- **T-1 (필수)** TX 를 여는 호출과 금융 잠금 호출은 포트 구현 클래스(`Default*`)와 사건 소비자(`*EventHandler`)의 메서드에만 둔다. 같은 패키지의 `internal` 협력 클래스는 TX 를 열지 않고 잠금을 잡지 않는다 — 잠금이 이미 걸렸다고 보는 본문만 갖고, 그런 메서드 이름은 `*Locked` 로 끝낸다.
- **T-2 (필수)** TX 밖에서만 불러야 하는 포트 메서드(스스로 TX 를 열기 전에 잠금 집합을 정하는 메서드, 외부 호출을 낀 처리기)에는 마커 어노테이션 `@OutsideTransaction`(`shared:common`)을 붙인다. 검사는 "TX 람다 안에서 마커 메서드를 부르지 않는다"다.
- **T-3 (필수)** 한 TX 의 금융 잠금 집합은 첫 금융 쓰기 전에 한 번에 전부 선언한다. 포트가 다른 포트를 부르는 중첩에서는 바깥 TX 가 안쪽이 잠글 주문까지 먼저 잠근다.
- **T-4 (필수)** 다중 루트 등록부의 호출 지점은 `Class.method` 까지 적고, 등록부 테스트가 메서드가 있는지 확인한다. 등록부에 오르는 것은 TX 를 여는 `Default*` 메서드다 — 클래스 이름만 보면 분할 뒤에도 통과하면서 낡는다.
- **T-5 (필수)** 등록부 항목마다 그 경로의 TX·잠금 실행 기록 고정 테스트를 `pinned_by` 로 적는다. 고정 테스트는 TX 를 연 횟수와 순서, TX 마다 선언한 잠금 집합, TX 밖 외부 호출의 위치, 아웃박스 적재를 기록해 기대값과 비교한다. 포트·구현을 나누는 변경은 이 테스트를 고치지 않고 통과해야 한다.

근거: 2026-11-11 독립 반증 검토 — 반품 정산 경로가 TX 밖에서 판정한 뒤 두 주문을 함께 잠그는데, 기존 등록부 테스트는 클래스 파일이 있는지만 봐서 포트 분할이 이 전제를 깨도 잡지 못했다.

### 7.3 DB 계층

- **DB-1 (필수)** 마이그레이션 파일에는 사용자 정의 함수·프로시저·트리거를 만들거나 고치는 문장을 쓰지 않는다 — `CREATE [OR REPLACE] FUNCTION`·`CREATE [OR REPLACE] PROCEDURE`·`CREATE [CONSTRAINT|EVENT] TRIGGER`. 지우는 문장(`DROP FUNCTION`·`DROP TRIGGER`)은 쓸 수 있다. DB 에 두는 것은 PK·FK·UNIQUE·NOT NULL·CHECK 제약과 권한(`GRANT`·`REVOKE`·열 권한)이다. PostgreSQL 내장 함수, 기본값, identity, DOMAIN 의 CHECK, 뷰는 절차 로직이 아니라 쓸 수 있다. 이미 함수·트리거가 있는 저장소는 표준을 채택한 시점의 마이그레이션 파일을 기준선으로 하고, 그 뒤의 파일은 기존 함수의 본문 수정도 쓰지 못한다 — 기능 변경이 그 로직의 수정을 요구하면 그 검사를 앱으로 옮기는 일을 그 변경과 함께 한다.
- **DB-2 (기본)** 절차 로직이 하던 일은 앱의 이 자리로 간다.

  | DB 가 하던 일 | 앱의 자리 |
  |---|---|
  | 돈·수량 불변식(합계 일치, 초과 환불 금지) | 도메인이 금융 잠금 아래에서 쓰기 전에 검사한다 |
  | 수정·삭제 금지(불변 행·불변 열) | 권한 회수 — 앱 계정에 `UPDATE`·`DELETE`·해당 열 권한을 주지 않는다 |
  | 한 행 안의 값 검사 | `CHECK` 제약, 또는 도메인 생성·행위 메서드 |
  | 상태 전이 가드 | 애그리거트 행위 메서드가 검사하고, data 는 기대 상태를 조건으로 건 UPDATE 로 쓴다 |
  | 금융 잠금 | 앱이 정해진 순서로 정렬한 `SELECT … FOR UPDATE` |
  | 고객 노출 번호 발급 | 앱이 번호 범위 행을 잠그고 발급한다 |
  | 운영 명령(재전송·건너뛰기·보류 해제) | 앱의 운영 포트 |
  | 원장 점검 | 앱 쿼리(persistence 의 읽기 전용 경로 하나) |

- **DB-3 (필수)** 업무 표에 쓰는 DB 계정은 앱 계정 하나다. 마이그레이션 소유자 계정은 DDL 만 하고, 운영자는 DB 에 직접 쓰지 않고 앱의 운영 포트로 명령한다 — 쓰는 길이 하나여야 앱의 검사가 전부를 덮는다.
- **DB-4 (필수)** 앱의 원장 점검 쿼리를 매일 돌려 불변식 위반을 찾고 경보한다. 앱 검사가 놓친 것을 하루 안에 찾는 보강이다.
- **DB-5 (필수)** DB 예외 번역은 한 곳이다. 번역 대상은 표준 제약 위반(유일·FK·CHECK)과 권한 거부다.

RLS 정책은 권한 선언이라 이 규칙이 막지 않는다(켤지는 저장소별 결정이다).

근거: 2026-11-11 사용자 결정 — 함수·트리거 충돌은 정책 예외가 아니라 원칙으로 푼다. [engineering-policy.md](../policies/engineering-policy.md)의 금지(2026-10-26) 뒤에도 두 저장소의 마이그레이션이 함수·트리거를 계속 만들었고, 금지를 문장이 아니라 마이그레이션 검사로 지키기로 했다.

## 8. 파일·코드 크기

- **S-1 (필수)** main 파일은 800줄을 넘지 않는다. 목표는 400줄이다.
- **S-2 (필수)** 테스트 파일은 1,500줄을 넘지 않는다.
- **S-3 (필수)** 파일 하나의 최상위 선언은 10개 이하다. `*Tables.kt`·`*Vocabulary.kt` 는 예외다(줄 수 한계는 적용). 선언을 sealed 부모 안에 넣어 수를 줄이는 우회를 막으려고 중첩 타입 선언도 센다.
- **S-4 (필수)** 한계를 넘는 기존 파일은 기준선으로 관리한다(§11).
- **S-5 (기본)** 나누는 순서: ① 포트별로 구현 클래스를 나눈다 ② 단계별(수락 TX·TX 밖 호출·결과 TX)이나 읽기·쓰기별로 같은 패키지의 `internal` 협력 클래스를 뺀다(T-1 을 지킨다) ③ 계산·조립은 domain 으로 내린다. 파일을 나눌 때 파일 단위 `private` 최상위 선언은 `internal` 로 올린다 — 그대로 두면 컴파일이 깨진다.

## 9. 설정·환경변수

- **C-1 (필수)** 설정 키 접두는 서비스 kebab 이름 하나다. 그 아래는 주제로 나눈다.
- **C-2 (필수)** 설정은 `@ConfigurationProperties` + `*Properties` 로만 읽는다. `Environment.getProperty` 와 `@Value` 는 쓰지 않는다 — 타입·필수 검사가 빠진다. contexts 의 모듈은 Spring 설정 API 를 읽지 않고 앱이 만든 `*Settings` 를 받는다.
- **C-3 (기본)** 필수 설정이 없으면 기동을 거절하고, 기본 DB·계정·비밀을 소스에 두지 않는다. 멀티프로젝트 표준의 `MUST` 이고 검사는 저장소의 기동 테스트가 맡는다.
- **C-4 (필수)** 환경변수는 `application.yml` 에 `${이름}` 으로 명시하고, 설정 키 표를 저장소 한 곳에 두어 테스트가 `application.yml` 과 대조한다.
- **C-5 (기본)** 환경변수 접두는 서비스마다 하나(`<SERVICE>_`)로 둔다. 이미 배포 계약이 된 접두는 바꾸지 않고 저장소 차이로 남긴다.

## 10. 문서 관례

- **X-1** 이 문서가 표준의 원본이다. 저장소 문서는 이 문서를 가리키고 "표준과 다른 점"만 적는다 — 같은 규칙이 두 곳에 있으면 한쪽이 낡는다([claude-md-policy.md](../policies/claude-md-policy.md)).
- **X-2 (필수)** 근접 `CLAUDE.md` 는 Gradle 모듈 디렉터리마다 하나다. 단 BC 는 계층마다 두지 않고 `contexts/<bc>/CLAUDE.md` 하나다. 내용은 규칙·경계·진입점만 둔다.
- **X-3** 저장소 스킬 이름은 `architecture-guide`·`add-context`·`add-integration-adapter`·`shared-kernel` 넷으로 같다. `architecture-guide` 의 공통 부분은 이 문서를 가리키고 저장소 차이만 남긴다.
- **X-4** 표준 규칙과 다른 선택을 하면 그 저장소 설계 문서의 결정에 규칙 ID 를 적는다. 설계 문서 본문에는 클래스·포트·패키지 이름을 쓰지 않고 책임 이름으로 쓴다 — 본문이 채택 근거에 들어가는 문서 체계에서는 개명 하나가 채택 재검토를 부른다.
- **X-6 (기본)** 경보는 kebab-case 메시지 키에 건다 — 로거 이름(클래스 FQCN)은 개명·이동하면 바뀐다.

## 11. 강제 장치

규칙은 각 저장소의 `architecture-test`(Konsist·ArchUnit·텍스트 검사)와 `build-logic`(Gradle 플러그인)에 넣는다. 저장소끼리는 아티팩트·소스에 의존하지 않으므로 규칙 코드는 복사하고, 규칙 ID 를 주석에 적어 이 문서와 대조한다.

### 11.1 기준선

기존 저장소에 새 규칙을 넣을 때 위반이 10건 안쪽이고 파일을 옮기지 않아도 되면 바로 고친다. 위반이 많은 규칙(이름·패키지·크기)은 기준선으로 넣는다 — 지금 위반을 목록으로 등록하고, 늘면 실패하고, 줄면 목록에서 지워야 통과한다.

- 규칙마다 기준선 파일을 따로 둔다 — 한 파일에 몰리면 병렬 브랜치가 늘 충돌한다.
- 기준선 파일마다 항목 수 상한을 처음 값으로 고정한다. 상한을 넘으면 실패한다 — 새 위반을 기준선에 넣는 길을 막는다.
- 항목에 `owner`·`ticket` 을 적는다 — 없으면 영구히 남는다.
- 개명·이동 커밋은 같은 커밋에서 기준선의 키만 바꾸고 항목 수는 늘리지 않는다.
- 새 규칙은 기존 위반 fixture 패키지를 대상에서 빼고, 규칙마다 위반 fixture 를 따로 둔다 — fixture 로 규칙이 실제로 잡는지 증명한다.

### 11.2 검사 목록

| 규칙 ID | 검사 내용 | 도구 |
|---|---|---|
| M-1·M-3·M-4·M-6 | 모듈 경로 종류와 규약 플러그인의 대응, 모듈 이름 형식, `api()` 는 kernel·common 에만 | 텍스트(build·settings 파일) |
| M-2 | `contexts.txt` 와 `contexts/` 디렉터리가 같다 | settings·테스트 |
| P-1 | 패키지당 main 파일 15개 이하(api 포함) | Konsist |
| P-2·P-3 | 하위 패키지 이름이 BC 이름 단독·역할 금지어가 아니다, 파일 하나짜리 패키지 없음, `query` 패키지의 클래스는 `*Query` 포트만 구현한다 | Konsist |
| P-4 | data·integrations 가 구현하는 domain 인터페이스는 `domain.port` 에 있다. `api.spi` 인터페이스는 자기 BC usecase 가 구현하지 않는다 | ArchUnit |
| P-5 | `*UseCaseConfiguration`·`*DataConfiguration` 은 계층 루트 패키지에 있다 | Konsist |
| P-6 | 하위 패키지를 둔 앱에서 `SmartLifecycle` 구현은 `..worker..`, `*Handler` 는 `..http..` | ArchUnit |
| P-8·P-9 | 테스트 패키지가 같은 모듈 main 에 있다, testFixtures 패키지는 `.test` | Konsist |
| N-1·N-2 | api 인터페이스 접미가 닫힌 집합이다. `Default{X}` 는 usecase 에만 있고 api 의 `X` 하나만 구현한다. contexts 의 data 구현은 data 에만 있고 `internal` 이다. `*Adapter`·`*Impl` 금지 | Konsist |
| N-1(접미의 뜻) | `*Query` 구현은 쓰기 TX 를 열지 않는다. `*Intake` 구현은 멱등 기록 포트에 의존한다. `*Listener` 의 메서드는 `Unit` 을 돌려준다 | ArchUnit |
| N-4 | `*Worker` 는 apps 의 `SmartLifecycle`, `*Scheduler` 금지, `*Handler` 는 apps, `*Properties` 는 `@ConfigurationProperties` 가 있거나 그 중첩 타입 | Konsist |
| N-5 | 이벤트 타입 등록 파일의 새 타입이 kebab-case 다 | 테스트 |
| N-7·N-8 | 오류 코드 enum 의 이름이 `*ErrorCode` 또는 `*ConflictCode`(domain 에만)이고 usecase 모듈에 없다 | Konsist |
| N-10·N-11 | `*Dto` 는 integration 패키지에만, 테이블 객체 이름에 `Table` 접미 없음 | Konsist |
| N-12·N-13 | 선언이 여럿인 파일은 파일 이름과 같은 선언이 있거나 허용 묶음 접미다 | Konsist + ktlint |
| N-14 | `@Tag("integration")` 직접 사용 금지, 대역 접두 금지어 | Konsist |
| N-15 | 같은 BC 안 최상위 선언 단순 이름 중복 없음 | Konsist |
| D-1 | domain·api·kernel·common 의 프레임워크 의존 없음 | ArchUnit |
| D-2·D-3 | BC 간 `:api` 만, build 파일로 만든 BC 그래프와 컴파일된 클래스 조각에 순환 없음 | 텍스트 + ArchUnit |
| D-4 | contexts 밖의 domain 의존 허용 목록과 낡은 항목 | 텍스트(build 파일) |
| D-5 | TX 람다 안 외부 연동 호출 없음, usecase → integration 의존 없음 | ArchUnit |
| D-6·D-7 | shared 의 build 파일에 `:contexts:` 의존 없음, `test*` 의존에도 §4 표·D-2(apps 제외) | 텍스트 |
| D-8 | 해석된 클래스패스에 다른 서비스 아티팩트·다른 빌드 프로젝트 없음 | Gradle `runtime-boundary` |
| T-1 | usecase 모듈에서 `Default*`·`*EventHandler` 가 아닌 클래스는 TX 를 열지 않고 금융 잠금을 부르지 않는다 | ArchUnit |
| T-2 | TX 람다 안에서 `@OutsideTransaction` 메서드를 부르지 않는다 | ArchUnit |
| T-4·T-5 | 등록부 호출 지점의 `Class.method` 가 있다, 항목마다 `pinned_by` 테스트가 있다 | 등록부 테스트 |
| DB-1 | 기준선 뒤의 마이그레이션 파일에 함수·프로시저·트리거를 만들거나 고치는 문장이 있으면 실패한다(주석·문자열은 뺀다) | Gradle `migrations` |
| DB-1(끝 상태) | 마이그레이션을 다 적용한 DB 의 사용자 함수·트리거 수가 기준선 값을 넘지 않는다 | 통합 테스트 |
| DB-3 | 업무 표에 `INSERT`·`UPDATE`·`DELETE` 권한을 가진 역할이 앱 역할뿐이다 | 통합 테스트 |
| DB-4·DB-5 | 원장 점검이 앱 쿼리로 돈다, 예외 번역이 한 곳이다 | 저장소 테스트·ArchUnit |
| S-1~S-4 | 파일 줄 수·선언 수(중첩 포함)와 기준선, 기준선 항목 수 상한·`owner`·`ticket` | 텍스트 |
| C-1·C-2 | `@ConfigurationProperties` 의 prefix 와 `application.yml` 최상위 키가 서비스 접두다. `Environment.getProperty`·`@Value` 사용 없음, contexts 모듈이 Spring `Environment` 를 모른다 | Konsist·ArchUnit |
| C-4 | 설정 키 표와 `application.yml` 대조 | 저장소 테스트 |
| X-2 | Gradle 모듈 디렉터리(BC 는 `contexts/<bc>`)에 `CLAUDE.md` 가 있고 BC 계층 디렉터리에는 없다 | 텍스트 |
| (테스트) | main 소스가 있는 domain·usecase·data 모듈에 테스트가 하나 이상 있다 | 텍스트 |

검사가 없는 규칙은 N-3·N-6·N-9·N-16·N-17·P-7·S-5·C-3·C-5·DB-2·X-6 이고 모두 기본이다.

## 12. 기존 저장소에 적용하기

구조 이행은 HTTP 계약·DB 스키마·사건 type 문자열·설정 키·환경변수를 바꾸지 않는다. 바뀌는 것은 Kotlin 패키지, 클래스·파일 이름, 모듈 의존, 포트·클래스 분할이다.

**옮기기 규칙**: 파일의 이름·패키지는 지금 그 파일이 있는 모듈의 슬라이스에서 한 번만 바꾼다. 다른 슬라이스는 그 파일의 import·참조만 고친다 — 같은 파일을 여러 번 옮기면 기준선과 문서 근거가 그때마다 낡는다.

| 순서 | 슬라이스 | 하는 일 | 파일 이름·패키지 변경 |
|---|---|---|---|
| R0 | 문서 선행 | 저장소 문서를 이 표준에 맞춘다. 설계 문서 본문의 클래스명을 책임 이름으로 바꾼다(X-4). DB-1 의 기준선을 기록한다 | 없음 |
| R1 | 검사 장치 | 기준선 장치와 §11.2 의 규칙을 넣는다 | 없음 |
| R2 | 안전망 | 금융 경로의 usecase 테스트, TX·잠금 실행 기록 고정 테스트(T-5), 등록부 메서드 검사(T-4), TX 밖 전용 마커(T-2) | 없음 |
| R3 | BC 세로 슬라이스 | BC 하나에서 한 번에: `api.spi` 이동, 포트 개명·분할, 구현 분할, 패키지, 파일·오류·테이블 이름 | 그 BC 의 파일만 |
| R4 | 바깥 모듈 | apps·integrations·shared 의 패키지와 이름, 설정 바인딩 | 그 모듈의 파일만 |
| R5 | 마감 | 기준선에 남은 항목 확인, 스킬·루트 CLAUDE.md 개정 | 없음 |

- 기본: R3 는 의존 그래프의 잎부터 한다. 제공하는 쪽의 포트 이름이 먼저 확정되면 쓰는 쪽 파일은 import 만 고치고 자기 슬라이스에서 한 번 옮긴다. 같은 저장소 안의 R3 는 차례로 한다 — 조립 클래스가 충돌한다.
- 포트·구현을 나누는 R3 는 R2 뒤에 한다. 고정 테스트는 고치지 않고 통과해야 한다(이름 참조만 바뀐다).

**모든 슬라이스의 검증**

1. `./gradlew check`(통합 테스트 포함)와 `:architecture-test:test`. `-PskipIntegration` 실행은 검증으로 치지 않는다 — DB 검증이 빠진다.
2. 설계 문서 검사(SOF 를 쓰는 저장소는 `foundry validate --strict`)와 문서가 가리키는 테스트·소스 경로의 갱신.
3. 다른 서비스와 함께 도는 e2e 가 있으면 그것도 통과시킨다.
4. 근거 경로 갱신: 근접 `CLAUDE.md`, 다중 루트 등록부, 아키텍처 테스트의 규칙 문자열·fixture.
5. 기준선: 항목 수가 늘지 않았다. 줄었으면 목록에서 지웠다.

**DB 절차 로직 이관**은 구조 이행 뒤의 별도 프로젝트다. 새 함수·트리거는 R1 의 DB-1 검사가 그동안에도 막는다. 순서는 위험이 낮은 것부터다.

1. 원장 점검을 앱 쿼리로 옮기고 매일 돌린다(DB-4) — 뒤 단계의 안전망이다.
2. 불변(수정·삭제 금지 가드) → 권한 회수.
3. 행 검사 → `CHECK` 제약 또는 도메인.
4. 잠금 → 앱의 정렬된 `SELECT … FOR UPDATE`.
5. 번호 발급 → 앱.
6. 운영 함수 → 앱의 운영 포트.
7. 상태 전이 가드 → 애그리거트 행위 메서드 + 조건부 UPDATE.
8. 여러 표에 걸친 합계 불변식 → 도메인이 금융 잠금 아래에서 쓰기 전에 검사.

단계마다 그 함수·트리거가 막던 사례를 앱 테스트로 먼저 옮긴다. 옮긴 테스트가 가드가 있는 DB 와 가드를 지운 DB 에서 모두 통과하는 것을 본 뒤에 `DROP` 마이그레이션을 낸다. 이미 적용된 마이그레이션은 고치지 않는다.

## 13. 참조 적용 — 주문 서비스·StoreFront

두 저장소가 이 표준의 첫 적용 대상이다. 아래는 §3 의 기준으로 저장소별로 남기는 차이다.

| 항목 | 주문 서비스 | StoreFront |
|---|---|---|
| 배포 단위·TX 단계 | 단일 단위, 다중 루트 등록제만 | 4단위, 단위 교차 금지 + 등록제 |
| 스코프 모델 | 판매 범위(`ScopedTable`) | 테넌트(`TenantTable`) |
| 앱 | `apps/service` 하나 | `common·web·admin·internal·worker` |
| 선택 모듈 | 없음 | `processes/checkout`, `query/admin` |
| 마이그레이션 배치 | 루트 `db/migration` | `db/<unit>` |
| 설정 키 접두 | `order-platform.*` | `storefront.*` |
| 환경변수 접두 | `ORDER_`·`ORDERPLATFORM_`·`ORDER_MIGRATION_`(배포 계약이라 유지, C-5) | `STOREFRONT_` |
| 이벤트 type 접두 | `kr.aladin.orderplatform` | `kr.aladin.storefront` |
| 멱등 기록(`*Intake` 검사) | `command_log` | 지정 필요 |

- **X-5** StoreFront `docs/package-conventions.md`(역할별 배치)는 이 문서 §5 가 대신한다.
- 슬라이스 검증의 e2e 는 StoreFront `scripts/e2e/run-all.sh` 다. 이 스크립트는 주문 서비스도 띄우므로 주문 서비스 슬라이스도 통과시킨다.
- DB 절차 로직 이관에서 주문 서비스가 앱 테스트로 옮길 사례의 원본은 `tools/entity` 의 검증 사례다.
- 저장소별 이행 계획·건수와 결정 기록은 Obsidian vault 의 `wiki/projects/order-platform/` 에서 관리한다.
