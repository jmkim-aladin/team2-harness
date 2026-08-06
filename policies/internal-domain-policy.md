# 내부통신 도메인 정책

> **상태: 확정** (2026-08-05, 개발3팀 합의). 도메인 문법과 내/외부 노출 방식은 신규 앱에 그대로 적용한다. §7은 앱 추가 시 확인할 운영 항목이다.

## 목적

서비스 애플리케이션의 도메인 이름, 내/외부 노출 경계, 애플리케이션 측 계약을 고정한다. 인프라팀이 앱을 추가할 때마다 협의하지 않고, 앱 개발자가 재배포 없이 노출 방식을 바꿀 수 있게 하는 것이 목적이다.

배경과 협의 이력은 vault [만권당 내부통신 도메인 및 base-path 결정](obsidian://open?vault=team2&file=wiki%2Fservices%2Fmax%2Fdecisions%2Finternal-alb-domain-and-base-path) 참조.

## 적용 범위

- 신규 백엔드 애플리케이션 전체 (max, tobe, shopping, blog, naru, bazaar, aasm, storefront, caravan, pod)
- 기존 앱은 Internal ALB 이관 시점에 적용. 이관 전에는 현행 유지 (인프라팀 2026-08-03 방침)
- **프론트엔드는 범위 밖.** 브라우저에 직접 노출되는 URL이므로 `{서비스}.aladin.co.kr` 형태로 별도 관리

## 1. 노출 방식과 도메인 문법

노출 성격에 따라 두 방식으로 나눈다. 앱은 두 경우 모두 **자기 경로만 안다** — 서비스 식별 경로를 앱이 갖지 않는 것이 공통 원칙이다.

| 노출 | 진입점 | 형태 | 서비스 식별 |
|---|---|---|---|
| 내부 inbound | Internal ALB | `{app}.internal.{service}[.{env}].aladin.co.kr` | 앱별 서브도메인 |
| 퍼블릭 inbound | API Gateway | `api.{service}[.{env}].aladin.co.kr/{app}` | 통합 도메인 + path 분기 (**G/W가 strip**) |

```
batch.internal.max.aladin.co.kr             내부 · prod
admin-api.internal.max.dev.aladin.co.kr     내부 · dev
api.max.aladin.co.kr/admin-api              외부 · prod
api.max.dev.aladin.co.kr/admin-api          외부 · dev
```

퍼블릭에서 path 분기를 쓰는 이유는 **API Gateway가 base path mapping으로 path를 strip해서 앱에 전달**하기 때문이다. 앱은 `/api/admin/v1/...`만 보므로 base-path 설정이 필요 없고, 도메인·인증서·Route 53 레코드가 앱 단위로 늘지 않는다. Internal ALB는 strip하지 않으므로 같은 방식을 쓸 수 없고, 그래서 내부만 앱별 서브도메인으로 간다.

path segment 이름은 **앱 축 이름과 같게** 쓴다. 내부 서브도메인의 app 라벨과 동일한 토큰이 되어 로그·추적·inventory에서 앱이 하나로 식별된다. `pubsvc01` 같은 순번 코드는 쓰지 않는다 — 의미가 없고 별도 매핑 표를 관리해야 한다.

### 내부 서브도메인 축

| 축 | 값 | 위치 |
|---|---|---|
| app | 배포 단위 이름 − 서비스 prefix | 최좌측 |
| internal | 내부 통신 전용일 때만 삽입 | app 우측 |
| service | 서비스 ID (`max`, `bazaar`, …) | internal 우측 |
| env | `dev` / `stg`. **prod은 생략** | service 우측 |

- **축 사이는 라벨(`.`), 축 내부 다중 단어만 하이픈(`-`).** `admin-api`, `batch-api`는 앱 이름 한 축이므로 하이픈이 맞다. `api-internal-batch`처럼 서로 다른 축을 하이픈으로 합성하지 않는다 — 위임 단위가 사라진다.
- app 축에서 서비스 prefix를 제거한다. `max-admin-api` → `admin-api`. 서비스 축이 이미 표현한다.
- `-api`는 앱 이름에 실제 있을 때만 붙인다. 업무 endpoint 없는 배치는 `batch`.
- prod bare는 사내 DNS 실측 관례다. `.prod.` 세그먼트는 사용하지 않는다.

**`internal` 라벨 유무 하나로 내/외부가 갈린다.** 로그·WAF Host·DNS inventory 분류가 suffix 하나로 끝난다.

같은 앱을 내부·외부 모두 노출해야 하면 두 진입점을 병행한다. 앱 입장에서는 두 경우 모두 같은 경로(`/api/admin/v1/...`)이므로 출처별 분기가 필요 없다.

### 금지

| 금지 | 이유 |
|---|---|
| **strip하지 않는 path 분기** (`{app}.internal.../batch`) | 앱이 base-path를 흡수해야 하고 인프라 라우팅 변경이 앱 재배포를 유발 |
| 내부 서브도메인 축을 하이픈으로 합성 (`api-internal-batch.max...`) | PHZ·인증서·IAM 위임 단위 소멸 |
| `internal`을 좌측에 두기 (`internal.batch.max...`) | wildcard 인증서를 앱마다 재발급 |
| 퍼블릭 앱마다 별도 도메인 발급 | 도메인·인증서·Route 53 레코드가 앱 단위로 증가 |

## 2. 인증서 · DNS

| 구분 | 인증서 | 앱 추가 시 증분 |
|---|---|---|
| 내부 | `*.internal.{service}.{env}.aladin.co.kr` | 인증서·zone 0, **DNS 레코드 1 + ALB host rule 1** |
| 외부 | API Gateway custom domain `api.{service}.{env}.aladin.co.kr` 기존 재사용 | **0** — G/W base path mapping만 추가 |

- ACM wildcard는 **가장 왼쪽 한 라벨만** 덮는다. apex도, 두 단계 아래도 덮지 않는다. 따라서 내부는 자체 wildcard가 필요하다.
- 인증서는 ALB와 **같은 계정·region**에 있어야 한다.
- 내부 이름은 Route 53 private hosted zone `internal.{service}.{env}.aladin.co.kr`에 둔다. 이 경계가 서비스별 AWS 계정 경계와 일치하는 것이 이 문법을 택한 이유다.
- PHZ suffix 내부의 미등록 이름은 퍼블릭으로 폴백하지 않고 **NXDOMAIN**이다. 형제 이름(`{service}.{env}.aladin.co.kr` 하위)은 정상적으로 퍼블릭 해석된다.
- 퍼블릭 ACM은 PHZ만으로 DNS 검증이 불가하다. 퍼블릭 zone에 검증 레코드가 필요하고, 인증서 이름은 CT 로그에 기록된다. **내부 이름의 비공개 범위는 앱 라벨까지다** — namespace 자체는 공개된다. Private CA는 도입하지 않는다.
- PHZ는 연결된 VPC에서만 보인다. 타 계정 VPC는 zone owner의 association authorization 후 VPC별 association이 필요하고, on-prem caller는 Route 53 Resolver inbound endpoint + forwarding이 필요하다. **전환 전 모든 caller의 VPC·계정·on-prem에서 DNS·route·SG를 전수 검증한다.**

## 3. 애플리케이션 계약

| ID | 규칙 |
|---|---|
| A1 | 앱은 base-path를 설정하지 않는다. **서비스 식별 경로 처리는 인프라 책임** — 내부는 경로 자체가 없고, 외부는 API Gateway가 strip한다 |
| A2 | actuator 경로 고정 — health `/actuator/health/*`, main port probe `/livez`·`/readyz`, metrics `/actuator/prometheus` |
| A3 | `management.endpoint.health.probes.enabled: true` 명시. Kubernetes 자동 감지에 의존하지 않는다 |
| A4 | `management.endpoint.health.probes.add-additional-paths: true` — main port에 `/livez`·`/readyz` 노출 |
| A5 | management port 분리는 기본값이 아니다. Service containerPort/targetPort, Ingress health port, SG/NetworkPolicy, 메트릭 endpoint를 함께 설계할 때만 도입 |
| A6 | **절대 URL을 반환하지 않는다.** `Location` 헤더, HATEOAS 링크, 페이지네이션 next, redirect target은 상대 경로로 쓴다 |
| A7 | **쿠키 기반 인증을 쓰지 않는다.** 토큰(Authorization 헤더)을 쓴다. 불가피하면 쿠키 `Path`를 앱 path segment로 고정한다 |
| A8 | OpenAPI/Swagger UI를 노출하는 앱은 A6·A9를 반드시 함께 적용한다 |
| A9 | A6~A8을 지킬 수 없으면 인프라팀에 `X-Forwarded-Prefix` 전달을 요청하고 `server.forward-headers-strategy: framework`를 설정한다. 앱이 prefix를 하드코딩하지 않는다 |

A6~A8이 필요한 이유는 **strip이 앱에게서 외부 경로 정보를 지운다**는 점이다. 앱은 자기가 `/{app}` 아래 있는 줄 모르므로:

- 절대 URL을 만들면 strip된 경로 기준이 되어 클라이언트가 404를 맞는다. API Gateway도 ALB도 `X-Forwarded-Prefix`를 자동으로 붙이지 않는다.
- 퍼블릭 통합 도메인에서는 여러 앱이 같은 host 아래 path로만 갈린다. `Path=/` 쿠키는 **앱 간 공유된다.** 도메인 분리 방식에서는 생기지 않는 문제다.
- Swagger UI가 만드는 server URL과 리소스 경로도 strip 기준이라 외부에서 깨진다.

MaxServer 현재 상태는 A6~A8을 모두 만족한다(2026-08-05 실측): base-path·`forward-headers` 설정 없음, `ServerResponse.created(uri)` 미사용(POST는 `status(201)` + body), 쿠키·세션 미사용(JWT Bearer / oauth2 resource server), springdoc 미도입. 따라서 **코드 변경 없이 API Gateway strip 방식에 안전하다.** 2026-07-30에 prod `api.max.aladin.co.kr/batch/actuator/health` 정상 응답으로 실증됐다.

A1 근거:

- `spring.webflux.base-path`는 호출 출처와 무관하게 앱의 모든 인바운드에 적용된다. 같은 Pod로 API Gateway와 Internal ALB 요청이 함께 들어오면 출처별로 분기할 수 없다.
- 별도 management context의 actuator base path는 `management.server.base-path` 기준이므로 base-path가 적용되지 않는다. management port를 분리한 앱과 안 한 앱의 경로 계약이 갈린다.
- 메트릭 스크레이프 URL이 base-path만큼 밀린다. MaxServer batch의 `.devops/{dev,prod}/batch/buildspec.yml:54`가 `:8080/actuator/prometheus` 하드코딩이라 base-path 도입 시 dev·prod 메트릭이 함께 끊긴다.

런타임별:

- Spring WebFlux — `spring.webflux.base-path`. 위 근거 그대로 적용.
- .NET Core — `UsePathBase`. 동일 문제.
- Next.js — `basePath`가 **빌드타임 고정**이라 환경변수로 분리 불가, 경로 변경 시 재빌드. FE를 이 정책 범위 밖에 두는 기술적 근거이기도 하다. (미검증 — 도입 전 확인)

A1 예외 조건 (둘 다 충족할 때만):

1. 도메인 추가 비용이 앱 설정 비용보다 크다
2. 해당 앱이 API Gateway와 Internal ALB 인바운드를 동시에 받지 않는다

## 4. Health check 계약

| 항목 | 값 |
|---|---|
| ALB health check port | **traffic port** (업무 포트). management port 아님 |
| ALB health check path | `/readyz` |
| ALB successCodes | **`200`** |
| k8s liveness probe | `/livez` |
| k8s readiness probe | `/readyz` |
| 보완 모니터 | 실제 private DNS hostname · TLS/SNI · ALB host rule을 통과하는 end-to-end synthetic. exact 200 + body `status: UP` |

근거:

- ALB target health는 traffic eligibility 판정이므로 의미상 readiness다. liveness를 재사용하지 않는다.
- **management port만 검사하면 main listener·connection pool 장애를 놓친다.** Spring 공식 문서가 경고하는 항목이다. ALB는 반드시 업무 포트를 본다.
- `successCodes: 200-499`는 404뿐 아니라 3xx·401·403도 통과시킨다. 경로만 좁히고 코드 범위를 안 좁히면 health check가 무력해진다.
- **가용성 우려는 ALB fail-open이 이미 해결한다.** target group의 모든 target이 unhealthy면 ALB는 unhealthy target에도 라우팅한다. 따라서 `200`으로 좁혀도 "전체 차단"은 발생하지 않는다.
- 실제 위험은 초기 등록이 한 번도 성공하지 못하는 배포다. deployment verification과 rollback으로 다룬다.
- health check port를 생략하면 기본값이 traffic port다. actuator를 별도 포트로 분리한 앱에서 이를 생략하면 **업무 포트의 404가 healthy로 처리된다.** A5가 management port 분리를 기본값으로 두지 않는 이유다.
- Pod IP 직접 스크레이프는 ALB·DNS·host rule 오설정을 검증하지 못한다. 보완 모니터는 최종 hostname을 경유해야 한다.

## 5. 경계 정의

정책 문서와 설계 문서에 "도메인을 분리했으므로 격리된다"고 쓰지 않는다. 실제 경계는 아래와 같다.

| 경계 | 무엇이 경계인가 | 경계 아닌 것 |
|---|---|---|
| 네트워크·권한 | SG (CIDR · prefix list · SG ID + port), NetworkPolicy, 방화벽 | DNS 이름, Host 헤더 — 클라이언트가 임의 생성 가능 |
| DNS 해석 | PHZ suffix + VPC association | 퍼블릭 zone 레코드 유무 |
| 인증서 lifecycle | 계정 · region · env별 ACM | wildcard 커버 범위 (이름은 CT 로그로 공개) |
| 실패 전파 | 진입점 인스턴스 — 내부는 ALB(listener·WAF·SG 공유), 외부는 API Gateway | 도메인 분리, path 분리, target group 분리 |
| 퍼블릭 접근 제어 | API Gateway — authorizer · throttle · WAF · usage plan | path segment |

- 여러 DNS alias가 같은 Internal ALB를 공유하고 exact Host rule로 target group을 가른다. ALB 대수·기본 비용은 늘지 않는다.
- default rule은 fixed deny response로 둔다. exact host rule을 쓰고, rule priority와 broad wildcard shadow 여부를 확인한다.
- `internal` 라벨은 로그·WAF Host·Network Firewall SNI 분류에 쓴다. 분류 편의이고 authorization이 아니다.
- 퍼블릭 통합 도메인은 앱 간 격리가 없다. **path segment는 접근 제어 단위가 아니므로** 앱별 인증·throttle을 G/W 레벨에서 명시한다.
- Quota 기본값: rules/ALB 100(조정 가능), **target groups/ALB 100(조정 불가)**, 추가 인증서/ALB 25(조정 가능).
- API Gateway 부수 제약: payload 10MB, 기본 integration timeout 29초, SSE·WebSocket 제약. 퍼블릭 앱이 대용량 업로드나 스트리밍을 요구하면 그때 노출 방식을 재검토한다.

## 6. 신규 앱 추가 시 변경 지점

앱 추가는 아래 전부를 한 번에 처리한다. 항목마다 canonical repo와 owner를 명시한다.

**내부 (Internal ALB)**

- [ ] PHZ 레코드 (+ 신규 zone이면 VPC association)
- [ ] 퍼블릭 ACM 검증 CNAME (신규 wildcard일 때)
- [ ] 인증서 ALB 부착
- [ ] ALB listener host rule + priority
- [ ] target group + health check path · port · matcher
- [ ] K8s Service / Ingress port · annotation (`target-type`이 `ip`면 Service port가 Pod targetPort로, `instance`면 NodePort로 해석)
- [ ] SG / NetworkPolicy / 방화벽 룰 (ALB↔target 새 포트 포함)
- [ ] caller 측 base URL
- [ ] end-to-end 모니터

**외부 (API Gateway)**

- [ ] base path mapping `{app}` 추가 (strip 확인)
- [ ] authorizer · throttle · usage plan
- [ ] VPC Link → target 경로
- [ ] 방화벽 룰 (src/dst 갱신)
- [ ] end-to-end 모니터 (최종 도메인 + path 경유)

**GitOps 밖에서 ALB를 직접 수정하면 controller reconciliation으로 되돌아간다.** 모든 변경은 GitOps에 반영한다.

## 7. 운영 확인 항목

문법·노출 방식은 확정됐다. 아래는 앱을 추가하거나 이관할 때 건별로 확인·협의하는 항목이다.

| 항목 | 확인하지 않으면 |
|---|---|
| 기존 ALB target group health check port 실측 | 업무 포트 404가 healthy로 처리되는 상태가 방치됨 |
| `successCodes` 200 확정 | health check가 무력한 채로 표준화됨 |
| PHZ cross-account association · on-prem Resolver 경로 | 전환 시점에 caller 해석이 깨짐 |
| 기존 앱 이관 기준 (신규만 적용 vs 일괄) | 내부·외부 혼재가 영구화되고 방화벽 룰 분류가 불가 |
| path segment 네이밍 (앱 이름 vs 순번 코드) | 로그·추적에서 내부 서브도메인과 앱 식별자가 어긋남 |
| 앱별 authorizer·throttle 기준 | 퍼블릭 통합 도메인에서 앱 간 격리가 없는 상태로 방치 |
| ALB URL rewrite transform 재검토 | 앱 무변경 대안(공용 도메인 + ALB path strip)이 사장됨. controller 버전·IaC 지원 확인 필요 |

## 관련

- [engineering-policy.md](./engineering-policy.md) — 신규 백엔드 스택 기준
- [aws-secrets-convention.md](./aws-secrets-convention.md) — Secrets Manager 명명
- [datadog-api-policy.md](./datadog-api-policy.md) — 모니터 구성 시 자격증명 기준
- [knowledge-base-policy.md](./knowledge-base-policy.md) — 협의 이력·결정은 vault, 표준은 이 문서
