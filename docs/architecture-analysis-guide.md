# DEV2 저장소 아키텍처 분석 기준

DEV2 서비스의 현재 구조와 설계 철학을 소스 근거로 복원하고, 이어갈 원칙과 위험을 같은 보고서에서 판단하는 공통 rubric이다.

## 목차

1. 핵심 원칙
2. 시스템 모델 복원
3. 아키텍처 적합성
4. 운영 가능성
5. 네이밍과 문서
6. 기술 스택별 보조 점검
7. 근거와 우선순위

## 1. 핵심 원칙

- 폴더 이름이 아니라 dependency와 runtime flow를 본다.
- 선언된 아키텍처와 실제 아키텍처를 분리한다.
- 엄격한 이론 준수 여부와 프로젝트가 택한 실용적 타협을 구분한다.
- 현재 구조가 해결하는 운영 문제를 이해한 뒤 개선을 제안한다.
- 대규모 순수화보다 실제 위험과 변경 압력을 우선한다.
- 장점과 문제를 함께 기록한다. 문제 목록만으로 프로젝트 철학을 설명하지 않는다.

## 2. 시스템 모델 복원

### 실행 경계

- 어떤 application, worker, scheduler, consumer가 실행되는가?
- 요청형, batch형, event형 workload가 같은 자원 budget을 공유하는가?
- application이 composition root인지 business rule도 소유하는지 구분한다.

### 의존성 경계

- source module dependency와 package import가 같은 방향인가?
- inner layer가 concrete DB/HTTP/framework 타입을 직접 참조하는가?
- transitive dependency가 실제 의존을 숨기는가?
- shared/common/base module이 업무 변경의 집중점이 되는가?

### 데이터와 상태

- system of record와 외부 원천은 어디인가?
- 주요 Aggregate 또는 transaction consistency 단위는 무엇인가?
- 상태 전이, 실패 이력, retry, dedupe, idempotency가 어디에 표현되는가?
- external call과 DB transaction 경계가 분리되는가?
- read/write model이 분리됐다면 목적과 consistency model이 명확한가?

### 외부 시스템

- 외부 DTO와 protocol이 Adapter 밖으로 새는가?
- 공급사·벤더·PG·인증 등 변동성이 Strategy/Port로 격리되는가?
- timeout, retry, circuit breaker, rate limit, error mapping이 실제 구현됐는가?

## 3. 아키텍처 적합성

### Clean Architecture

| 확인 | 잘 맞음 | 타협 또는 불일치 신호 |
|---|---|---|
| 의존 방향 | business rule이 interface를 소유 | inner layer가 adapter 구현을 참조 |
| framework 독립성 | framework type이 경계 밖에 머묾 | domain/application API에 Web/JPA concrete type 유입 |
| 테스트 가능성 | port 대역으로 usecase 검증 가능 | application test가 전체 container를 요구 |
| 모델 독립성 | domain 변경이 DB/API schema와 분리 | persistence model과 domain claim이 문서상 모순 |

JPA annotation이나 `@Transactional`이 있다는 사실만으로 실패로 판정하지 않는다. 교체 필요성, 테스트 비용, 문서상 주장과 실제 coupling을 함께 본다.

### Hexagonal Architecture

- inbound와 outbound Port의 소유자가 내부인가?
- Adapter 선택이 registry/composition에서 끝나는가?
- canonical model이 외부 provider schema를 차단하는가?
- application이 구체 Adapter를 조립하는 것은 허용하되, Adapter가 application contract를 소유하지 않는지 확인한다.
- Port가 단순히 Repository class 이름만 바꾼 것인지, 업무가 요구하는 capability를 표현하는지 본다.

### DDD

- Aggregate가 실제 invariant와 transaction 경계를 보호하는가?
- Entity setter 대신 의미 있는 상태 전이 메서드가 있는가?
- bounded context가 업무 언어와 변경 이유로 나뉘는가, 기술 폴더만 나뉘는가?
- 같은 현실 개념을 모든 context에서 한 Entity로 공유하지 않는가?
- Domain Service, Policy, Strategy가 구체적인 업무 의미 없이 패턴 이름으로만 존재하지 않는가?

### CQRS와 Event/Outbox

- Command/Query 분리가 필요한 조회·쓰기 압력에 대응하는가?
- Event/Outbox가 실제 비동기·재처리 요구를 해결하는가?
- 선점, 중복 발행, retry backoff, dead-letter, stuck recovery가 다중 노드에서도 안전한가?
- `at-least-once`를 `exactly-once`로 과장해 문서화하지 않는가?

## 4. 운영 가능성

### 보안

- 인증 검증을 Gateway에 위임하면 직접 접근 차단이 증명되는가?
- 사용자 scope가 list/detail/export 등 모든 조회 경로에 동일하게 적용되는가?
- secret 값이 log, buildspec, test fixture, exception에 노출되는가?
- 외부 입력 기반 SQL, URL, sort/property가 allowlist 또는 validation을 거치는가?

### 동시성과 신뢰성

- JVM 내부 lock/flag를 distributed guarantee로 오해하지 않는가?
- replica 수와 scheduler 중복 실행 가정이 배포 설정에 표현되는가?
- optimistic/pessimistic lock 또는 atomic claim이 필요한 상태에 존재하는가?
- 재처리가 동일한 side effect를 반복해도 안전한가?

### 배포와 migration

- CI가 실제 test를 실행하는가?
- drain/pause timeout 뒤 강제 배포가 데이터 흐름을 끊을 수 있는가?
- migration이 application 자동 실행인지 DBA/별도 pipeline인지 설정과 문서가 일치하는가?
- rollback보다 forward recovery를 택했다면 운영 절차가 있는가?

### 테스트

- clean checkout에서 compile/test 가능한가?
- ignored local file, real DB credential, developer machine path를 요구하지 않는가?
- domain/usecase/adapter별 위험에 비례해 test가 분포하는가?
- architecture dependency rule이 자동 검증되는가?

## 5. 네이밍과 문서

### 네이밍

- 오타와 단·복수, 약어 표기가 public API/package에 퍼지는가?
- `UseCase`, `Coordinator`, `Executor`, `Manager`, `Helper`, `Facade`, `Adapter`의 역할이 반복적으로 같은가?
- `temporary`, `legacy`, `new`, `common`처럼 수명을 설명하지 못하는 이름이 운영 코드에 남는가?
- 공급사·provider·제품명이 하나의 bounded context에서 혼용되는가?
- 메서드가 결과 타입이 아니라 업무 의도를 드러내는가?

### 문서 drift

- 버전, 모듈 수, API 인증, runtime, scheduler가 현재 코드와 일치하는가?
- 문서의 `CURRENT`, `DECIDED`, `PROPOSAL`, `DEPRECATED`가 구분되는가?
- migration이나 설계 문서만 있고 application code가 없는 기능을 구현 완료로 설명하지 않는가?

## 6. 기술 스택별 보조 점검

### Kotlin/Spring

- Gradle project dependency, component scan, configuration import 범위
- Spring Data ID generic과 Entity ID 타입 일치
- transaction manager와 read/write datasource 선택
- coroutine fan-out과 connection pool budget
- `TODO()`/`error()`가 활성 runtime path에 존재하는지

### .NET

- project reference 방향과 DI composition root
- Domain/Application의 EF Core·ASP.NET concrete type 의존
- hosted service와 web request workload 자원 공유
- transaction/outbox/background retry의 process boundary

### Node/Frontend

- feature/domain/shared boundary와 순환 import
- server/client boundary, auth token과 permission enforcement 위치
- API schema와 view model 결합
- build-time/runtime environment variable 노출

### Legacy

- DB/SP가 실질적인 domain/application layer인지
- shared database와 직접 table write owner
- strangler/adapter seam과 현대화 가능한 transaction boundary
- 문서상 계층보다 실제 호출·데이터 소유권을 우선

## 7. 근거와 우선순위

| 등급 | 기준 |
|---|---|
| P0 | credential 노출, 권한 우회, 데이터 손실·중복 결제, 즉시 배포 위험 |
| P1 | 활성 경로 runtime 실패, CI 재현 불가, 다중 노드 경쟁, 높은 장애 확률 |
| P2 | dependency 역전, 모듈 경계, 테스트·문서 drift처럼 변경 비용을 높이는 구조 부채 |
| P3 | 오타, 역할명 불일치, 오래된 통계 등 국소적 가독성·정리 문제 |

근거 수준:

- 높음: 실행 경로와 구체 코드 또는 재현 명령으로 확인
- 중간: 정적 구조로 확인했으나 runtime/config 가정이 남음
- 낮음: 문서·이름에서 추론했으며 담당자 또는 운영 환경 확인 필요

권장은 다음 순서로 정한다.

1. 보안·데이터·배포 안전성
2. 테스트와 clean checkout 재현성
3. transaction·동시성·멱등성
4. 컴파일 가능한 모듈·dependency 경계
5. 네이밍과 문서
6. persistence/domain 완전 분리 같은 고비용 순수화
