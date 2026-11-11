# Kotlin 백엔드 구조 표준 — 이름 규칙

[Kotlin 백엔드 구조 표준](./kotlin-backend-structure-standard.md)의 이름 규칙(`N`)이다. 적용 강도(필수·기본)와 규칙 ID 의 뜻은 그 문서를 따르고, 검사는 [검사 장치와 적용 절차](./kotlin-backend-structure-standard-enforcement.md)에 있다.

## 1. 포트와 구현

**들어오는 포트**는 api 모듈의 인터페이스 가운데 usecase 모듈의 클래스가 구현하는 것이다(`api.spi` 의 필요 포트는 다른 BC 의 usecase 가 구현한다). api 안에서만 구현되는 인터페이스(sealed 분기, 값 인터페이스)는 계약 타입이고 포트 이름 규칙의 대상이 아니다 — 인터페이스라는 이유만으로 포트로 보면 계약 타입이 위반으로 잡힌다.

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
| 외부 API 호출 타입 | `{System}{대상}Client` | `OrderPlatformClient` | |
| 한 포트의 구현이 여럿 | `{변형}{포트 이름}` | `{사건}EventHandler` | |

접미의 뜻은 호출자가 아니라 **효과**로 정한다 — 호출자 기준은 같은 포트가 두 접미에 걸치고, 효과는 검사할 수 있다. 위에서부터 먼저 맞는 것이 그 포트의 접미다.

| 순서 | 접미 | 뜻 |
|---|---|---|
| 1 | `*Query` | 읽기 TX 만 연다. 다른 포트에 넘길 때는 `*Query` 에만 넘긴다 — `*Intake`·`*Commands`·`*Listener` 는 쓸 수 있는 포트라 부르지 않는다 |
| 2 | `*Intake` | 요청 멱등 키를 받아 멱등 기록에 결과를 남기는 쓰기. 호출자가 밖인지 안인지는 따지지 않는다. 반환값이 없어도 멱등 기록을 남기면 `*Intake` 다 |
| 3 | `*Listener` | 반환값이 없는 통지. Kotlin 선언의 반환형이 `Unit` 이다 |
| 4 | `*Commands` | 그 밖의 쓰기 |

- **N-1 (필수)** 위 두 표. 읽기와 쓰기가 한 인터페이스에 섞인 포트는 쪼갠다. 포트 하나의 usecase 구현은 정확히 하나다. `Default` 는 usecase 의 포트 구현에만 쓴다.
- **N-2 (필수)** domain 안에는 `Default*` 구현을 두지 않는다. 도메인 서비스는 구체 클래스나 `object` 다.
- **N-3 (기본)** 저장 포트의 읽기 메서드 접두는 `get`(없으면 예외)·`find`(null)·`list`·`count`·`is` 로 닫는다. 쓰기 메서드는 상태 전이를 드러내는 동사(`open`·`mark`·`record`·`create`)를 쓴다 — `save` 하나로 모으면 어떤 전이인지 이름에서 사라진다.

## 2. 조립·설정·진입점

| 접미 | 뜻 | 위치 |
|---|---|---|
| `*Configuration` | `@Configuration` 조립. 계층 모듈은 `{Bc}{Layer}Configuration` | 모듈마다, 앱이 `@Import` |
| `*Properties` | `@ConfigurationProperties` 로 묶는 클래스와 그 중첩 값 | apps, 자기 설정을 가진 shared 기술 모듈 |
| `*Settings` | 설정 어노테이션이 없는 순수 값. usecase·domain 이 생성자로 받는다 | usecase·shared |
| `*EventHandler` | 사건 소비자 | usecase |
| `*Handler` | HTTP 요청 하나를 처리한다. `{동사}{대상}Handler` | apps `http` |
| `*RouterConfiguration` | 라우터 빈만 둔다. 경로 → 핸들러 메서드, 로직 없음 | apps `http` |
| `*Worker` | 주기 실행 진입점(`SmartLifecycle`). 로직은 usecase·shared 의 접미 없는 업무 명사가 갖는다 | apps `worker` |

- **N-4 (필수)** 위 표. `*Scheduler` 와 shared 의 `*Worker` 는 쓰지 않는다. `*EventHandler` 를 먼저 가려내고, 그 밖의 `*Handler` 는 HTTP 전용이다 — 같은 접미가 두 뜻이면 이름으로 역할을 찾을 수 없다.

## 3. 이벤트·오류·타입

- **N-5 (필수)** CloudEvents type 은 `kr.aladin.<service>.<producer_bc>.<event-type>.v<n>` 이고 `<event-type>` 은 kebab-case 다. 이미 등록된 타입은 계약이라 그대로 두고 판을 올릴 때 바꾼다. **기본:** `<event-type>` 은 과거형 사실로 짓는다(`payment-failed`).
- **N-6 (기본)** 발행 사건을 만드는 타입은 `{과거형 사실}Event`, 묶음은 `{주제}Events`, 소비 쪽 type 상수는 `{Producer}EventTypes` 로 짓는다.
- **N-7 (필수)** 오류 코드는 `enum class {주제}ErrorCode`, 상수는 `UPPER_SNAKE`, 파일은 `{주제}ErrorCode.kt` 단독이다. 접미 `*ConflictCode` 는 저장 시점의 유일성 충돌 전용이다 — data 가 유일 제약 위반을 바꿔 던지고 usecase 가 잡아 거래 거절로 옮기는 코드다.
- **N-8 (필수)** usecase 모듈에는 오류 코드를 두지 않는다. **기본:** 위치는 던지는 쪽과 잡는 쪽이 모두 볼 수 있는 가장 낮은 계층이다 — 도메인이나 data 가 던지면 `domain`(usecase 는 data 를 볼 수 없다), 유스케이스가 던져 다른 BC·앱이 계약으로 보면 `api`, apps·integrations·shared 자신의 오류는 자기 모듈.
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
- **N-11 (필수)** 테이블 객체는 `internal object` 이고 `Table` 접미는 기반 클래스만 쓴다. **기본:** 이름은 복수 명사다.

## 4. 파일·테스트·중복

- **N-12 (필수)** 파일 이름은 그 파일의 주 선언(포트 인터페이스·애그리거트·구현 클래스) 이름이다. 파일 하나에 포트 인터페이스는 하나다. 그 포트만 쓰는 요청·결과 타입은 같은 파일에 둘 수 있다(크기 한계 안). **기본:** 둘 이상의 포트가 쓰는 타입은 자기 파일을 갖는다.
- **N-13 (필수)** 묶음 파일 접미는 셋뿐이다: `*Tables.kt`(테이블 객체), `*Vocabulary.kt`(작은 enum·value class), `*Fakes.kt`(테스트 대역). `*Api.kt`·`*Ports.kt`·`*Enums.kt`·`*Values.kt` 는 쓰지 않는다 — 파일 이름으로 선언을 찾을 수 없다.
- **N-14 (필수)** 테스트 클래스는 `{대상}Test` 다. HTTP 테스트 클라이언트로 앱의 HTTP 표면을 부르는 apps 테스트는 `{기능}HttpTest` 이고, 그 이름은 그런 테스트에만 쓴다. 메서드는 백틱 문장이다. 통합 표식은 픽스처 어노테이션 `@IntegrationTest` 만 쓴다(`@Tag` 는 그 어노테이션의 정의에만 있다). 대역 접두는 `Fake*`(동작하는 인메모리 구현)·`Recording*`(호출 기록)·`Fixed*`(고정 값), 환경 픽스처는 `*Fixture`, 표본 데이터는 `*Samples` 다. **기본:** 메서드 문장은 한국어로 쓴다.
- **N-15 (필수)** 같은 BC 안(api·domain·usecase·data)의 main 에서 최상위 타입 선언(class·interface·object·typealias)의 단순 이름은 겹치지 않는다. api 타입은 접미를 갖고 domain 은 접미 없는 명사를 쓰므로 겹칠 이유가 없다.
- **N-16 (기본)** BC 가 다르면 같은 이름을 각자 가질 수 있다. 뜻과 값이 같고 둘 이상의 BC 가 쓰면 kernel 승격을 검토한다.
- **N-17 (기본)** 업무 명사는 그 저장소 도메인 모델 문서의 용어(`name`·`aliases`)에서 가져온다. 새 명사는 용어에 먼저 올린다.
