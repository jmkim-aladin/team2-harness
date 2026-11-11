# Kotlin 백엔드 구조 표준

BC 4계층 구조(`contexts/<bc>/{api,domain,usecase,data}`)를 쓰는 개발2팀 Kotlin 백엔드의 모듈·패키지·의존·트랜잭션 경계·DB 계층·크기 규칙이다. 주문 서비스(order-platform)와 StoreFront(storefront-server)가 첫 적용 대상이고, 같은 구조로 시작하는 새 서비스는 처음부터 따른다.

표준은 이 문서와 아래 두 문서다. 규칙 ID 는 세 문서가 함께 쓴다.

| 문서 | 내용 |
|---|---|
| [이름 규칙](./kotlin-backend-structure-standard-naming.md) | 포트·구현·설정·이벤트·오류·타입·파일·테스트 이름(`N`) |
| [검사 장치와 적용 절차](./kotlin-backend-structure-standard-enforcement.md) | 기준선, 규칙별 검사와 시점, 이행 순서, 두 저장소의 차이 |

[Kotlin/Spring 멀티프로젝트 애플리케이션 표준](./kotlin-spring-multi-project-application-standard.md)(이하 "멀티프로젝트 표준")이 앱별 배포·런타임·보안·관측 기준을 정한다. 이 표준은 그 문서가 예시로 남긴 모듈·패키지·이름을 구체 규칙으로 정한다. 두 문서가 다른 곳은 §2 에 있다.

근거: 2026-11-11 사용자 결정 — 두 저장소의 구조 실태 조사, 표준 초안, 독립 검토 두 번을 거쳐 결정 질문 Q-STD-1~8 을 채택했다. 결정 기록과 이행 계획은 Obsidian vault 의 `wiki/projects/order-platform/backend-structure-standard-draft-2026-11-11.md` 에 있다.

## 적용 강도와 규칙 ID

| 표기 | 의미 |
|---|---|
| **필수** | [지시 강도](../policies/instruction-precedence-policy.md)의 policy 등급이다. 검사로 강제한다. 저장소 결정으로 벗어날 수 없고, 다르게 하려면 이 표준을 먼저 고친다 |
| **기본** | heuristic 등급이다. 검사가 없다. 더 나은 방법이 있으면 바꾸고, 그 저장소 설계 결정에 규칙 ID 와 이유를 남긴다 |
| **운영** | 문서의 원본과 기록 방식을 정한다. 검사 대상이 아니다 |

멀티프로젝트 표준의 `MUST` 가 필수에, `SHOULD` 가 기본에 대응한다.

규칙 ID 는 `M`(모듈)·`P`(패키지)·`N`(이름)·`D`(의존)·`T`(트랜잭션 경계)·`DB`(DB 계층)·`S`(크기)·`C`(설정)·`X`(문서)다. 아키텍처 테스트의 규칙 주석에 같은 ID 를 적어 문서와 검사를 잇는다. 번호는 다시 쓰지 않는다(`M-5` 는 `M-4` 에 합쳐져 비어 있다).

## 1. 원칙

1. **구조로 강제하고 테스트로 감사한다.** 필수 규칙은 검사가 있고, 검사를 만들 수 없는 규칙은 기본으로 적는다 — 문장만 있는 규칙은 지켜지지 않는다.
2. **세 축을 겹치지 않게 쓴다.** 경계는 Gradle 모듈(BC × 계층)이, 탐색은 패키지(업무 기능)가, 뜻은 이름(역할 접두·접미)이 맡는다. 모듈이 이미 계층을 나누므로 패키지에서 계층·역할을 다시 나누지 않는다.
3. **이름 하나에 뜻 하나.** 접두·접미는 닫힌 목록에서 고르고, 접미의 뜻은 기계가 판정할 수 있는 효과로 정한다.
4. **저장소의 기존 원칙은 전제다.** BC 4계층, 다른 BC 는 `:api` 만, TX 는 usecase 에서 TX 포트로만, 스코프 격리, 이벤트 봉투·아웃박스, 다중 루트 등록부는 이 표준이 바꾸지 않는다. 금융 잠금은 "한 TX 가 영향 주문 전체를 첫 금융 쓰기 전에 한 번, 정해진 순서로 잠근다"는 규약이 전제이고, 구현 수단은 원칙 6 을 따른다.
5. **표준은 공통 뼈대만 정한다.** §3 의 기준에 드는 차이는 저장소 문서에 "표준과 다른 점"으로 남긴다.
6. **DB 에는 선언만 둔다.** DB 에는 표준 선언적 제약(PK·FK·UNIQUE·NOT NULL·CHECK)과 권한만 두고, 함수·트리거 같은 절차 로직은 두지 않는다. 검증·상태 변경·잠금·번호 발급·운영 명령·원장 점검은 앱이 맡는다(§6.3). [engineering-policy.md](../policies/engineering-policy.md) §PostgreSQL 구현 원칙과 같은 방향이라 예외 조항을 두지 않는다.

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

**이 표준이 우선하는 항목은 셋이다.** [engineering-policy.md](../policies/engineering-policy.md)의 가리키는 줄에 같은 셋을 적는다.

| 항목 | 멀티프로젝트 표준 | 이 표준 | 이유 |
|---|---|---|---|
| 나가는 포트의 자리 | 예시 트리에서 `application` | `domain.port` 패키지 | 적용 저장소의 아키텍처 테스트가 이 패키지를 기준으로 삼는다 |
| 통합 테스트의 자리 | `src/integrationTest` JVM Test Suite | `src/test` + `@IntegrationTest` 태그(`-PskipIntegration` 으로 태그째 뺀다) | 적용 저장소의 빌드 규약과 픽스처가 태그 방식이다 |
| usecase 의 Spring | application 은 Spring 을 모른다 | usecase 모듈의 조립 클래스(`*Configuration`)만 Spring 을 쓴다. 업무 구현 클래스는 Spring 을 모른다(D-1) | 조립을 모듈마다 두고 앱이 `@Import` 한다. 업무 코드의 순수성은 검사로 지킨다 |

그 밖(앱별 분리, 런타임, config·secret·health, 마이그레이션 실행 주체, 인증·인가, 관측성, 배포 계약)은 멀티프로젝트 표준을 그대로 따른다.

영속 기술과 런타임은 멀티프로젝트 표준의 선택 항목이다. 이 표준의 `Exposed*`·`ScopedTable` 같은 이름은 첫 적용 저장소의 선택(Exposed R2DBC, WebFlux)을 예로 든 것이고, 다른 기술을 고른 저장소는 구현 접두만 바꾼다.

## 3. 공통과 저장소별 차이

배포·데이터 구성에서 오는 차이, 도메인 어휘, 이미 저장소 밖으로 나간 계약은 저장소별로 남긴다. 그 밖은 공통이다.

- 저장소별로 남기는 것: 배포 단위 수와 TX 단계, 스코프 모델, 앱 수, 선택 모듈(`processes`·`query`), 마이그레이션 디렉터리 배치, 설정 키·환경변수 접두, 이벤트 type 접두·확장 속성, 업무 명사.
- 계약의 이름은 이 표준 밖이다. TypeSpec·OpenAPI 의 interface·operation 이름은 Kotlin 포트를 개명해도 그대로 둔다 — operationId 가 바뀌면 호출자가 깨진다. 대응은 포트 KDoc 에 계약 이름을 적어 잇는다.

## 4. 모듈 구성

| 모듈 | 경로 | 규약 플러그인 | 책임 | main 이 의존해도 되는 것 |
|---|---|---|---|---|
| 공용 언어 | `shared/kernel` | `domain` | 2개 이상 BC 가 쓰는 식별자·금액·오류 분류 | 없음 |
| 기술 포트 | `shared/common` | `domain` | 스코프·TX·시각·이벤트 포트 | kernel |
| 저장 기반 | `shared/persistence-<기술>` | `spring-library` | TX 구현·스코프 테이블·예외 번역·시각 변환 | common |
| 메시징 기반 | `shared/messaging` | `spring-library` | 아웃박스·봉투·릴레이·멱등 소비 | common, persistence |
| BC 얼굴 | `contexts/<bc>/api` | `domain` | 들어오는 포트, 계약 타입, 필요 포트(`api.spi`) | common |
| BC 모델 | `contexts/<bc>/domain` | `domain` | 애그리거트·불변식·나가는 포트 | kernel |
| BC 유스케이스 | `contexts/<bc>/usecase` | `spring-library` | 포트 구현·TX 경계·이벤트 소비 | 자기 domain·api, 다른 BC `:api`, common |
| BC 저장 | `contexts/<bc>/data` | `data` | 저장 포트 구현 | 자기 domain, persistence, common |
| 프로세스 api(선택) | `processes/<p>/api` | `domain` | 여러 BC 를 순서대로 부르는 흐름의 얼굴 | common |
| 프로세스 usecase(선택) | `processes/<p>/usecase` | `spring-library` | 흐름 구현. TX 를 열지 않는다 | 자기 process api, 참여 BC `:api`, common |
| 조회(선택) | `query/<surface>` | `query` | 조회 전용 읽기 모델 | kernel |
| 외부 어댑터 | `integrations/<system>/<capability>`(+ `core`) | `kotlin-library` 또는 `spring-library` | 외부 포트 구현, `core` 는 공용 클라이언트 | 대상 BC domain(허용 목록, D-4), common, 같은 system 의 `core`. 봉투를 번역하는 사건 어댑터는 shared messaging |
| 실행 앱 | `apps/<app>` | `spring-boot-app` | 들어오는 어댑터(HTTP·워커)와 조립 | BC `:api`·process api(호출), BC usecase·data·process usecase(조립 — `*Configuration` 만 참조), integrations(빈 등록), shared, 공용 앱 라이브러리 |
| 공용 앱 라이브러리(선택) | `apps/common` | `spring-library` | 여러 실행 앱이 함께 쓰는 인바운드 공통(필터·오류 응답). 실행 artifact 가 아니다 | BC `:api`, common |
| 구조 검사 | `architecture-test` | — | Konsist·ArchUnit 규칙과 위반 fixture | 전 모듈(테스트 의존) |

- **M-1 (필수)** 모듈 종류는 위 표가 전부다. 새 종류는 이 표준을 먼저 고친다 — 종류가 늘면 의존 규칙과 검사가 따라가지 못한다.
- **M-2 (필수)** BC 목록은 `gradle/contexts.txt` 하나가 정한다. BC 이름은 소문자 영문 한 단어(`[a-z]+`)이고 `contexts/` 디렉터리와 같다.
- **M-3 (필수)** 모듈 이름은 소문자 영문·하이픈이다. `integrations` 는 `<system>/<capability>` 두 단계다. **기본:** `core` 는 능력이 둘 이상 같은 클라이언트를 쓸 때만 둔다.
- **M-4 (필수)** 규약 플러그인은 `<service>.{kotlin-library, domain, spring-library, data, spring-boot-app, runtime-boundary, migrations}` 일곱이 공통이고 `query` 는 선택이다. 모듈은 위 표의 플러그인만 쓴다. `runtime-boundary` 는 D-8 을, `migrations` 는 DB-1 을 검사한다.
- **M-6 (필수)** main 의 의존은 `implementation()` 이다. main 의 `api()` 는 kernel·common 재노출에만 쓴다 — 전이 노출이 늘면 BC 의 얼굴(`:api`) 밖 타입이 새어 나간다. `testFixturesApi` 는 픽스처가 공개 타입으로 내놓는 테스트 라이브러리에 쓸 수 있다.

## 5. 패키지 배치

루트 패키지는 `kr.co.aladin.<service>` 아래에 모듈 종류별로 둔다: BC 계층 `<bc>.<layer>`, shared `shared.<module>`, integrations `integration.<system>.<capability>`(`core` 모듈은 `integration.<system>`), processes `process.<p>.<layer>`, apps `app.<app>`.

- **P-1 (필수)** 계층 모듈은 단일 패키지로 시작한다. 한 패키지의 main 파일이 15개를 넘으면 **업무 기능** 하위 패키지로 나눈다. api 모듈도 같고, api 의 기능 패키지 이름은 그 BC usecase 의 기능 패키지와 같게 짓는다. 고정 패키지(P-4)도 15개를 넘으면 `domain.port.<기능>`·`api.spi.<기능>` 으로 나눈다.
- **P-2 (필수)** 기능 패키지 이름은 소문자 한 단어다. 다른 BC 이름을 단독으로 쓰지 않는다 — BC 와 그 BC 를 다루는 기능이 이름으로 구분되지 않는다. 다른 BC 와 맞닿은 기능은 `{상대 BC}{행위}` 한 단어로 짓는다(`paymentrequest`·`fulfillmentrelease`). **기본:** 이름은 업무 명사이고 그 저장소 설계 문서의 책임 이름과 맞춘다.
- **P-3 (필수)** 역할 패키지를 만들지 않는다 — `command`·`handler`·`assembler`·`codec`·`policy`·`model`·`service`·`error`·`repository`·`table`·`configuration`. 파일이 하나뿐인 패키지도 만들지 않는다(계층 루트와 P-4 의 고정 패키지는 예외). `query` 는 예외로 허용한다 — `*Query` 포트 구현과 그 `internal` 협력 클래스만 담는 패키지 하나. 조회는 여러 기능의 사실을 한 읽기 모델로 합쳐서 기능 하나에 속하지 않는다.
- **P-4 (필수)** 고정 패키지는 둘이다. `domain.port`(와 그 하위)에는 그 BC 의 나가는 포트 인터페이스(저장 포트·외부 포트)를 전부 둔다. `api.spi`(와 그 하위)에는 다른 BC 가 구현하는 필요 포트를 둔다(D-3). 이 둘은 기능이 아니라 모듈의 경계라서 검사가 패키지 하위 전체를 기준으로 삼는다.
- **P-5 (필수)** 조립 클래스(`*Configuration`)는 계층 루트 패키지에 둔다.
- **P-6 (필수)** apps 는 들어오는 어댑터의 종류로 나눈다: `http`(핸들러·라우트·오류 응답), `worker`(주기 실행 진입점과 그 조립), `access`(인증·호출자·스코프 결정), 루트(Application·health·공통 조립). 어댑터 종류가 곧 변경 이유다. 파일이 15개 이하인 앱은 평면으로 둔다.
- **P-7 (기본)** integrations 와 shared 는 평면으로 두고, 15개를 넘으면 P-1 을 따른다.
- **P-8 (필수)** 한 클래스를 검사하는 테스트(`{대상}Test`)의 패키지는 대상 클래스의 패키지와 같다. 대상 클래스가 하나가 아닌 테스트는 자리가 정해져 있다 — HTTP 시나리오 테스트는 앱의 `http` 패키지(평면 앱은 앱 루트), 조립·통합 테스트는 그 모듈의 루트 패키지, 구조 검사는 `architecture-test` 의 `architecture` 패키지.
- **P-9 (필수)** `testFixtures` 의 패키지는 모듈 루트 패키지 + `.test` 다.

## 6. 의존·경계 규칙

### 6.1 모듈 의존

- **D-1 (필수)** main 의 모듈 의존은 §4 표의 마지막 열이 전부다. domain·api·kernel·common 은 Spring·영속 프레임워크·Reactor 를 모른다. usecase 모듈에서 Spring 을 쓰는 것은 조립 클래스(`*Configuration`)뿐이고, 업무 구현 클래스는 Spring 을 모른다(§2 의 우선 항목).
- **D-2 (필수)** 다른 BC 는 `:api` 만 본다. domain·api 모듈은 다른 컨텍스트 모듈에 의존하지 않는다.
- **D-3 (필수)** BC 의존 그래프(usecase → 다른 BC api)에는 순환이 없다. 역방향으로 알리거나 물어야 하면, 부르는 쪽 BC 가 자기 `api.spi` 에 필요 포트를 선언하고 상대 BC 의 usecase 가 구현한다. 필요 포트의 접미도 이름 규칙의 넷이다. 호출은 같은 프로세스 안의 동기 호출이라 한 TX 합류와 잠금 순서는 달라지지 않는다. 구현하는 BC 는 `api.spi` 의 타입을 자기 사건의 payload 로 그대로 쓰지 않고 자기 payload 타입에 옮겨 담는다 — 남의 계약 타입이 자기 사건 계약이 되면 소유가 뒤섞인다.
- **D-4 (필수)** contexts 밖 모듈(apps·integrations·shared·processes·query)의 컨텍스트 domain 의존은 허용 목록에 이유와 함께 있는 것만 된다. 이유는 둘뿐이다 — 어댑터가 그 BC 의 domain 포트를 구현한다, 앱이 그 포트 타입을 빈으로 등록한다. 쓰지 않는 허용 항목도 실패한다. 앱이 응답·화면에 쓰는 값은 api 타입으로 받는다.
- **D-5 (필수)** usecase 는 integrations 패키지를 모른다. 외부 호출은 `domain.port` 의 `*Port` 로만 하고 TX 람다 밖에서 부른다. TX 람다가 직접 부르는 것뿐 아니라, 람다가 부른 협력 메서드를 거쳐 부르는 것도 금지다. 검사가 외부 연동으로 보는 대상은 integration 패키지, `domain.port` 의 `*Port` 전부, `*Registry`·`*Client` 다.
- **D-6 (필수)** shared 는 contexts 를 모른다. kernel 은 의존이 없고 common 은 kernel 만 본다.
- **D-7 (필수)** 테스트 의존도 §4 표와 D-2 를 따른다. 다른 BC 의 usecase·data 를 테스트 의존으로 무는 것은 조립을 검사하는 apps 테스트와 전 모듈을 읽는 `architecture-test` 만 된다. data 테스트는 자기 BC 의 usecase 도 물지 않는다. 공용 대역·픽스처는 `testFixtures` 로 나눈다.
- **D-8 (필수)** 다른 서비스의 아티팩트·소스 빌드에 의존하지 않는다(`runtime-boundary`).

### 6.2 트랜잭션 경계

포트와 구현을 나누면 "TX 를 열기 전에 판정하고, 첫 문장에서 영향 주문 전체를 잠근다"는 전제가 깨지기 쉽고, 그 실패는 해당 경로에서 실행 중에만 드러난다.

- **T-1 (필수)** TX 를 여는 호출과 금융 잠금 호출은 포트 구현 클래스(`Default*`)와 사건 소비자(`*EventHandler`)의 메서드에만 둔다. 같은 패키지의 `internal` 협력 클래스는 TX 를 열지 않고 잠금을 잡지 않는다 — 잠금이 이미 걸렸다고 보는 본문만 갖고, 그런 메서드 이름은 `*Locked` 로 끝낸다. shared 의 TX 구현(persistence·messaging)은 이 규칙의 대상이 아니다.
- **T-2 (필수)** TX 밖에서만 불러야 하는 포트 메서드(스스로 TX 를 열기 전에 잠금 집합을 정하는 메서드, 외부 호출을 낀 처리기)에는 마커 어노테이션 `@OutsideTransaction`(`shared:common`)을 붙인다. 포트 선언에 붙인 마커는 구현에도 적용된다. TX 람다 안에서는 마커 메서드를 직접으로도, 협력 메서드를 거쳐서도 부르지 않는다. 정적 검사가 따라가지 못하는 호출은 T-5 가 맡는다.
- **T-3 (필수)** 한 TX 의 금융 잠금 집합은 첫 금융 쓰기 전에 한 번에 전부 선언한다. 포트가 다른 포트를 부르는 중첩에서는 바깥 TX 가 안쪽이 잠글 주문까지 먼저 잠근다. 잠금 구현은 선언한 집합 밖의 주문을 뒤에 잠그려 하면 거절한다 — 이 거절과 T-5 의 실행 기록이 이 규칙의 검사다.
- **T-4 (필수)** 다중 루트 등록부의 호출 지점은 클래스 전체 이름과 메서드까지 적고, 등록부 테스트가 메서드가 있는지 확인한다. 등록부에 오르는 것은 TX 를 여는 `Default*` 메서드다 — 클래스 이름만 보면 분할 뒤에도 통과하면서 낡는다.
- **T-5 (필수)** TX·잠금 실행 기록 고정 테스트를 `pinned_by` 로 건다. 대상은 다중 루트 등록부의 항목 전부와, TX 안에서 정적 검사가 따라가지 못하는 호출(다른 모듈의 포트, 실행 때 구현이 정해지는 호출)을 하는 TX 진입 메서드다 — 뒤의 것은 TX 경계 목록에 올린다. 정적 검사는 추적을 멈춘 지점의 진입 메서드가 두 목록 어디에도 없으면 실패한다. 고정 테스트는 실제로 연 TX 의 수와 순서, TX 마다 선언한 잠금 집합과 순서, TX 가 열린 동안 외부 포트·마커 메서드 호출이 없음, 아웃박스 적재를 단언한다. 포트·구현을 나누는 변경은 이 테스트를 고치지 않고 통과해야 한다.

근거: 2026-11-11 독립 검토 — 기존 등록부 테스트는 클래스 파일이 있는지만 봤고 기존 TX 검사는 람다의 직접 호출만 봤다. 협력 클래스로 나누면 검사 사각이 넓어진다.

### 6.3 DB 계층

- **DB-1 (필수)** 마이그레이션 파일에는 사용자 정의 함수·프로시저·트리거를 만들거나 고치는 문장을 쓰지 않는다 — `CREATE [OR REPLACE] FUNCTION`·`CREATE [OR REPLACE] PROCEDURE`·`CREATE [OR REPLACE] TRIGGER`·`CREATE CONSTRAINT TRIGGER`·`CREATE EVENT TRIGGER`, 그리고 기존 절차 객체를 바꾸거나 끄거나 쿼리를 다시 쓰는 `ALTER FUNCTION|PROCEDURE|ROUTINE|TRIGGER|EVENT TRIGGER|RULE|AGGREGATE|OPERATOR`·`CREATE [OR REPLACE] RULE`·`CREATE AGGREGATE|OPERATOR|CAST`·`ALTER TABLE … ENABLE|DISABLE [ALWAYS|REPLICA] TRIGGER|RULE`(행 보안 `ROW LEVEL SECURITY` 는 해당 없음). 금지 목록 밖의 드문 문장(`CREATE TRANSFORM`·`CREATE LANGUAGE`·외부 표 트리거)은 리뷰로 막는다. `DO` 블록이나 동적 SQL 안에서 만드는 것도 같다. 지우는 문장(`DROP`)은 쓸 수 있다. DB 에 두는 것은 PK·FK·UNIQUE·NOT NULL·CHECK 제약과 권한(`GRANT`·`REVOKE`·열 권한)이다. PostgreSQL 내장 함수, 기본값, identity, DOMAIN 의 CHECK, 뷰는 절차 로직이 아니라 쓸 수 있다.
  - 이미 함수·트리거가 있는 저장소는 채택 시점의 마이그레이션 파일을 **경로와 내용 해시**로 고정한다. 고정된 파일은 고치거나 지우지 못하고, 목록에 없는 파일은 날짜와 상관없이 새 파일로 검사한다.
  - 새 파일은 기존 함수의 본문 수정도 쓰지 못한다 — 기능 변경이 그 로직의 수정을 요구하면 그 검사를 앱으로 옮기는 일을 그 변경과 함께 한다.
  - 적용이 끝난 DB 에 남은 함수·프로시저·트리거는 채택 시점 객체의 부분집합이고 정의가 같아야 한다.
- **DB-2 (기본)** 절차 로직이 하던 일은 앱으로 옮긴다. 돈·수량 불변식(합계 일치, 초과 환불 금지)은 도메인이 금융 잠금 아래에서 쓰기 전에 검사한다. 수정·삭제 금지는 권한 회수로, 한 행의 값 검사는 `CHECK` 제약이나 도메인으로, 상태 전이는 애그리거트 행위 메서드와 기대 상태를 조건으로 건 UPDATE 로, 금융 잠금은 정해진 순서로 정렬한 `SELECT … FOR UPDATE` 로 바꾼다. 번호 발급·운영 명령·원장 점검은 앱 코드가 한다.
- **DB-3 (필수)** 업무 표에 쓰는 런타임 주체는 앱 하나다. 주체를 셋으로 나눈다 — 런타임(앱 로그인 계정과 그 계정이 상속하는 권한 그룹), 운영자(업무 표에 쓰는 권한도, 쓰는 함수의 실행 권한도 없다. 앱의 운영 포트로 명령한다), 마이그레이션 소유자(DDL 과 마이그레이션 파일에 적힌 백필만 한다). 쓰는 길이 하나여야 앱의 검사가 전부를 덮는다. 검사는 역할 이름이 아니라 상속을 포함한 유효 권한(`INSERT`·`UPDATE`·`DELETE`·`TRUNCATE`·열 권한)을 본다.
- **DB-4 (필수)** 앱의 원장 점검 쿼리를 매일 돌려 불변식 위반을 찾고 경보한다. 앱 검사가 놓친 것을 하루 안에 찾는 보강이다.
- **DB-5 (필수)** DB 예외 번역은 한 곳이다. 번역하는 것은 표준 제약 위반(유일·FK·CHECK·NOT NULL), 권한 거부, 경합(직렬화 실패·교착·잠금 대기 초과), 연결·자원 오류다. 기존 가드 트리거의 오류 번역은 그 가드를 앱으로 옮겨 지울 때까지 둔다.

DB-1 의 새 절차 로직 금지는 채택한 날부터 건다. DB-3·DB-4 의 끝 상태와 "남은 함수·트리거 0"은 구조 이행 뒤의 DB 절차 로직 이관이 채운다(시점은 검사 문서). RLS 정책은 권한 선언이라 막지 않는다.

근거: 2026-11-11 사용자 결정 — 정책의 금지(2026-10-26) 뒤에도 두 저장소의 마이그레이션이 함수·트리거를 계속 만들어, 금지를 문장이 아니라 마이그레이션 검사로 지키기로 했다.

## 7. 파일·코드 크기

- **S-1 (필수)** main 파일(`src/main`)은 800줄을 넘지 않는다. 목표는 400줄이다. 생성 코드는 세지 않는다.
- **S-2 (필수)** 테스트 파일(`src/test`·`src/testFixtures`)은 1,500줄을 넘지 않는다.
- **S-3 (필수)** 파일 하나의 최상위 타입 선언은 10개 이하다. `*Tables.kt`·`*Vocabulary.kt` 는 예외다(줄 수 한계는 적용). 선언을 sealed 부모 안에 넣어 수를 줄이는 우회를 막으려고 중첩 타입 선언도 센다.
- **S-4 (필수)** 한계를 넘는 기존 파일은 기준선으로 관리한다(검사 문서 §2).
- **S-5 (기본)** 나누는 순서: ① 포트별로 구현 클래스를 나눈다 ② 단계별(수락 TX·TX 밖 호출·결과 TX)이나 읽기·쓰기별로 같은 패키지의 `internal` 협력 클래스를 뺀다(T-1 을 지킨다) ③ 계산·조립은 domain 으로 내린다. 파일을 나눌 때 다른 파일이 쓰게 되는 `private` 최상위 선언은 `internal` 로 올린다 — 그대로 두면 컴파일이 깨진다.

## 8. 설정·환경변수

- **C-1 (필수)** 서비스가 만든 설정 키의 접두는 서비스 kebab 이름 하나다. 그 아래는 주제로 나눈다. `spring`·`server`·`management` 같은 프레임워크 키는 이 규칙의 대상이 아니다.
- **C-2 (필수)** 설정은 `@ConfigurationProperties` + `*Properties` 로만 읽는다. `Environment.getProperty` 와 `@Value` 는 쓰지 않는다 — 타입·필수 검사가 빠진다. contexts 의 모듈은 Spring 설정 API 를 읽지 않고 앱이 만든 `*Settings` 를 받는다.
- **C-3 (필수)** 필수 설정이 없으면 기동을 거절하고, 기본 DB·계정·비밀을 소스에 두지 않는다. 멀티프로젝트 표준의 `MUST` 를 잇는다. 검사는 저장소의 기동 테스트다.
- **C-4 (필수)** 설정 키 표를 저장소 한 곳에 두고 테스트가 대조한다. 값이 하나인 키는 `application.yml` 에 `${환경변수}` 로 명시한다. 목록·맵처럼 환경변수 이름이 실행 때 정해지는 키는 표에 이름 패턴으로 적고 테스트가 패턴을 대조한다.
- **C-5 (기본)** 환경변수 접두는 서비스마다 하나(`<SERVICE>_`)로 둔다. 이미 배포 계약이 된 접두는 바꾸지 않고 저장소 차이로 남긴다.

## 9. 문서 관례

- **X-1 (운영)** 이 표준(세 문서)이 원본이다. 저장소 문서는 표준을 가리키고 "표준과 다른 점"만 적는다 — 같은 규칙이 두 곳에 있으면 한쪽이 낡는다([claude-md-policy.md](../policies/claude-md-policy.md)).
- **X-2 (필수)** 근접 `CLAUDE.md` 는 소스가 있는 Gradle 모듈 디렉터리마다 하나다. 단 BC 는 계층마다 두지 않고 `contexts/<bc>/CLAUDE.md` 하나다. 내용은 규칙·경계·진입점만 둔다. 루트 프로젝트는 루트 `CLAUDE.md` 가 맡고 `build-logic` 은 대상이 아니다.
- **X-3 (기본)** 저장소 스킬 이름은 `architecture-guide`·`add-context`·`add-integration-adapter`·`shared-kernel` 넷으로 맞춘다. `architecture-guide` 의 공통 부분은 이 표준을 가리키고 저장소 차이만 남긴다.
- **X-4 (운영)** §3 이 허용한 저장소 차이와 기본 규칙의 대체는 그 저장소 설계 문서의 결정에 규칙 ID 와 함께 적는다. 필수 규칙은 저장소 결정으로 바꿀 수 없다 — 이 표준을 먼저 고친다. **기본:** 설계 문서 본문에는 클래스·포트·패키지 이름을 쓰지 않고 책임 이름으로 쓴다 — 본문이 채택 근거에 들어가는 문서 체계에서는 개명 하나가 채택 재검토를 부른다.
- **X-6 (기본)** 경보는 kebab-case 메시지 키에 건다 — 로거 이름(클래스 FQCN)은 개명·이동하면 바뀐다.

`X-5`(운영)는 저장소 하나의 기록이라 검사 문서 §7 에 있다.
