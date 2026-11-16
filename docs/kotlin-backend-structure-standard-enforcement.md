# Kotlin 백엔드 구조 표준 — 검사 장치와 적용 절차

[Kotlin 백엔드 구조 표준](./kotlin-backend-structure-standard.md)과 [이름 규칙](./kotlin-backend-structure-standard-naming.md)의 필수 규칙을 무엇으로, 언제부터 검사하는지와 기존 저장소에 적용하는 순서다. 규칙의 정의는 두 문서에 있고 여기서는 규칙 ID 로만 가리킨다.

## 1. 검사를 두는 방식

- 규칙은 각 저장소의 `architecture-test`(Konsist·ArchUnit·텍스트 검사)와 `build-logic`(Gradle 플러그인)에 넣는다. 저장소끼리는 아티팩트·소스에 의존하지 않으므로 규칙 코드는 복사하고, 규칙 ID 를 주석에 적어 표준과 대조한다.
- 규칙마다 통과 fixture 와 위반 fixture 를 함께 둔다 — 위반만 있으면 정상 코드를 잡는 오탐을 모른다. 새 규칙은 기존 위반 fixture 패키지를 대상에서 뺀다.
- 기본: 소스·클래스 수집은 한 번 하고 규칙들이 그 결과를 함께 쓴다. 마이그레이션·경로 같은 정적 검사는 DB 없이 따로 돌 수 있게 하고 `check` 가 모은다 — 규칙이 늘어도 검사 시간이 규칙 수만큼 늘지 않게 한다.
- 검사가 규칙의 일부만 보면 아래 표의 "검사 내용"에 본 범위를 적는다. 정적 검사가 증명하지 못하는 것은 행동 테스트나 운영 확인으로 나눈다.

## 2. 기준선

기존 저장소에 새 규칙을 넣을 때 위반이 10건 안쪽이고 파일을 옮기지 않아도 되면 바로 고친다. 위반이 많은 규칙(이름·패키지·크기)은 기준선으로 넣는다.

- 기준선은 규칙마다 파일을 따로 두고, 항목마다 대상(파일·선언)과 측정값(줄 수·선언 수), `owner`·`ticket` 을 적는다 — 한 파일에 몰리면 병렬 브랜치가 늘 충돌하고, 담당이 없으면 영구히 남는다.
- 검사는 기준 브랜치의 기준선과 지금 기준선을 **항목 집합으로** 비교한다. 기준 브랜치에 없던 항목이 생기면 실패한다. 항목의 측정값은 허용값보다 늘 수 없다. 위반이 사라지면 항목을 지워야 통과한다.
- 개명·이동은 같은 커밋에서 옛 키 → 새 키 대응을 기준선에 적어 넘긴다. 대응이 없는 새 키는 새 위반이다.
- 항목 수 상한은 보조 조건이다 — 상한만 보면 위반 하나를 고치고 다른 위반 하나를 넣는 교체를 막지 못한다.

## 3. 적용 시점

| 표기 | 뜻 |
|---|---|
| **즉시** | 검사를 넣는 날부터 위반 0 으로 통과한다(R1) |
| **기준선** | 검사를 넣는 날 위반을 기준선에 등록하고, 이행하며 줄인다(R1 → R3·R4) |
| **안전망** | 포트·구현을 나누기 전에 넣는다(R2) |
| **DB 이관** | 구조 이행 뒤 DB 절차 로직 이관의 수용 조건이다. 이관 전에는 충족할 수 없어 그때 건다 |

## 4. 검사 목록

| 규칙 | 검사 내용 | 방식 | 시점 |
|---|---|---|---|
| M-1·M-3·M-4 | 모듈 경로 종류와 규약 플러그인의 대응([표준 §4 의 모듈 표](./kotlin-backend-structure-standard.md#4-모듈-구성), 실행 앱·공용 앱 라이브러리·프로세스 api/usecase 구분), `apps/<app>`의 `spring-boot-app`·`standalone-app` 상호 배타, standalone의 per-app classpath allowlist와 기본 거부 목록, 모듈 이름 형식 | Gradle 모델·해석 classpath·텍스트 | 즉시 |
| M-2 | `contexts.txt` 와 `contexts/` 디렉터리가 같다 | settings·테스트 | 즉시 |
| M-6 | main 의 `api()` 는 kernel·common 에만. 규약 플러그인이 넣는 의존 포함 | Gradle 모델 | 즉시 |
| P-1 | 패키지 선언 기준으로 패키지당 main 파일 15개 이하(api·고정 패키지 포함) | Konsist | 기준선 |
| P-2·P-3 | 하위 패키지 이름이 소문자 한 단어이고 BC 이름 단독·역할 금지어가 아니다. 파일 하나짜리 패키지 없음(계층 루트·고정 패키지 예외). `query` 패키지의 클래스는 `*Query` 구현이거나 `internal` 이고 쓰기 TX 를 열지 않는다 | Konsist | 기준선 |
| P-4 | data·integrations 가 구현하는 domain 인터페이스는 `domain.port` 하위에 있다. `api.spi` 하위의 인터페이스는 자기 BC usecase 가 구현하지 않는다 | ArchUnit | 기준선 |
| P-5 | `*Configuration` 은 계층 루트 패키지에 있다 | Konsist | 기준선 |
| P-6 | 하위 패키지를 둔 앱에서 `SmartLifecycle` 구현은 `..worker..`, `*Handler` 는 `..http..`. 파일 15개를 넘는 앱은 평면이 아니다 | ArchUnit·Konsist | 기준선 |
| P-8 | `{X}Test` 와 이름이 맞는 `X` 가 같은 모듈 main 에 있으면 같은 패키지다. 없으면 P-8 이 정한 자리(앱 `http`·모듈 루트·`architecture`)에 있다 | Konsist | 기준선 |
| P-9 | testFixtures 의 패키지는 모듈 루트 + `.test` | Konsist | 즉시 |
| N-1(이름) | usecase 가 구현하는 api 인터페이스(§5.3 의 포트 분류)의 접미가 닫힌 집합이다. 포트마다 usecase 구현이 정확히 하나이고 이름이 `Default{포트}` 다. contexts 의 data 구현은 data 에만 있고 `internal` 이다. `*Adapter`·`*Impl` 없음 | ArchUnit·Konsist | 기준선 |
| N-1(효과) | `*Query` 구현은 쓰기 TX 를 열지 않고 `*Query` 가 아닌 포트(`*Intake`·`*Commands`·`*Listener`)에 의존하지 않는다. `*Intake` 구현이나 그 협력 클래스가 멱등 기록 포트에 의존한다. `*Listener` 메서드의 Kotlin 선언 반환형이 `Unit` 이다 | ArchUnit·Konsist(§5.3) | 기준선 |
| N-2 | domain 에 `Default*` 없음 | Konsist | 기준선 |
| N-4 | `*EventHandler` 를 먼저 가린 뒤 `*Handler` 는 apps 에만. `*Worker` 는 apps 의 `SmartLifecycle`. `*Scheduler` 없음. `*Properties` 는 `@ConfigurationProperties` 가 있거나 그 중첩 타입 | Konsist | 기준선 |
| N-5 | 이벤트 타입 등록 파일의 새 타입이 type 문법(접두·판·kebab-case)에 맞다. 과거형인지는 보지 않는다 | 테스트 | 즉시(새 타입) |
| N-7·N-8 | 오류 코드 enum 의 이름이 `*ErrorCode` 또는 `*ConflictCode`(domain 에만), 상수 `UPPER_SNAKE`, 파일 단독이고 usecase 모듈에 없다 | Konsist | 기준선 |
| N-10·N-11 | `*Dto` 는 integration 패키지에만. 테이블 객체는 `internal object` 이고 `Table` 접미가 없다 | Konsist | 기준선 |
| N-12·N-13 | 파일 이름과 같은 선언이 있거나 허용 묶음 접미다. 파일 하나에 포트 인터페이스가 둘 이상 없다 | Konsist + ktlint | 기준선 |
| N-14 | 테스트 클래스 이름 `*Test`. HTTP 테스트 클라이언트 타입을 쓰는 apps 테스트는 `*HttpTest` 이고 그 이름의 테스트는 그 타입을 쓴다(이름이 아니라 쓰는 타입으로 가린다). 메서드 이름이 백틱 문장. `@Tag("integration")` 은 `@IntegrationTest` 정의에만. 테스트 대역 이름에 금지 접두(`InMemory*`·`Memory*`·`Mock*`·`Stub*`) 없음. 대역이 접두의 뜻대로 동작하는지와 `*Fixture`·`*Samples` 의 뜻은 검토가 본다 | Konsist | 기준선 |
| N-15 | 같은 BC 의 main 에서 최상위 타입 선언의 단순 이름 중복 없음(테스트·함수·프로퍼티 제외) | Konsist | 기준선 |
| D-1 | main 의 project 의존이 [표준 §4 의 모듈 표](./kotlin-backend-structure-standard.md#4-모듈-구성) 안이다(integrations 의 같은 system `core`·shared messaging, 앱의 process api 포함). Spring 앱이 BC usecase·data·process usecase 에서 참조하는 타입은 `*Configuration` 뿐이고, standalone 앱은 프레임워크 없는 공개 조립 타입만 참조한다. standalone의 project/runtime classpath allowlist와 해석 classpath에 Spring·JPA·DB driver·Secrets Manager·AI provider SDK가 들어오지 않는다. domain·api·kernel·common 에 프레임워크 의존 없음. usecase 에서 Spring 을 쓰는 클래스는 `*Configuration` 뿐이다 | Gradle 모델 + ArchUnit | 즉시(기존 검사)·기준선(앱의 참조·usecase Spring) |
| D-2·D-3 | main 의존으로 만든 BC 그래프에 `:api` 밖 의존과 순환 없음. 컴파일된 클래스의 BC 조각에도 순환 없음 | Gradle 모델 + ArchUnit | 기준선 |
| D-4 | contexts 밖의 domain 의존 허용 목록과 낡은 항목 | 텍스트(build 파일) | 즉시 |
| D-5·T-2 | TX 람다와 거기서 닿는 협력 메서드 안에 외부 연동 호출·마커 메서드 호출 없음(§5.2 의 범위). usecase → integration 의존 없음 | ArchUnit + 고정 테스트 | 즉시(직접 호출)·안전망(전이·마커) |
| D-6·D-7 | shared 에 `:contexts:` 의존 없음. 테스트 의존에도 [표준 §4 의 모듈 표](./kotlin-backend-structure-standard.md#4-모듈-구성)·D-2(apps·`architecture-test` 제외) | Gradle 모델 | 즉시(D-6)·기준선(D-7) |
| D-8 | 해석된 클래스패스에 다른 서비스 아티팩트·다른 빌드 프로젝트 없음 | Gradle `runtime-boundary` | 즉시 |
| T-1 | usecase 모듈에서 `Default*`·`*EventHandler` 가 아닌 클래스는 TX 를 열지 않고 금융 잠금을 부르지 않는다(람다는 그 람다를 가진 메서드로 본다) | ArchUnit | 기준선 |
| T-3 | 고정 테스트의 실행 기록에서 잠금 선언이 첫 금융 쓰기보다 앞이다. 잠금 구현이 집합 밖 주문의 뒤늦은 잠금을 거절한다 | 행동 테스트(통합) | 안전망 |
| T-4·T-5 | 등록부 호출 지점의 클래스 전체 이름·메서드가 있다. 다중 루트 등록부와 TX 경계 목록의 항목마다 `pinned_by` 테스트가 있고 TX·잠금 집합·TX 가 열린 동안 외부·마커 호출 0·아웃박스를 단언한다. 정적 검사가 TX 안에서 추적을 멈춘 진입 메서드가 두 목록에 없으면 실패한다 | 등록부 테스트 + ArchUnit + 고정 테스트 | 안전망 |
| DB-1(파일) | 고정 목록의 파일이 내용 해시까지 그대로다. 목록 밖 파일에 금지 문장이 없다(§5.1) | Gradle `migrations` | 즉시 |
| DB-1(끝 상태) | 적용이 끝난 DB 의 함수·프로시저·트리거가 채택 시점 객체의 부분집합이고 정의가 같다(§5.1) | 통합 테스트 | 즉시 |
| DB-1(0건) | 남은 함수·프로시저·트리거가 없다 | 통합 테스트 | DB 이관 |
| DB-3 | 허용한 주체 밖에 업무 표 쓰기 유효 권한이 없다. 운영자 역할의 쓰기가 거부된다(§5.4) | 통합 테스트 | DB 이관 |
| DB-4 | 원장 점검이 앱 쿼리로 돌고 위반을 찾는다(테스트). 매일 실행과 경보 전달은 운영 확인 | 저장소 테스트 + 운영 확인 | DB 이관 |
| DB-5 | 예외 번역이 한 곳이다. SQLSTATE 별 번역(제약·권한·경합·연결)이 맞다 | ArchUnit + 단위 테스트 | 즉시 |
| S-1~S-4 | 파일 줄 수(생성 코드 제외), Kotlin 파서로 센 타입 선언 수(중첩 포함), 기준선(§2) | Konsist·텍스트 | 기준선 |
| C-1·C-2 | `@ConfigurationProperties` 의 prefix 와 서비스가 만든 `application.yml` 키가 서비스 접두다(프레임워크 키 제외). Spring 앱에는 `Environment.getProperty`·`@Value` 없음. `standalone-app`은 앱 루트의 단일 `*Environment` 디코더가 고정 allowlist의 `System.getenv("LITERAL_NAME")`만 읽고 순수 `*Settings`로 바꾸는 예외만 허용한다. `source: file` 항목(예: `LAMP_BROKER_CA_FILE`)은 허용 root·최대 크기·regular file·권한·symlink 정책을 검사한 뒤 읽으며, contexts 모듈은 Spring `Environment`를 모른다 | Konsist·ArchUnit·텍스트·YAML 파싱 | 즉시·기준선 |
| C-3 | 필수 설정이 없으면 기동이 거절된다 | 저장소 기동 테스트 | 즉시 |
| C-4 | 설정 키 표와 `application.yml` 대조. 동적 키는 이름 패턴 대조 | 저장소 테스트 | 즉시 |
| X-2 | 소스가 있는 Gradle 모듈 디렉터리(BC 는 `contexts/<bc>`)에 `CLAUDE.md` 가 있고 BC 계층 디렉터리에는 없다 | 텍스트 | 즉시 |
| (테스트) | main 소스가 있는 domain·usecase·data 모듈에 테스트가 하나 이상 있다 | 텍스트 | 기준선 |

검사가 없는 규칙은 기본·운영이다: P-7, N-3·N-6·N-9·N-16·N-17, S-5, C-5, DB-2, X-1·X-3·X-4·X-5·X-6, 그리고 필수 규칙 안의 "기본:" 부분(M-3 의 `core` 조건, P-2 의 업무 명사, N-5 의 과거형, N-8 의 위치, N-11 의 복수 명사, N-12 의 공용 타입, N-14 의 한국어).

## 5. 검사 계약

### 5.1 DB-1 — 마이그레이션

검사는 세 가지 책임으로 나눈다. 하나로 합치면 기준선 파일의 본문 변경과 같은 수의 객체 교체를 놓친다.

1. **고정 목록**: 표준을 채택한 시점의 마이그레이션 파일을 저장소 상대 경로와 내용 SHA-256 으로 적는다. 목록의 파일이 바뀌거나 없어지면 실패한다. 목록에 없는 파일은 파일 이름의 날짜와 상관없이 새 파일이다. 목록에 항목을 더하는 변경은 기준 브랜치와 비교해 실패시킨다 — 새 함수 파일을 넣고 목록도 같이 고치는 자기 승인을 막는다.
2. **새 파일의 문장 검사**: 금지 문장은 `CREATE [OR REPLACE] FUNCTION`·`PROCEDURE`·`TRIGGER`, `CREATE CONSTRAINT TRIGGER`, `CREATE EVENT TRIGGER`, `ALTER FUNCTION|PROCEDURE|ROUTINE|TRIGGER|EVENT TRIGGER|RULE|AGGREGATE|OPERATOR`, `CREATE [OR REPLACE] RULE`, `CREATE AGGREGATE|OPERATOR|CAST`, `ALTER TABLE … ENABLE|DISABLE [ALWAYS|REPLICA] TRIGGER|RULE` 다(2026-11-11 두 저장소 구현과 맞춤 — 통과 예: `ROW LEVEL SECURITY`·`OPERATOR CLASS|FAMILY`·`DROP`·`GRANT EXECUTE`). 남은 드문 문장(`CREATE TRANSFORM`·`CREATE LANGUAGE`·외부 표 트리거)은 검사 밖이라 리뷰로 막는다. `DO` 블록은 쓸 수 있지만 본문과 `EXECUTE` 문자열에 금지 문장이 있으면 실패하고, 문장을 읽을 수 없는 동적 SQL(리터럴 틀 없이 변수만으로 만든 문장)도 실패한다 — 읽을 수 없으면 통과가 아니라 실패다. 주석, 일반 문자열, `COMMENT ON` 안의 글자는 문장이 아니다.
3. **끝 상태**: 마이그레이션을 다 적용한 DB 에서 서비스가 소유한 스키마의 함수·프로시저(스키마·이름·인자 서명·정의), 내부 FK 트리거를 뺀 사용자 트리거, 이벤트 트리거를 읽는다. 채택 시점 객체 집합의 부분집합이고 남은 객체의 정의가 같아야 한다. 시스템·확장이 소유한 객체는 뺀다.

- 연결: 저장소의 `check` 와 마이그레이션 실행 진입점 앞에 건다. 파일 이름·디렉터리 규칙은 저장소마다 달라서 다른 저장소 것을 복사하지 않는다.
- fixture: 직접 `CREATE`·`OR REPLACE`(대소문자·줄바꿈·주석을 끼운 것 포함) 실패, 고정 목록 파일의 한 글자 변경 실패, 과거 날짜의 새 파일은 검사 대상, 문자열·주석·`COMMENT ON` 속 글자 통과, `DO`·`EXECUTE` 로 만든 함수 실패, 읽을 수 없는 동적 SQL 실패, `DROP` 통과, FK·CHECK·권한·뷰·identity 통과, 목록에 몰래 넣은 새 파일 실패, 인용 안의 세미콜론을 문장 끝으로 보지 않음.
- 한계: 빈 DB 에 전부 적용하는 검사는 운영 DB 의 적용 이력 불일치를 재현하지 않는다(고정 목록이 그 자리를 맡는다). 수동 실행 경로가 이 검사를 거치는지는 배포 계약에서 확인한다.

### 5.2 D-5·T-1·T-2 — TX 안 호출

- 범위: TX 람다에서 시작해 그 안의 람다(중첩 suspend 포함)와, 람다가 부르는 같은 BC usecase 의 메서드를 따라간다. 인터페이스 호출은 선언 타입으로 판정하고, 마커는 포트 선언과 그 구현(override)에 함께 적용한다. 기본 인자·합성 메서드는 원래 선언으로 되돌려 본다.
- 정적 검사가 닿지 않는 것: 다른 모듈로 넘어간 뒤의 호출, 리플렉션, 실행 때 정해지는 구현. 검사는 여기서 조용히 통과시키지 않는다 — TX 안에서 추적을 멈춘 지점이 있으면 그 TX 진입 메서드가 다중 루트 등록부나 TX 경계 목록에 있어야 하고, 항목마다 고정 테스트(T-5)가 걸려 있어야 한다. TX 경계 목록은 다중 루트가 아닌 경로(단일 루트 쓰기 중 다른 모듈 호출, 등록부 밖 외부 호출 경로)를 적는 별도 목록이다.
- 고정 테스트의 관찰: 기록용 TX 매니저와 기록용 외부 포트로 "TX 가 열린 동안 외부 포트 호출 0"을 본다. 마커 메서드는 외부 포트만 기록해서는 보이지 않으므로 테스트 대역이나 감싸개로 마커 메서드 호출도 기록한다.
- fixture: 람다의 직접 호출, 협력 메서드를 거친 호출, 인터페이스를 거친 호출, 기본 인자가 있는 메서드, 중첩 suspend 람다, TX 밖 호출(통과).

### 5.3 포트 분류와 접미 효과

- 포트 분류: api 모듈의 인터페이스를 "usecase 모듈의 클래스가 구현하는 것(포트)"과 "api 안에서만 구현되는 것(계약 타입)"으로 나눈다. 어디서도 구현하지 않는 인터페이스는 실패다. 접미 검사는 포트에만 건다.
- `*Listener`: Kotlin 소스의 선언 반환형으로 본다. JVM 반환형으로 보면 `suspend` 함수가 전부 실패한다(`suspend fun … : Unit` 은 JVM 에서 `Object` 를 돌려준다). fixture 는 `suspend` Unit, 생략한 Unit, 일반 Unit, 값 반환, 상속·기본 구현 메서드.
- `*Query`: 직접 쓰기 TX 를 열지 않는 것과 `*Query` 가 아닌 포트에 의존하지 않는 것까지 본다. `*Listener` 도 여기에 든다 — 반환값만 없을 뿐 쓸 수 있다. fixture 는 `*Query` → `*Query` 위임(통과), `*Query` → 쓰는 `*Listener`(실패). 그 밖의 경로로 쓰는지는 증명하지 못한다.
- `*Intake`: 멱등 기록 포트 의존은 근사치다. 결과가 실제로 기록되는지는 같은 키로 다시 부르는 테스트가 본다.

### 5.4 DB-3 — 권한

배포 단위마다 런타임 로그인 계정, 그 계정이 상속하는 권한 그룹, 마이그레이션 소유자를 허용 주체로 적는다. 검사는 업무 표마다 역할의 유효 권한(상속 포함, `INSERT`·`UPDATE`·`DELETE`·`TRUNCATE`·열 권한)을 읽어 허용 주체 밖에 쓰기 권한이 없는지 본다. 운영자 역할로 쓰기를 시도해 권한 거부가 나는 사례도 둔다. 계정이 하나라는 사실이 앱 코드만 쓴다는 증명은 아니다 — 소유자 계정의 사용 경계는 운영 통제다.

### 5.5 M-1·M-4·C-2 — standalone-app

`standalone-app`은 Spring 앱을 표준에서 빼기 위한 저장소별 우회가 아니라, Spring 없는 실행 artifact를 같은 경계 검사 아래 두기 위한 정식 모듈 계약이다. 작은 이미지와 제한된 자원만 주는 실행 주체가 Spring·DB·provider 자격증명을 실수로 끌어오지 않게 하는 것이 목적이다. 일반 standalone과 보안 격리 standalone은 같은 plugin을 쓰되 `mode`와 per-app classpath allowlist로 구분한다. `strict`는 untrusted input·단기 grant·격리 worker/runner처럼 실행 경계가 필요한 앱에만 쓰며, allowlist가 없으면 통과하지 않는다.

검사는 다음 세 가지를 함께 본다.

1. **Gradle 계약(M-1·M-4)**: `apps/<app>` 모듈은 `standalone-app` 또는 `spring-boot-app` 하나만 적용한다. standalone 모듈은 고정 main/실행 JAR를 만들고 Spring Boot plugin·starter·runtime을 가져오지 않으며, per-app project/runtime classpath allowlist와 해석 classpath를 함께 검사한다. Spring·JPA·DB driver·Secrets Manager·AI provider SDK 계열은 기본 거부하며 명시 allowlist로도 재허용하지 않는다. `strict` 앱은 untrusted input·grant·격리 worker/runner에 필요한 최소 integration만 허용하고, `runtime-boundary`와 같은 D-8 검사를 통과해야 한다. `apps/common`은 실행 artifact가 아니므로 standalone plugin 대상이 아니다.
2. **bootstrap 디코더(C-2)**: standalone 앱 루트(`app.<app>`)에는 환경을 읽는 단일 `*Environment` 디코더만 둔다. 저장소의 모든 `src/main` Kotlin 소스를 스캔해 이 디코더 밖의 `System.getenv`·직접 파일 읽기와 contexts/usecase/integration의 우회를 실패시킨다. `Files`의 알려진 읽기 API뿐 아니라 `Files.newInputStream`, `File`/`FileInputStream`/`FileChannel`, `Path`·`Paths`, Kotlin stream 확장, `Channels`·`URL` 등 직접 파일 I/O 호출은 secure reader 밖에서 fail-closed로 거절하고, 가능하면 컴파일된 callsite/AST 규칙도 함께 실행한다. 디코더의 `System.getenv("LITERAL_NAME")` 호출은 저장소 설정표에 적힌 고정 allowlist와 일치해야 하며, `System.getenv()` 전체 맵·동적 이름·임의 파일 fallback·환경변수 탐색은 실패한다. 설정표가 `source: file`로 등록한 `LAMP_BROKER_CA_FILE` 같은 값은 허용 root 아래의 절대 경로·regular file을 확인하고 root·최종·중간 경로 구성요소의 symlink를 모두 거절한 뒤, 상한을 넘지 않는 bounded stream으로 읽는다. POSIX 권한을 확인하지 못하면 실패시키며 group/world writable은 기본 거절하고, 읽기 권한은 배포 주체 기준 allowlist 정책으로 명시한다(Kubernetes Secret/ConfigMap의 0444 또는 `fsGroup` 읽기도 해당 배포 정책에 등록할 수 있다). `material: public-ca`는 실제 Deployment/Pod manifest의 serviceAccount·fsGroup·readOnly volume·0444 매핑과 선언을 함께 검증한다. 디코더는 즉시 프레임워크 없는 `*Settings`로 변환하고, contexts·usecase·integrations의 다른 소스는 환경변수·파일을 직접 읽지 않는다. 필수 값 누락은 명시적으로 거절하고 비밀값 기본값을 두지 않는다.
3. **Spring 앱 보존**: `spring-boot-app` fixture는 기존처럼 `@ConfigurationProperties`·`*Properties`만 통과한다. standalone 예외가 Spring 앱의 `Environment.getProperty`·`@Value` 또는 contexts의 Spring API 사용을 허용하지 않는다.

fixture 계약은 각 저장소 `architecture-test`의 `resources/structure`와 컴파일 fixture에 함께 둔다. 이 표준 저장소의 `tests/fixtures/standalone-app/gradle-contract`가 복사 가능한 기준 구현이다. fixture의 settings YAML은 실제로 파싱하고, allowlist·denied family·환경변수 source·file validation metadata를 구조적으로 대조한다. Gradle contract fixture는 실제 `runtimeClasspath.incoming.resolutionResult.allComponents`의 모든 `ModuleComponentIdentifier`와 `ProjectComponentIdentifier`를 immutable denied family·per-app allowlist와 대조하고, resolved artifact의 origin도 검사한다. file/flatDir/local JAR·unknown component·included build identity는 기본 거부한다. `runtimeOnly`·전이 의존·project transitive·version catalog·convention/plugin 주입을 각각 별도 fixture로 둔다. 테스트는 정상 fixture의 Kotlin `ExampleSettings`/`readValidatedFile`도 실제 컴파일하고, SecurityProbe가 정상 파일 읽기와 최종·중간 symlink·root 밖·크기 초과·group/world writable 거부를 실행한다. 전체 main Kotlin 소스의 알려진 직접 파일 I/O API를 secure reader 밖에서 fail-closed로 검사하며, 결과는 fixture 경로와 evidence 경로를 함께 출력하거나 보존해 문자열 존재만으로 통과시키지 않는다. `public-ca` file fixture는 실제 Deployment와 Pod manifest의 serviceAccount·fsGroup·readOnly·0444 선언을 YAML 파싱해 설정표와 대조한다.

- **정상 fixture**: `apps/standalone/build.gradle.kts`가 `standalone-app`만 적용하고 `mode`와 per-app project/runtime allowlist, 고정 main을 선언한다. 앱 루트의 `ExampleEnvironment`가 allowlist의 리터럴 환경변수만 읽어 `ExampleSettings`를 만들며, `readValidatedFile` 구현을 포함한 모든 정상 Kotlin 소스가 컴파일된다. `source: file` 항목은 `material: public-ca`와 serviceAccount·fsGroup·readOnly volume·0444 매핑, root·크기·권한·symlink 검증 metadata와 검증 reader를 갖는다. `apps/web`의 `spring-boot-app`·`ExampleProperties`는 기존 규칙을 통과한다.
- **위반 fixture**: Gradle contract의 `runtime-only`, `transitive-runtime`, `project-transitive`, `version-catalog`, `plugin-injection`을 각각 하나의 classpath 규칙으로 실패시킨다. standalone 모듈의 `spring-boot-app` 동시 적용, `apps` 밖의 `standalone-app`, Spring Boot/JPA/DB driver/Secrets Manager/AI provider SDK·다른 서비스 artifact 유입, allowlist 밖 project/runtime, main 밖의 `System.getenv`·직접 파일 읽기·`System.getenv()` 전체 맵·동적 이름, allowlist 밖 리터럴, file-backed 값의 root·크기·권한·symlink 검증 누락, `*Environment`가 raw map/비밀 기본값을 반환, contexts/usecase/integration에서 환경변수 또는 파일을 읽는 우회를 각각 exact error code로 실패시킨다.
- fixture 테스트는 정상·위반 양쪽을 **실행**하고, 각 위반 fixture의 `expected_error` 하나만 일치하는지, settings YAML 파싱·evidence 경로 확인을 보장한다. 실제 저장소가 standalone 앱을 갖지 않더라도 이 계약 fixture는 유지해 규칙이 사라지지 않게 한다.

## 6. 기존 저장소에 적용하기

구조 이행은 HTTP 계약·DB 스키마·사건 type 문자열·설정 키·환경변수를 바꾸지 않는다. 바뀌는 것은 Kotlin 패키지, 클래스·파일 이름, 모듈 의존, 포트·클래스 분할이다.

**옮기기 규칙**: 파일의 이름·패키지는 지금 그 파일이 있는 모듈의 슬라이스에서 한 번만 바꾼다. 다른 슬라이스는 그 파일의 import·참조만 고친다 — 같은 파일을 여러 번 옮기면 기준선과 문서 근거가 그때마다 낡는다.

| 순서 | 슬라이스 | 하는 일 | 파일 이름·패키지 변경 |
|---|---|---|---|
| R0 | 문서 선행 | 저장소 문서를 이 표준에 맞춘다. 설계 문서 본문의 클래스명을 책임 이름으로 바꾼다(X-4). DB-1 의 고정 목록을 만든다 | 없음 |
| R1 | 검사 장치 | 기준선 장치와 §4 의 "즉시"·"기준선" 검사를 넣는다 | 없음 |
| R2 | 안전망 | 금융 경로의 usecase 테스트, TX 경계 목록과 고정 테스트(T-5), 등록부 메서드 검사(T-4), 마커와 전이 검사(T-2), 잠금 거절 테스트(T-3) | 없음 |
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
5. 기준선: 새 항목이 없고 측정값이 늘지 않았다. 위반이 사라진 항목은 지웠다.

**DB 절차 로직 이관**은 구조 이행 뒤의 별도 프로젝트다. 새 절차 로직은 R1 의 DB-1 검사가 그동안에도 막는다. §4 에서 시점이 "DB 이관"인 검사는 이 프로젝트의 수용 조건이다. 순서는 위험이 낮은 것부터다.

1. 원장 점검을 앱 쿼리로 옮기고 매일 돌린다(DB-4) — 뒤 단계의 안전망이다.
2. 불변(수정·삭제 금지 가드) → 권한 회수.
3. 행 검사 → `CHECK` 제약 또는 도메인.
4. 잠금 → 앱의 정렬된 `SELECT … FOR UPDATE`. 집합 밖 주문의 뒤늦은 잠금 거절(T-3)을 앱 잠금 구현이 이어받는다.
5. 번호 발급 → 앱.
6. 운영 함수 → 앱의 운영 포트. 운영자 역할의 쓰기 경로를 없앤다(DB-3).
7. 상태 전이 가드 → 애그리거트 행위 메서드 + 조건부 UPDATE.
8. 여러 표에 걸친 합계 불변식 → 도메인이 금융 잠금 아래에서 쓰기 전에 검사.

단계마다 그 함수·트리거가 막던 사례를 앱 테스트로 먼저 옮긴다. 옮긴 테스트가 가드가 있는 DB 와 가드를 지운 DB 에서 모두 통과하는 것을 본 뒤에 `DROP` 마이그레이션을 낸다. 이미 적용된 마이그레이션은 고치지 않는다. 가드 오류의 번역(DB-5)은 그 가드를 지울 때 함께 지운다.

## 7. 참조 적용 — 주문 서비스·StoreFront

두 저장소가 이 표준의 첫 적용 대상이다. 아래는 표준 §3 의 기준으로 저장소별로 남기는 차이다.

| 항목 | 주문 서비스 | StoreFront |
|---|---|---|
| 배포 단위·TX 단계 | 단일 단위, 다중 루트 등록제만 | 4단위, 단위 교차 금지 + 등록제 |
| 스코프 모델 | 판매 범위(`ScopedTable`) | 테넌트(`TenantTable`) |
| 앱 | `apps/service` 하나 | 실행 앱 `web·admin·internal·worker` + 공용 앱 라이브러리 `apps/common` |
| 선택 모듈 | 없음 | `processes/checkout`, `query/admin` |
| 마이그레이션 | 루트 `db/migration`. `migrations` 플러그인을 새로 만든다 | `db/<unit>`·`db/rls/<unit>`. 기존 `verifyMigrations` 에 DB-1 을 더한다 |
| 설정 키 접두 | `order-platform.*` | `storefront.*` |
| 환경변수 접두 | `ORDER_`·`ORDERPLATFORM_`·`ORDER_MIGRATION_`(배포 계약이라 유지, C-5). 채널별 큐 맵은 동적 키다(C-4) | `STOREFRONT_` |
| 이벤트 type 접두 | `kr.aladin.orderplatform` | `kr.aladin.storefront` |
| 멱등 기록(`*Intake` 검사) | `command_log` | 지정 필요 |
| 런타임 주체(DB-3) | 앱 계정 하나 | 앱 계정 하나가 권한 그룹 둘을 상속한다 |

- **X-5 (운영)** StoreFront `docs/package-conventions.md`(역할별 배치)는 표준 §5 가 대신한다.
- 슬라이스 검증의 e2e 는 StoreFront `scripts/e2e/run-all.sh` 다. 이 스크립트는 주문 서비스도 띄우므로 주문 서비스 슬라이스도 통과시킨다.
- DB 절차 로직 이관에서 주문 서비스가 앱 테스트로 옮길 사례의 원본은 `tools/entity` 의 검증 사례다.
- 저장소별 이행 계획·건수와 결정 기록은 Obsidian vault 의 `wiki/projects/order-platform/` 에서 관리한다.
