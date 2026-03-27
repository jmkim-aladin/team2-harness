# 서비스 카탈로그

개발 2팀이 관리하는 서비스 인벤토리입니다.

## 서비스 목록

| 서비스 | 유형 | 스택 | DB | SP | 현대화 트랙 후보 | 하네스 상태 |
|--------|------|------|-----|-----|-----------------|-------------|
| [만권당 (max)](max.yaml) | legacy | .NET FW 4.8 / .NET 8 / Next.js 14 | MSSQL 5개 공유 | 580+ | Wrap/Extract | 미시작 |
| [투비컨티뉴드 (tobe)](tobe.yaml) | legacy | .NET FW 4.8 (ASP.NET MVC + React SSR) | MSSQL 5개 공유 | 200+ | Wrap | 미시작 |
| [naru](naru.yaml) | new | Spring Boot 3.5.6 + Kotlin | PostgreSQL | 없음 | Observe | 미시작 |
| [bazaar](bazaar.yaml) | new | Spring Boot 3.5.3 + Kotlin | PostgreSQL + MSSQL(읽기) | 없음 | Observe | 미시작 |
| [aasm](aasm.yaml) | new | Next.js 16 + TypeScript | PostgreSQL (마이그레이션 중) | 없음 | Observe | 미시작 |

## 아키텍처 비교

| 서비스 | 아키텍처 | ORM | 배포 | 호스팅 |
|--------|----------|-----|------|--------|
| max | N-Tier (Controller→Service→Repository→SP) | Dapper | MSBuild + IIS / Docker | IIS + Docker |
| tobe | Layered N-Tier (MVC→Bll→Dal→SP) | Dapper | CodeDeploy (Windows) | IIS (Windows Server) |
| naru | Hexagonal + DDD + CQRS | JPA/Hibernate | Docker multi-stage → AWS ECS | AWS ECS |
| bazaar | Hexagonal + DDD + CQRS | JPA/Hibernate | Docker → AWS ECR → ArgoCD (K8s) | K8s (ArgoCD) |

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

## 현대화 트랙 분포

| 트랙 | 서비스 | 설명 |
|------|--------|------|
| Observe | naru, bazaar, aasm | 이미 modern stack, 하네스 문서화만 |
| Wrap | tobe, max(일부) | adapter/facade로 감싸기, SP 확산 방지 |
| Extract | max(일부) | 신규 서비스로 도메인 추출 후보 |
| Freeze/Retire | - | 해당 없음 |

## 신규 서비스 등록

1. `_template.yaml`을 복사하여 `{서비스ID}.yaml` 생성
2. 필수 항목 작성
3. 이 README에 서비스 추가
4. 서비스 레포에 하네스 템플릿 적용 (`templates/service-harness/` 참조)
