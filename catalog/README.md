# 서비스 카탈로그

개발 2팀이 관리하는 서비스 인벤토리입니다.

팀이 직접 소유하거나 주도하는 서비스는 `catalog/{service_id}.yaml`에 둔다. 여러 팀/서비스가 함께 쓰는 공통 서비스는 팀 서비스 프로파일과 섞지 않고 [`catalog/common-services/registry.yaml`](common-services/registry.yaml)에 둔다. 공통 서비스 영향 확인 기준은 [공통 서비스 정책](../policies/common-service-policy.md)을 따른다.

## 서비스 목록

| 서비스 | 유형 | 스택 | DB | SP | 현대화 트랙 후보 | 하네스 상태 |
|--------|------|------|-----|-----|-----------------|-------------|
| [만권당 (max)](max.yaml) | legacy | .NET FW 4.8 / .NET 8 / Next.js 14 | MSSQL 5개 공유 | 580+ | Wrap/Extract | 미시작 |
| [투비컨티뉴드 (tobe)](tobe.yaml) | legacy | .NET FW 4.8 (ASP.NET MVC + React SSR) | MSSQL 5개 공유 | 200+ | Wrap | 미시작 |
| [알라딘 쇼핑 (shopping)](shopping.yaml) | legacy | .NET FW 4.8 ASP.NET (web) + VB6 (백오피스) | MSSQL (webcatalog/ebookcms) | TBD | Wrap | 미시작 |
| [블로그/북플 (blog)](blog.yaml) | legacy | .NET FW 4.8 ASP.NET Web Site | MSSQL (webcatalog 공유) | TBD | Wrap | 미시작 |
| [naru](naru.yaml) | new | Spring Boot 3.5.6 + Kotlin | PostgreSQL | 없음 | Observe | 미시작 |
| [bazaar](bazaar.yaml) | new | Spring Boot 3.5.3 + Kotlin | PostgreSQL + MSSQL(읽기) | 없음 | Observe | 미시작 |
| [aasm](aasm.yaml) | new | Next.js 16 + TypeScript | PostgreSQL (마이그레이션 중) | 없음 | Observe | 미시작 |
| [caravan](caravan.yaml) | new | Spring Boot 3.3.7 + Kotlin + Spring Cloud Gateway + Next.js 14 | PostgreSQL + Redis 7 | 없음 | Observe | 미시작 |
| [pod](pod.yaml) | new | Spring Boot 3.5.1 + Kotlin | PostgreSQL + S3/KMS | 없음 | Observe | 초기 등록 |
| [스토어프론트](storefront.yaml) | new | Spring Boot 4.1.0 + Kotlin 2.3.21 | PostgreSQL 17 로컬 스켈레톤, 앱 연결 미구현 | 없음 | Observe | 갱신 중 |

## 운영 모니터링

- IDC DB 이전 Datadog 서비스 매핑: [`datadog-idc-db-monitoring.yaml`](datadog-idc-db-monitoring.yaml)
- IDC DB 이전 Datadog 대시보드 구성: [`docs/datadog-idc-db-monitoring-dashboard.md`](../docs/datadog-idc-db-monitoring-dashboard.md)

## 아키텍처 비교

| 서비스 | 아키텍처 | ORM | 배포 | 호스팅 |
|--------|----------|-----|------|--------|
| max | N-Tier (Controller→Service→Repository→SP) | Dapper | MSBuild + IIS / Docker | IIS + Docker |
| tobe | Layered N-Tier (MVC→Bll→Dal→SP) | Dapper | CodeDeploy (Windows) | IIS (Windows Server) |
| shopping | ASP.NET WebForms + VB6 백오피스 (도메인 혼재) | ADO.NET / SP | MSBuild + IIS / Windows 클라이언트 배포 | IIS + Windows |
| blog | ASP.NET Web Site (App_Code 런타임 컴파일, .csproj 없음) | ADO.NET / SP | self-hosted runner `git pull` (MSBuild 없음) | IIS |
| naru | Hexagonal + DDD + CQRS | JPA/Hibernate | Docker multi-stage → AWS ECS | AWS ECS |
| bazaar | Hexagonal + DDD + CQRS | JPA/Hibernate | Docker → AWS ECR → ArgoCD (K8s) | K8s (ArgoCD) |
| caravan | Clean Architecture (domain/application/infra) + Reverse-Proxy Gateway | JPA/Hibernate (Admin) | Docker → Kubernetes | Kubernetes |
| pod | Spring Boot layered service (Controller→Service→Repository/JPA) | JPA/Hibernate | TODO | TODO |
| storefront | Gradle 멀티모듈 모놀리식 + DDD/Hexagonal/Clean 스켈레톤 | 미구현 | 미정 | 미정 |

## 공유 DB 현황

| DB | max | tobe | 비고 |
|----|-----|------|------|
| WebCatalog | O | O | 카탈로그/상품 |
| WebLog | O | O | 로깅 |
| Alibaba | O | O | 서드파티 연동 |
| WebMarket | - | O | 마켓/커머스 |
| Tobe | - | O (Primary) | tobe 메인 DB |
| EbookCms | O | - | max CMS |

> max와 tobe가 WebCatalog, WebLog, Alibaba를 공유 — 현대화 시 함께 고려 필요

## 공통 서비스

공통 서비스는 개발 2팀의 단독 소유가 아니지만 티켓 영향 범위에 반복적으로 등장하는 인증, 결제, 정산, 메시징, 공통 API 같은 경계다. 공통 서비스는 팀 서비스 목록에 넣지 않고 별도 registry에서 관리한다.

| 공통 서비스 | 영역 | 확인 기준 |
|---|---|---|
| 알라딘 인증 (`aladin-auth`) | 로그인, SSO, 세션, 권한, 회원 식별 | 로그인/권한/회원 식별 변경 시 공통 서비스 영향 확인 |
| [뉴빌링 (`new-billing`)](common-services/new-billing.yaml) | 결제, 청구, 환불, 정산, 구독, 빌링키 | 소스 확인됨, 개발 중, 현재 팀 서비스 active 연동 없음. 신규 빌링성 기능은 뉴빌링 API 우선 확인 |

자세한 기준: [`catalog/common-services/registry.yaml`](common-services/registry.yaml), [`policies/common-service-policy.md`](../policies/common-service-policy.md)

## 현대화 트랙 분포

| 트랙 | 서비스 | 설명 |
|------|--------|------|
| Observe | naru, bazaar, aasm, caravan, pod, storefront | modern stack 서비스. storefront는 실제 BC 구현 전 스켈레톤 단계 |
| Wrap | tobe, max(일부), shopping, blog | adapter/facade로 감싸기, SP 확산 방지 |
| Extract | max(일부), shopping(후보) | 신규 서비스로 도메인 추출 후보 (shopping은 B2B/C2C/중고매장 분리 식별 단계) |
| Freeze/Retire | - | 해당 없음 |

## 신규 서비스 등록

1. `_template.yaml`을 복사하여 `{서비스ID}.yaml` 생성
2. 필수 항목 작성
3. 이 README에 서비스 추가
4. 서비스 레포에 하네스 템플릿 적용 (`templates/service-harness/` 참조)

공통 서비스는 위 절차가 아니라 `catalog/common-services/registry.yaml`에 `status: candidate`로 먼저 등록하고, owner/API/repo/KB/runbook이 확인되면 증거 수준을 갱신한다.
