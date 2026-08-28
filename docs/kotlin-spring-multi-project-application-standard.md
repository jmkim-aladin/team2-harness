# Kotlin/Spring 멀티프로젝트 애플리케이션 표준

이 문서는 하나의 repository에 API, admin, batch 등 여러 Spring Boot 애플리케이션을 둘 때 적용하는 개발2팀 기본값이다. 특정 폴더 트리를 복사하는 템플릿이 아니라, 애플리케이션별 의존성과 운영 lifecycle을 분리하면서 Clean/Hexagonal Architecture의 이점을 유지하기 위한 결정 기준이다.

전사 Clean Architecture 원칙은 [REF-A-1958](https://aladincommunication.youtrack.cloud/articles/REF-A-1958)을 따르고, 이 문서는 Kotlin/Spring 멀티프로젝트에 필요한 구체적인 적용 기준을 보완한다.

## 적용 강도

| 표기 | 의미 |
|---|---|
| **MUST** | 보안, 데이터 소유권, 배포 격리, 의존 방향에 관한 필수 규칙. 이탈 시 ADR과 승인 필요 |
| **SHOULD** | 기본값. 다르게 선택하면 이유와 검증 방법을 티켓 또는 ADR에 기록 |
| **MAY** | workload와 팀 경험에 따라 애플리케이션이 선택 |

## 핵심 원칙

1. 같은 repository여도 애플리케이션은 독립된 artifact·config·secret·deploy·rollback 단위다. **(MUST)**
2. 애플리케이션은 실제 사용하는 capability와 외부 resource만 조립한다. **(MUST)**
3. domain/application은 framework와 외부 시스템을 모르고, adapter가 Spring·DB·보안·관측 기술을 소유한다. **(MUST)**
4. 데이터와 migration은 capability가 소유하고 write runtime은 하나만 둔다. **(MUST)**
5. 팀 표준은 선택 기준과 검증 계약을 공통화한다. 두 번째 실제 consumer가 생기기 전 generic platform을 먼저 만들지 않는다. **(SHOULD)**

## 최소 모듈 구조

```text
apps/
  api/                         # 독립 bootJar/image/config/deploy
  admin-api/
  batch/

capabilities/<capability>/
  domain/                      # 순수 Kotlin model/rule
  application/                 # use case, inbound/outbound port
  adapters/
    inbound-<runtime>/         # MVC, WebFlux, scheduler 등
    outbound-<technology>/     # JPA, JDBC, client, messaging 등

build-logic/                   # 실제 두 app 이상이 공유하는 build convention만
```

이 트리는 예시다. 고정해야 하는 것은 폴더 개수가 아니라 다음 의존 방향이다.

```text
app composition → adapter → application → domain
```

- domain/application에 Spring, JPA `@Entity`, Spring Data, QueryDSL, JDBC, Reactor, Datadog 타입을 노출하지 않는다. **(MUST)**
- app은 필요한 adapter를 선택해 조립하며, 사용하지 않는 DB driver·client·secret·health check를 가져오지 않는다. **(MUST)**
- 공용 모듈은 “여러 곳에서 쓸 것 같다”가 아니라 두 번째 실제 사용과 동일한 변경 이유가 확인된 뒤 추출한다. **(SHOULD)**
- application 간 JPA entity/repository 공유는 금지한다. 다른 app은 owner의 공개 use case/API 또는 명시적인 read-only adapter로 접근한다. **(MUST)**

## 애플리케이션별 선택 항목

아래 값은 repository 전체가 아니라 각 application이 결정한다.

| 항목 | 결정 질문 | 기록 위치 |
|---|---|---|
| web runtime | 요청이 blocking JDBC 중심인가, end-to-end reactive인가? | app ADR 또는 티켓 |
| DB resource | 실제 call graph가 사용하는 DB·schema는 무엇인가? | config 계약·service catalog |
| persistence | JPA, JDBC, Exposed 중 query·write 특성에 맞는가? | capability adapter |
| migration | 누가 어느 환경에서 DDL을 실행하는가? | migration/release 계약 |
| secret | app이 필요한 key만 주입되는가? | config 계약 |
| pool | Pod 수와 DB connection budget 안에 드는가? | 배포 계약 |
| security | identity를 누가 검증하고 어떤 policy로 인가하는가? | security ADR·test |
| observability | 기존 Agent/collector와 어떤 신호 경로를 쓰는가? | telemetry 계약 |

`cool`, `lego` 같은 이름은 resource namespace일 뿐 module 경계가 아니다. `cool` 안에 여러 DB가 있다면 `mssql.cool`처럼 묶지 말고 `mssql.cool.webcatalog`처럼 실제 resource 단위로 선택한다.

## MVC, WebFlux, coroutine, virtual thread

| workload | 권장 runtime | blocking 처리 |
|---|---|---|
| JDBC/JPA 중심 API·admin | Spring MVC | adapter-owned virtual thread 또는 검증된 bounded executor |
| end-to-end non-blocking I/O·streaming | Spring WebFlux | reactive driver/client 유지 |
| 혼합 | 주 경로를 기준으로 선택 | blocking 경계를 adapter에 격리하고 pool budget 검증 |

- coroutine controller는 MVC와 WebFlux 모두에서 사용할 수 있다. 다만 `suspend`가 JDBC/JPA를 non-blocking으로 바꾸지는 않는다.
- blocking 기술 때문에 WebFlux를 선택하거나, coroutine을 쓴다는 이유로 R2DBC를 도입하지 않는다. **(SHOULD)**
- MVC+JDBC에서 virtual thread는 blocking outbound adapter가 소유한다. domain/application에 dispatcher·executor를 노출하지 않는다. **(MUST)**
- Spring의 global virtual-thread switch는 모든 scheduler/executor 동작을 함께 바꾸므로 application 단위 근거와 회귀 검증 없이 켜지 않는다. **(SHOULD)**
- coroutine fan-out은 DB connection pool을 늘려주지 않는다. 동시성 제한과 `Pod 수 × pool max`를 함께 계산한다. **(MUST)**

### JPA transaction과 coroutine

JPA transaction은 thread-bound이므로 transaction 중 suspension과 thread 전환을 허용하지 않는다. **(MUST)**

```kotlin
interface TransactionPort {
    suspend fun <T> execute(block: () -> T): T
}
```

- 구현 adapter가 virtual thread에서 `TransactionTemplate`로 block 전체를 실행한다.
- block과 그 안에서 호출하는 persistence port는 동기식이다.
- controller/use case 경계의 `suspend`와 JPA transaction 내부 실행 모델을 구분한다.

## persistence 기본값

- 팀 경험과 Spring 생태계 호환성을 고려해 aggregate write와 일반 CRUD는 JPA를 기본값으로 둔다. **(SHOULD)**
- domain model과 JPA entity는 분리하고 outbound adapter mapper로 변환한다. **(MUST)**
- QueryDSL은 조건 조합, join, projection 등 실제 복잡한 동적 조회가 있을 때 query adapter에만 적용한다. **(MAY)**
- Exposed는 Kotlin DSL, SQL 제어, JDBC 중심 모델이 명확한 capability에서 선택할 수 있지만 팀 공통 기본값은 아니다. QueryDSL 전체를 대체한다고 가정하지 않는다.
- raw JDBC나 stored procedure는 legacy adapter 경계에서만 사용하고 새 domain model로 변환한다. 신규 core로 legacy DB 모델을 전파하지 않는다. **(MUST)**

## 데이터 소유권과 legacy 전환

- capability/table마다 migration owner와 단일 write runtime을 명시한다. **(MUST)**
- 레거시와 신규 DB를 동시에 쓰는 초기 단계에서도 dual-write를 기본값으로 두지 않는다. 필요하면 정합성·재시도·복구 설계를 별도 승인한다.
- MSSQL→PostgreSQL 전환은 adapter 교체 문제만이 아니다. read/write owner, reconciliation, cutover, rollback 증적을 갖춰야 한다.
- shared JPA entity/repository로 미래 애플리케이션을 미리 연결하지 않는다. 공개 계약 또는 read-only adapter로 협력한다.

## config, secret, DB health

- `local`, `test`, `dev`, `prod` profile을 명시하고 credential 또는 URL fallback으로 `localhost`에 조용히 연결하지 않는다. **(MUST)**
- application은 필요한 DB capability를 명시적으로 선택한다. 선택한 required resource에는 datasource·secret binding·schema validator만 구성하고, 사용하지 않는 resource에는 datasource·secret·migration initializer·health indicator를 만들지 않는다. **(MUST)**
- 선택한 required datasource의 config·초기 connection·schema validation 중 하나라도 실패하면 원인을 포함해 기동에 실패한다. 기동 후 연결 장애는 liveness가 아니라 readiness에 반영한다. **(MUST)**
- secret은 application별 최소 key만 주입하고 코드, image, log에 값을 남기지 않는다. **(MUST)**
- required DB 또는 schema가 준비되지 않으면 readiness는 DOWN, liveness는 유지한다. **(SHOULD)**
- datasource마다 pool을 독립 구성한다. pool은 고정 표준값이 아니며 `datasource별 maxPool × (steady replica + rollout maxSurge)`를 해당 서비스의 최대 점유량으로 계산한다. 같은 DB를 쓰는 batch·다른 서비스의 점유량과 운영 여유분까지 DB connection limit 안에 들어야 한다. **(MUST)**
- 최종 pool 값은 DBA의 connection limit와 배포 담당자의 replica·rollout 설정을 증적으로 확인한 뒤 배포 계약에 고정한다. `minimumIdle=0`은 저트래픽 신규 app의 시작점으로 검토할 수 있다.
- PostgreSQL major version은 application/database별로 고정한다. 같은 repository의 다른 app이 같은 major로 올라가야 할 이유는 없다.

### EKS inbound와 management endpoint

기본 EKS topology는 [내부통신 도메인 정책](../policies/internal-domain-policy.md)을 따른다.

```text
내부  caller → Internal ALB → Ingress/Service → Pod
외부  caller → API Gateway(path strip) → VPC Link → Internal ALB → Ingress/Service → Pod
운영  kubelet/ALB health/Datadog Agent → Pod target의 probe·metric endpoint
```

- 신규 app은 업무 포트 하나를 기본으로 사용한다. 별도 management port는 Service·Ingress·health port·SG·NetworkPolicy·scrape 경로를 함께 설계한 예외에서만 사용한다. **(SHOULD)**
- business Ingress와 API Gateway는 `/actuator/**`, `/livez`, `/readyz`를 사용자 route로 노출하지 않는다. **(MUST)**
- ALB target health는 업무 포트 `/readyz`와 exact `200`, Kubernetes는 `/livez`·`/readyz`, Datadog Agent는 Pod의 `/actuator/prometheus`를 직접 사용한다. **(MUST)**
- actuator 노출은 `health,prometheus`로 제한하고 health detail은 숨긴다. **(MUST)**
- app에는 service 식별 base-path를 두지 않는다. 외부 `{app}` segment는 API Gateway가 strip한다.
- 실제 GitOps의 Ingress path, target type, Service port, health matcher와 API Gateway mapping은 app별 배포 handoff에서 확인한다. 문서상 예상 경로만으로 완료 처리하지 않는다. **(MUST)**

## schema migration과 배포

하나의 versioned SQL source와 checksum을 환경별 다른 실행 주체가 사용한다. **(MUST)**

| 환경 | 실행 방식 | runtime 계정 |
|---|---|---|
| local/test | app 또는 test harness 자동 migration | local owner |
| dev | rollout 전 별도 migration job 자동 실행 | DDL identity와 DML runtime 분리 |
| prod | DBA가 배포 전에 동일 bundle 수동 실행·증적 전달 | application은 DML-only |

- production application startup에서 DDL을 실행하지 않는다. schema validation만 한다. **(MUST)**
- dev migration 성공 전 rollout을 시작하지 않고, prod는 DBA의 version·checksum·실행 결과 확인 전 rollout하지 않는다. **(MUST)**
- rollback은 previous image가 선반영 schema와 호환될 때만 허용한다. destructive change는 expand/contract와 별도 정리 단계로 나눈다. **(MUST)**
- migration 실패, app rollout 실패, rollback 각각의 owner와 중단 조건을 배포 계약에 기록한다.

## 인증과 인가

- 인증 공급자의 token/header 타입은 inbound security adapter에서 domain-neutral identity로 변환한다. **(MUST)**

```kotlin
data class AdminIdentity(
    val provider: String,
    val subject: String,
)
```

- Gateway가 인증을 담당하면 외부에서 들어온 identity header 제거, 검증된 값 재주입, Gateway 우회 차단이 신뢰 경계의 전제다.
- admin frontend가 OAuth 2.0/OIDC를 처리하면 BFF가 token 교환·refresh·revoke와 `httpOnly` cookie를 소유하고, browser storage에 token을 두지 않는다. BFF/proxy가 backend 호출에 access token을 `Authorization: Bearer`로 전달한다. **(MUST)**
- backend는 전달받은 JWT의 signature, expiry/not-before, issuer, audience와 token 용도를 독립적으로 검증한 뒤 claim을 사용한다. payload decode만으로 인증하지 않는다. **(MUST)**
- 임의 header나 local identity fallback을 운영 경로에 두지 않는다. **(MUST)**
- 인증과 인가는 별개다. 승인된 policy가 연결되기 전 privileged endpoint는 fail-closed한다. **(MUST)**
- Spring Security 타입은 inbound adapter 밖으로 노출하지 않고 identity와 authorization result만 use case에 전달한다.
- security 구현은 401/403, header 위조, 비활성 계정, 권한 누락, 정책 미연결을 통합 테스트하고 팀의 일반 코드리뷰 절차를 따른다. **(MUST)**

### claim과 인가 계정 연결

- 인증 주체의 기술 식별자는 검증된 `(issuer, subject)` 조합이다. raw JWT, email, 표시 이름을 식별 키로 쓰지 않는다. **(MUST)**
- 사번 같은 고정 업무 claim은 SSO 계약이 불변성·유일성·퇴사 후 재사용 정책을 보장하는지 확인한 뒤 계정 연결과 운영 조회에 사용할 수 있다.
- role/permission은 사번이나 claim 문자열에 직접 매달기보다 서비스 내부 `admin_id`에 연결하는 방식을 우선 검토한다. `(issuer, subject)`와 승인된 사번 claim을 내부 ID로 매핑할지는 실제 권한 lifecycle 설계에서 결정한다. **(SHOULD)**
- 사번 pseudonymization이 필요하면 단순 hash가 아니라 서버 비밀키 기반 HMAC과 key version을 사용한다. 검색·운영 표시가 필요하면 접근 통제된 원문 또는 별도 암호화 컬럼 여부를 보안 요구에 따라 결정한다.
- 퇴사·휴직·사번 변경/재사용·SSO subject 변경 시 계정 비활성화와 재연결 절차를 인가 정책에 포함한다. **(MUST)**

## 관측성 표준

### 신호 경로

기존 Kubernetes Datadog Agent가 준비된 서비스의 기본값은 다음이다.

```text
metric  Micrometer → /actuator/prometheus → Datadog Agent OpenMetrics
trace   OpenTelemetry API → Datadog Java Agent provider → Datadog APM
log     stdout JSON → Datadog Agent log collection
```

- 애플리케이션에 Datadog API key를 넣지 않는다. **(MUST)**
- trace instrumentation은 OTel API를 사용하고 runtime이 `DD_TRACE_OTEL_ENABLED=true`인 Datadog Java Agent를 주입한다. **(SHOULD)**
- Datadog Java Agent를 provider로 쓸 때 OTel SDK·OTLP exporter·OTel Java Agent를 함께 구성하지 않는다. **(MUST)**
- domain/application은 OTel·Datadog API를 모르며 custom span은 inbound/outbound adapter에만 둔다. **(MUST)**
- 기존 observability module이 WebFlux `WebFilter`나 Reactor Hook에 묶여 있으면 MVC app에 그대로 재사용하지 않는다. 두 runtime의 공통 추출은 두 번째 실제 consumer와 동일한 요구가 확인된 뒤 한다.
- Agent/collector가 없는 local에서도 app이 기동해야 하며 telemetry 전송 실패로 readiness를 내리지 않는다. **(MUST)**

기존 Agent가 없거나 OTLP 수신이 준비된 환경은 같은 애플리케이션 계측 계약을 유지하되 exporter/provider만 별도 결정한다. Datadog Java Agent와 OTel SDK를 동시에 활성화하는 구성은 허용하지 않는다.

### tag와 log correlation

- 필수 tag: `service`, `env`, `version`.
- `service`는 배포 단위별 lowercase 이름을 사용한다. 예: `max-admin-api`.
- stdout JSON에는 `service`, `env`, `version`, `trace_id`, `span_id`를 포함해 trace와 log를 연결한다.
- `X-Trace-Id` 응답 header는 기존 client/support 계약이 확인된 경우에만 추가한다. 표준 trace context를 source of truth로 유지한다.
- `/actuator/health/**`, `/actuator/prometheus`, `/livez`, `/readyz` 같은 probe·scrape endpoint는 APM trace 수집에서 제외한다. **(SHOULD)**
- trace 제외는 endpoint 비활성화가 아니다. Prometheus scrape, readiness/liveness 판정, 실패 probe log와 Kubernetes event는 유지한다. **(MUST)**
- 제외 방식은 고정한 Agent version에서 검증된 server-path exclusion 또는 sampling 설정을 사용하고 dev smoke로 확인한다.

### 수집 금지와 allowlist

- raw request/response body를 span이나 일반 application log에 저장하지 않는다. **(MUST)**
- query string은 수집하지 않는다. Java tracer는 `DD_HTTP_SERVER_TAG_QUERY_STRING=false`, Agent는 가능한 경우 `DD_APM_OBFUSCATION_HTTP_REMOVE_QUERY_STRING=true`를 방어적으로 적용한다. **(MUST)**
- Authorization, cookie, internal SSO identity header, secret, SQL parameter, 개인정보를 tag로 수집하지 않는다. **(MUST)**
- 사용자·주문·콘텐츠 ID 같은 고카디널리티 값을 일반 span tag로 넣지 않는다.
- 운영 진단은 아래 저카디널리티 allowlist를 기본값으로 한다.

| 신호 | 허용 예시 |
|---|---|
| span attribute | `admin.action`, `target.type`, `result`, `error.code`, `validation.field`, `payload.size`, DB resource name, record count |
| audit log | actor reference, action, target reference, result, trace ID |

audit actor/target reference는 접근 통제된 audit sink에 필요한 최소 식별자만 남기고 raw payload와 credential은 남기지 않는다. AppSec의 request-body inspection은 WAF 탐지 기능이며 운영자가 raw body를 조회하기 위한 APM logging으로 사용하지 않는다.

### Agent 호환성 gate

Datadog Java Agent의 Spring Boot 4/Spring Framework 7 지원은 2026-08-27 현재 [공식 tracker](https://github.com/DataDog/dd-trace-java/issues/11597)에서 계속 검증 중이다. 따라서 다음을 적용한다.

- Agent version을 image/deploy 계약에 고정한다. **(MUST)**
- dev에서 MVC, Spring Security, JDBC, coroutine, adapter-owned virtual thread의 trace 연속성과 중복 span 여부를 smoke한다. **(MUST)**
- APM 비호환은 배포 증적에 기록하고 Agent 적용을 중단할 수 있어야 한다. core app의 readiness와 metric/log 경로는 유지한다.
- 지원 여부를 추측하지 않고 upgrade마다 같은 smoke를 반복한다.

참고:

- [Datadog SDK의 OpenTelemetry API 지원](https://docs.datadoghq.com/opentelemetry/instrument/dd_sdks/api_support/)
- [Datadog APM 데이터 보안](https://docs.datadoghq.com/tracing/configure_data_security/)
- [Datadog Java tracer 설정](https://docs.datadoghq.com/tracing/trace_collection/library_config/java/)

## architecture·integration 검증

각 application은 최소 다음을 자동 검증한다.

- 허용된 Gradle project dependency 방향
- domain/application의 Spring·JPA·QueryDSL·Reactor·Datadog 의존 금지
- exact DB만 생성되고 config/secret fallback이 없음
- business Ingress/API Gateway에서 management path 차단, Pod 직접 probe·scrape 유지
- JPA transaction 중 suspension/thread 전환 없음
- migration clean/validate와 runtime DDL 금지
- required DB/schema 장애 시 readiness DOWN·liveness UP
- 인증 위조·인가 미연결 fail-closed
- Agent 없는 local 기동, provider 중복 없음
- raw body·query string·민감 header 미수집
- health·Prometheus endpoint는 APM trace에 없지만 metric 수집과 probe 실패 진단은 유지
- 배포 후 metric·trace·log의 `service/env/version`와 trace context 연속성
- 같은 repository의 기존 application artifact·config·deployment revision 무변경

## 배포 책임 계약

| 애플리케이션 팀 | 플랫폼·인프라 팀 | DBA |
|---|---|---|
| code, test, config schema, migration bundle | build/deploy runtime, secret/network resource | production DDL 실행 |
| meter, structured log, OTel API, tag/redaction 계약 | Agent 주입, version 고정, APM/OpenMetrics/log 수집 | version/checksum/실행 증적 |
| 호출 주체·노출 범위, route·probe·scrape 계약과 acceptance | GitOps Application·Helm·Ingress·Service, API Gateway/VPC Link와 management path 차단 | - |
| application acceptance와 rollback 판단 | rollout/rollback mechanism | DB 권한 검토 |

조직별 담당 팀 이름은 달라질 수 있지만 code/runtime/DDL 책임 경계는 배포 전에 명시한다.

애플리케이션 팀은 인프라 manifest를 대신 작성하지 않는다. 대신 인프라팀이 구현할 수 있도록 포트, business path, 내부/외부 노출 여부, health matcher, probe, scrape, 금지 path와 검증 방법을 versioned 배포 계약으로 전달한다. 운영 완료는 실제 GitOps revision과 endpoint smoke 증적을 application artifact에 연결했을 때다.

## 만들지 않는 기본값

- DB-less production mode로 required DB 오류 숨기기
- repository 전체에 모든 DB·secret·migration 의존 강제
- 미래 app을 위한 shared JPA entity/repository
- 실제 consumer 없는 generic DB/capability registry
- MVC/WebFlux를 한 구현으로 감추는 선행 observability framework
- Datadog Java Agent와 OTel SDK/Agent의 중복 provider
- raw payload 수집을 통한 디버깅
- 정상 health·Prometheus scrape span을 상시 수집해 APM signal과 비용을 희석하는 구성
- 근거 없는 XA·dual-write·범용 migration engine

## 프로젝트 시작 체크리스트

1. app별 artifact/config/deploy/rollback 경계를 적는다.
2. 첫 vertical slice의 call graph로 exact DB와 legacy dependency를 찾는다.
3. capability owner, write runtime, migration owner를 정한다.
4. MVC/WebFlux와 persistence 기술을 workload 근거로 선택한다.
5. local/test/dev/prod의 migration 실행 주체와 계정을 적는다.
6. security trust boundary와 미연결 시 fail-closed endpoint를 적는다.
7. 기존 Agent/collector를 확인해 metric·trace·log 경로와 privacy 설정을 정한다.
8. 기존 운영 app의 test·artifact·config·deployment 기준선을 잡는다.
9. 첫 vertical slice와 dev smoke가 통과한 규칙만 팀 표준 후보로 승격한다.

## MaxServer 참조 적용

MaxServer `admin-api`는 이 기준의 첫 대형 reference다.

| 항목 | 적용 결정 |
|---|---|
| 기존 app 보호 | 운영 중인 `max-batch` artifact·config·rollout 무변경 |
| runtime | Spring MVC annotated coroutine controller + adapter-owned virtual thread |
| persistence | MSSQL Spring JDBC legacy adapter + PostgreSQL 18 JPA adapter, 복잡 조회만 QueryDSL |
| schema | local/test 자동, dev migration job 자동, prod DBA 수동 DDL |
| security | admin front BFF가 SSO token을 Bearer로 전달하고 backend가 JWT를 검증; 고정 claim 기반 authorization의 claim·내부 ID·HMAC 방식은 주니어 구현 전 설계 리뷰 TODO, 미연결 privileged endpoint fail-closed |
| observability | 기존 Agent OpenMetrics/APM/log 경로, OTel API, raw body/query string 미수집 |
| EKS route | `admin-api.internal.max[.{env}].aladin.co.kr` 전용 Internal ALB route와 단일 업무 포트; public API Gateway mapping 없음 |
| 애플리케이션 경계 | `maxcms-front`·`maxcms-api`와 artifact·route·auth·deploy lifecycle을 공유하지 않는 독립 admin application |

상세 결정과 실행 티켓은 Obsidian vault의 `wiki/projects/legacy-modernization-multi-project-standard/`에서 관리한다.
