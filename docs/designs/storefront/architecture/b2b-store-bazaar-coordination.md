# SF ↔ 바자르 연동 설계 — 실 코드 분석 기반

> **작성일**: 2026-04-22
> **작성**: 김정민
> **분석 대상**: `/Users/user/Documents/workspace/bazaar/BazaarServer` (31,594 LOC Kotlin Spring Boot 3.5.3)
> **기반 문서**: `BazaarServer/docs/architecture/ARCHITECTURE.md` (2025-10-27, 김규태 작성)
> **목적**: 스토어프론트(SF)가 바자르를 공급측 오케스트레이터로 활용하기 위한 연동 설계·책임 경계·API 계약
> **중요 전제 (4/22 확정)**:
> 1. **모든 상품 = 알라딘 상품**. 오픈마켓 상품이 SF에 흘러들어올 일 없음
> 2. **모든 주문 = 알라딘으로 이행됨**. SF는 오픈마켓과 무관
> 3. SF 관점 바자르 = **알라딘 supplier 경로 + B2B용 신규 vendor 추가** 구조

---

## 목차

1. [바자르 실체 요약](#1-바자르-실체-요약)
2. [바자르 핵심 개념 (실 코드 용어)](#2-바자르-핵심-개념-실-코드-용어)
3. [핵심 발견 — VendorType.IN_HOUSE_COMMERCE 예약](#3-핵심-발견--vendortypein_house_commerce-예약)
4. [SF ↔ 바자르 3가지 연동 모델](#4-sf--바자르-3가지-연동-모델)
5. [권장 모델 — 새 Vendor.B2B_STOREFRONT 등록](#5-권장-모델--새-vendorb2b_storefront-등록)
6. [책임 경계 매트릭스 (실 도메인 기반)](#6-책임-경계-매트릭스-실-도메인-기반)
7. [API 계약 설계 (Port 단위)](#7-api-계약-설계-port-단위)
8. [주문·이행·클레임 플로우](#8-주문이행클레임-플로우)
9. [이벤트 구독 스키마 (Outbox)](#9-이벤트-구독-스키마-outbox)
10. [바자르 측 필요 변경 사항](#10-바자르-측-필요-변경-사항)
11. [MVP 단계별 로드맵](#11-mvp-단계별-로드맵)
12. [김규태 팀장과의 협의 체크리스트](#12-김규태-팀장과의-협의-체크리스트)
13. [미결 질문 (세부 조사 필요)](#13-미결-질문-세부-조사-필요)
14. [참조 파일 경로](#14-참조-파일-경로)

---

## 1. 바자르 실체 요약

**이전 대화에서 "바자르 = 컨셉 단계" 이해는 부정확**. 재정의:

| 항목 | 실체 |
|------|------|
| 상태 | **실제 운영 중인 Kotlin Spring Boot 3.5.3 시스템** (2025-10-27 기준 최신 반영) |
| 규모 | **31,594 LOC Kotlin** (538 파일) + 테스트·SQL 포함 35,101 LOC |
| 아키텍처 | **Hexagonal (Ports & Adapters) + DDD + CQRS** — ARCHITECTURE.md §2 |
| DB | PostgreSQL (primary) + MSSQL (알라딘 공급자, 읽기 전용) |
| 비동기 | Kotlin Coroutines 1.9.0 |
| 이벤트 발행 | **Transactional Outbox At-Least-Once 보장** |
| 팀 오너 | **김규태** (개발 2팀장, ARCHITECTURE.md 작성자) |

### 현재 운영 중 연동 벤더

| 벤더 | 코드 | `vendorType` | `vendorBusinessScopes` | 활성 |
|------|-----|------------|---------------------|:----:|
| 지마켓 | GMARKET (GMAS) | OPEN_MARKET | FULL_COMMERCE | ✅ |
| 옥션 | AUCTION (AUAS) | OPEN_MARKET | FULL_COMMERCE | ✅ |
| 11번가 | ST11 (ESAS) | OPEN_MARKET | FULL_COMMERCE | ✅ |
| 쿠팡 | COUPANG (COPG) | OPEN_MARKET | FULL_COMMERCE | ❌ (비활성) |
| ~~B2B_BULK_ORDER~~ | B2BO (주석) | **IN_HOUSE_COMMERCE** | ORDER_INFO | ❌ (미개발) |

근거: `bazaar-base/src/main/kotlin/kr/co/aladin/bazaar/base/constants/Vendor.kt`

### "SF 연계 미준비"의 정확한 의미

- 바자르 자체는 **공급측(Supply) 오케스트레이터로 성숙**
- 수요측으로 이미 **오픈마켓 4개 연동** 운영 중
- 단 **B2B 전용몰 같은 In-House 수요 채널**은 **설계만 예약됐고 구현 안 됨**
- 따라서 SF는 **"활성화되지 않은 B2B 경로를 깨우는 최초의 In-House Vendor"**

---

## 2. 바자르 핵심 개념 (실 코드 용어)

SF 팀이 반드시 이해해야 할 바자르 용어. **바자르 코드와 용어 일치 필수**.

### 2-1. SupplierReference vs VendorReference

```
SupplierReference = 상품의 원천 (= 알라딘 본사)
    ├─ supplier: Supplier enum (현재 알라딘 MSSQL만)
    └─ referenceId: String (알라딘 쪽 상품·주문 ID)

VendorReference = 판매 채널 (= 오픈마켓 또는 SF)
    ├─ vendor: Vendor enum (GMARKET, ST11, ..., 향후 B2B_STOREFRONT)
    └─ referenceId: String (채널 쪽 상품·주문 ID)
```

**ProductRootEntity 구조**:
```
Product
  ├─ supplierReference  (알라딘 원천 상품)
  ├─ productType        (KOREAN_BOOK | FOREIGN_BOOK | EBOOK | ...)
  ├─ productFulfillmentType  (SHIPPING 등)
  ├─ productGrade       (NEW | USED)
  ├─ productStatus      (NORMAL | TEMP_OUT_OF_STOCK | OUT_OF_STOCK | EXCLUDED)
  ├─ stock
  ├─ shipmentLocationKey  (출고지 UUID — SHIPPING 타입만)
  ├─ returnLocationKey    (반품지 UUID — SHIPPING 타입만)
  ├─ bookInfo             (도서 메타: ISBN·저자·출판사)
  └─ productVendorItems[]  (채널별 등록 정보)
      └─ 각각 vendorReference + 판매 상태 + 동기화 상태
```

**OrderRootEntity 방향성**:
```
Order
  ├─ vendorReference     (vendor 쪽 주문 ID — 오픈마켓 주문 번호)
  ├─ supplierReference   (supplier 쪽 주문 ID — 알라딘 주문 번호, 나중에 생성)
  ├─ orderVendorStatus   (CREATED | CHANGED)
  ├─ supplierOrderStatus (CREATE_READY → CREATE_PROCESSING → CREATE_APPLIED | CREATE_REJECTED)
  ├─ orderSyncStatus     (PENDING | PROCESSING | SYNCED | FAILED | NOT_APPLICABLE)
  └─ orderItems[]
```

**흐름**: 채널 주문 수신 → 바자르 저장 → 알라딘 supplier 주문 생성 → 알라딘 이행

**SF 관점 적용**: SF가 주문을 만들면 → `vendorReference.vendor = B2B_STOREFRONT` + vendor 쪽 referenceId = SF 주문 번호 → 바자르가 알라딘 supplier 주문 생성 트리거.

### 2-2. VendorBusinessScope — 능력 매트릭스

바자르는 벤더마다 **지원 범위**를 세분화. 6가지:

| Scope | 설명 (실 코드) |
|-------|------------|
| `CATALOG` | 상품 등록·수정·삭제만 지원 |
| `ORDER_INFO` | 주문 조회만 가능, 상품 정보 없어 이행 불가 |
| `FULFILLMENT` | 풀필먼트만 처리, 상품/주문 정보 검증 불가, 이행타입·서플라이어 정보 전달 필요 |
| `FULL_COMMERCE` | 상품-주문-이행 전체 프로세스 |
| `AFTER_SALES` | 반품/교환/취소 등 클레임 및 이행 |
| `CUSTOMER_SUPPORT` | CS 및 문의 처리 |

근거: `Vendor.kt:38-48`

**SF 권장 초기 Scope**: `FULL_COMMERCE + AFTER_SALES` (상품 조회 + 주문 생성 + 이행 위임 + 클레임). **`CUSTOMER_SUPPORT`는 Phase 2+**.

### 2-3. Fulfillment 2가지 모드

`FulfillmentRootEntity`가 특별한 이중 모드 지원:

- **`isIntegratedMode`** (`domainKey != null`): Order와 엮인 통합 이행
- **`isStandaloneMode`** (`domainKey == null`): 독립 이행 (Order 없이도 가능)

`FulfillmentDomainSource`로 출처 구분. SF 주문의 이행은 **Integrated 모드**로 진입해야 Order와 연결됨.

### 2-4. Resolution — 후처리 (교환·반품·취소)

```
Resolution
  ├─ fulfillmentKey: UUID  (연관 Fulfillment)
  ├─ orderKey: UUID        (원본 Order)
  ├─ resolutionType: ResolutionType  (CANCEL | RETURN | EXCHANGE 등)
  ├─ resolutionSupplierStatus  (READY → PROCESSING → APPLIED | REJECTED)
  └─ resolutionItems[]
```

**SF 관점**: SF가 취소/반품/교환 요청 → 바자르 Resolution 생성 → 알라딘 supplier에 위임.

### 2-5. Transactional Outbox

**핵심**: 바자르는 **At-Least-Once Delivery** 보장. SF는 바자르 OutboxEvent를 구독해 이벤트 수신. 멱등성은 구독자(SF) 책임.

---

## 3. 핵심 발견 — VendorType.IN_HOUSE_COMMERCE 예약

`Vendor.kt:17` 주석 처리된 항목:

```kotlin
// B2B_BULK_ORDER("B2BO", false, VendorType.IN_HOUSE_COMMERCE, "B2B 대량주문", 
//                setOf(VendorBusinessScope.ORDER_INFO)),
```

**해석**:

1. **바자르 팀이 이미 B2B를 의도적으로 설계에 반영** — 김규태가 만든 흔적
2. `VendorType` enum에 `OPEN_MARKET`과 **`IN_HOUSE_COMMERCE`** 두 타입 존재 (`Vendor.kt:32-35`)
3. `IN_HOUSE_COMMERCE` = "알라딘 내부가 직접 운영하는 상거래 채널"
4. B2B_BULK_ORDER는 **대량구매(견적) 고객용**으로 예약. SF의 **견적 몰**과 정확히 일치
5. 일반 몰(공통 몰)용으로 **B2B_STOREFRONT** 같은 추가 항목 필요

### 이것이 SF 설계에 미치는 영향

- **공통 몰 MVP 첫 고객 = 일반 임직원 구매자**는 `VendorType.IN_HOUSE_COMMERCE`의 **신규 vendor** 등록이 정석
- 견적 몰(Phase 2b)은 예약된 `B2B_BULK_ORDER`를 활성화하면 됨
- 이 방향이 바자르 팀(김규태)이 **이미 인지한 설계 경로**라서 협의 난이도 낮음

---

## 4. SF ↔ 바자르 3가지 연동 모델

### 옵션 A — 신규 Vendor 등록 (권장)

```
 B2B 임직원 ─▶ SF ─(주문 생성)─▶ 바자르 (vendor=B2B_STOREFRONT) ─▶ 알라딘 supplier
                   ◀──(Outbox 이벤트: 배송 상태 등)──                    │
                                                                       ▼
                                                                   알라딘 이행
```

- SF = `Vendor.B2B_STOREFRONT (VendorType=IN_HOUSE_COMMERCE, Scopes=[FULL_COMMERCE, AFTER_SALES])`
- **`Vendor.B2B_BULK_ORDER`** 활성화는 견적 몰(Phase 2b)

### 옵션 B — 바자르 우회, 알라딘 supplier 직접 호출

```
 SF ─(직접)─▶ 알라딘 MSSQL (supplier-aladin 재사용)
```

- **장점**: 바자르 변경 없음
- **단점**: 이행·클레임·재고·상태 머신 전부 SF가 재구현. **거대한 낭비**

### 옵션 C — 바자르를 라이브러리로 포함

- 바자르 모듈을 SF가 가져와 같은 Runtime에서 호출
- 너무 깊은 결합. 팀 소유권 경계 모호. **비추천**

### 내 권장: **옵션 A**

이유:
- `VendorType.IN_HOUSE_COMMERCE`가 이미 설계에 존재 (김규태가 예약)
- 바자르의 Product·Order·Fulfillment·Resolution 오케스트레이션 **그대로 재사용**
- Outbox 이벤트 발행 인프라 재사용
- SF-바자르 결합도는 API·이벤트 수준으로 **명확히 분리**

---

## 5. 권장 모델 — 새 Vendor.B2B_STOREFRONT 등록

### 5-1. Vendor.kt 추가 (바자르 측 변경)

```kotlin
// 예상 추가
B2B_STOREFRONT("B2SF", true, VendorType.IN_HOUSE_COMMERCE, "B2B 스토어프론트",
               setOf(VendorBusinessScope.FULL_COMMERCE, VendorBusinessScope.AFTER_SALES)),

// 견적 몰 (Phase 2b, 기존 주석 활성화)
B2B_BULK_ORDER("B2BO", true, VendorType.IN_HOUSE_COMMERCE, "B2B 대량주문",
               setOf(VendorBusinessScope.FULL_COMMERCE, VendorBusinessScope.AFTER_SALES)),
```

**변경 영향 범위**:
- `Vendor.kt` enum 항목 추가 (1 라인)
- `VendorAccount.kt` 계정 매핑 추가 (필요 시)
- `ProductAggregate.addAllOpenMarketVendors()`는 이름 그대로 OK (오픈마켓만 돌아감)
- **신규**: `addInHouseVendor(vendor: Vendor)` 같은 메서드 (SF만 선택 등록)

### 5-2. `VendorBusinessScope` 활용

| 단계 | SF의 Scope | 의미 |
|------|----------|------|
| MVP Phase 1 | `FULL_COMMERCE + AFTER_SALES` | 상품 조회 + 주문 생성 + 이행 위임 + 클레임 |
| Phase 2 | + `CUSTOMER_SUPPORT` | CS 문의 연계 |

---

## 6. 책임 경계 매트릭스 (실 도메인 기반)

| 영역 | 바자르 소유 (실코드 확인) | SF 소유 (신규) | 비고 |
|------|---------------------|-----------|------|
| 상품 원천 데이터 | ✅ `ProductRootEntity` + `supplier-aladin-mssql` | — | SF는 Query Port로 참조만 |
| 상품 카테고리 마스터 | ✅ `CategoryRootEntity` + 벤더 매핑 | — | SF `category` enum은 바자르 것 재사용 |
| 도서 정보 (ISBN·저자) | ✅ `ProductBookInfoEntity` | — | 조회만 |
| 재고 (실재고) | ✅ `Product.stock` + `decreaseStockWithStatus()` | — | SF는 수량 조회 + **수량 제한 정책**은 SF |
| 상품 상태 (품절·정상) | ✅ `ProductStatus` enum | — | 자동 전이 (품절 시 판매 정지) 바자르가 처리 |
| 출고지·반품지 | ✅ `shipmentLocationKey` / `returnLocationKey` | — | Location 도메인 별도 존재 |
| 가격 (원가) | ⚠️ 바자르 Product에 직접 `price` 필드 없음 — 알라딘 supplier에서 조회 | ✅ 테넌트 오버레이·할인율 | **가격 데이터 소스 확인 필요** |
| 주문 엔티티 | ✅ `OrderRootEntity` (vendor 주문 → supplier 주문 변환) | ✅ SF Order (테넌트 컨텍스트) | 양측 매핑 key: `SF.orderId = bazaar.Order.vendorReference.referenceId` |
| 주문 생명주기 | ✅ `orderVendorStatus`, `supplierOrderStatus`, `orderSyncStatus` | ✅ SF 상태 머신 | SF가 바자르 Outbox 구독해 상태 반영 |
| 주문 이행 | ✅ `FulfillmentRootEntity` (통합 vs 독립 모드) | — | SF는 상태 구독만 |
| 배송 상태·추적 | ✅ `FulfillmentShippingEntity` | L— | SF는 조회 |
| 교환·반품·취소 | ✅ `ResolutionRootEntity` + `ResolutionItemEntity` | ✅ **SF 클레임 오케스트레이션** (환원 순서·보상 Tx) | SF가 시작, 바자르가 실행 |
| 결제 오케스트레이션 | ❌ (바자르 책임 아님) | ✅ SF + 뉴빌링 | |
| 혜택·포인트 | ❌ | ✅ SF 자체 | |
| 테넌트·고객 | ❌ | ✅ Naru 위임 | 바자르에 `tenant_context` 필드 필요 여부 논의 |
| 감사 로그 | ✅ `AuditMetaData` 상속 (모든 Entity) | ✅ SF 자체 | 바자르 쪽 기존 감사 재사용 가능 |
| 이벤트 발행 | ✅ `OutboxRootEntity` (At-Least-Once) | ✅ SF Outbox | SF가 바자르 Outbox 구독 |

**원칙**:
- **상품·벤더 성격 종속 정책** → 바자르 (반품 가능 여부, 배송 방식)
- **고객·테넌트·채널 종속 정책** → SF (할인율, 포인트 한도, 분야 제한)

---

## 7. API 계약 설계 (Port 단위)

바자르 스타일(Command/Query 분리)에 맞춰 **SF가 호출할 4개 Port** 제안.

### Port 1 — `ProductQueryPort` (SF → 바자르)

SF가 상품 조회. 바자르의 기존 Query Repository를 노출.

```kotlin
interface BazaarProductQueryPort {
    // 외부 노출용 productKey(UUID)로 조회
    suspend fun findByProductKey(productKey: UUID): ProductSnapshot?
    
    // 카테고리별 조회 (SF 카탈로그 페이지용)
    suspend fun findByCategory(categoryKey: UUID, page: Int): List<ProductSnapshot>
    
    // 검색 (알리스와 혼용 여부는 D-04 4-3 참조)
    suspend fun search(query: ProductSearchQuery): List<ProductSnapshot>
}

data class ProductSnapshot(
    val productKey: UUID,
    val productName: String,
    val productType: ProductType,          // KOREAN_BOOK 등
    val productGrade: ProductGrade,        // NEW | USED
    val productStatus: ProductStatus,      // NORMAL 등
    val stock: Int,
    val bookInfo: BookInfo?,
    val basePrice: Money                   // 알라딘 원가 — 가격 데이터 소스 확인 필요
)
```

### Port 2 — `OrderDispatchPort` (SF → 바자르)

SF가 주문 생성 요청. 바자르가 `vendorReference.vendor = B2B_STOREFRONT`로 Order 저장 + supplier 주문 생성 트리거.

```kotlin
interface BazaarOrderDispatchPort {
    suspend fun createOrder(request: SfOrderCreateRequest): OrderKey  // UUID
    
    suspend fun changeOrder(orderKey: UUID, changes: OrderChangeRequest): Unit
    
    // 주문 생성 전 취소 (supplier 연동 전)
    suspend fun cancelBeforeSync(orderKey: UUID, itemKeys: List<UUID>): Unit
}

data class SfOrderCreateRequest(
    val sfOrderId: String,                 // vendor referenceId가 됨
    val tenantContext: TenantContext,      // SF만 의미 있음, 바자르는 메타로 저장
    val items: List<SfOrderItem>,
    val shippingAddress: ShippingAddress,
    val recipientInfo: RecipientInfo
)
```

### Port 3 — `ResolutionRequestPort` (SF → 바자르)

SF가 취소·반품·교환 요청.

```kotlin
interface BazaarResolutionRequestPort {
    suspend fun requestCancel(
        orderKey: UUID,
        itemKeys: List<UUID>,
        reason: String
    ): ResolutionKey
    
    suspend fun requestReturn(...)    // Phase 2
    suspend fun requestExchange(...)  // Phase 2
}
```

**중요**: SF가 **PG 취소·혜택 환원**을 먼저 오케스트레이션하고, 실 공급 취소만 바자르에 위임.

### Port 4 — `BazaarEventSubscriptionPort` (바자르 → SF)

바자르 Outbox 이벤트를 SF가 구독. 어댑터 방향이 반대이지만 **SF 측이 구독자**.

```kotlin
// SF 쪽 구현 (Consumer)
interface BazaarEventConsumer {
    suspend fun onOrderSynced(event: OrderSyncedEvent)
    suspend fun onFulfillmentStarted(event: FulfillmentStartedEvent)
    suspend fun onFulfillmentCompleted(event: FulfillmentCompletedEvent)
    suspend fun onResolutionCompleted(event: ResolutionCompletedEvent)
    suspend fun onStockChanged(event: StockChangedEvent)
}
```

---

## 8. 주문·이행·클레임 플로우

### 정상 플로우 (성공 경로)

```
[SF] 사용자 주문 확정
  │
  ├─▶ [SF] 혜택 차감 (알라딘 포인트)
  ├─▶ [SF] PG 결제 (뉴빌링)
  │    ↓ 성공
  └─▶ [SF→바자르] OrderDispatchPort.createOrder()
         │
         [바자르] OrderRootEntity 저장 (vendor=B2B_STOREFRONT)
         │   ↓ Outbox: OrderCreated
         │   
         [바자르] supplier 주문 생성 → 알라딘 MSSQL
         │   supplierOrderStatus: CREATE_READY → CREATE_PROCESSING → CREATE_APPLIED
         │   ↓ Outbox: OrderSynced
         │   
      ┌──◀ SF는 이벤트 구독 → 주문 상태 업데이트
      │   
      │  [바자르] Fulfillment 시작 (Integrated 모드, domainKey=orderKey)
      │     ↓ Outbox: FulfillmentStarted
      ├──◀ SF 주문 상태: 준비 중
      │     
      │  [바자르] Shipping → 알라딘 이행 → 배송 완료
      │     ↓ Outbox: FulfillmentCompleted
      └──◀ SF 주문 상태: 배송 완료 + 사용자 알림
```

### 취소 플로우 (Resolution)

```
[SF] 사용자 취소 요청
  │
  ├─▶ [SF] 취소 금액 산출 + 혜택 환원 순서 결정 (D-02 2-5)
  ├─▶ [SF] 혜택 환원 (알라딘 포인트)
  ├─▶ [SF] PG 취소 (뉴빌링)
  │    ↓
  └─▶ [SF→바자르] ResolutionRequestPort.requestCancel(orderKey, items, reason)
         │
         [바자르] Resolution 생성 (type=CANCEL)
         │   resolutionSupplierStatus: READY → PROCESSING → APPLIED
         │   ↓ Outbox: ResolutionCompleted
         │   
      ┌──◀ SF는 이벤트 구독 → 취소 최종 확정
      │   
      │  (Outbox 실패 시 재시도, SF 멱등성 보장 필요)
```

### Shadow Path (실패 경로)

| 시점 | 실패 종류 | 처리 |
|------|---------|------|
| 결제 승인 후, 바자르 주문 생성 실패 | `createOrder` 타임아웃·네트워크 | SF 보상 Tx: 혜택 환원 + PG 취소. 사용자 에러 |
| 바자르 supplier 주문 생성 실패 | `supplierOrderStatus=CREATE_REJECTED` | Outbox 이벤트로 SF에 알림. SF 보상 Tx |
| Fulfillment 실패 | `FulfillmentFailureEntity` | Outbox 이벤트. SF CS 영역 |
| Resolution 실패 | `ResolutionFailureEntity` | SF가 재시도 or 수동 처리 |

---

## 9. 이벤트 구독 스키마 (Outbox)

바자르는 이미 Outbox 발행 인프라가 있음. SF가 구독할 주요 이벤트 예상:

| 이벤트 | 트리거 | 페이로드 |
|-------|-------|--------|
| `OrderSynced` | `supplierOrderStatus = CREATE_APPLIED` | `orderKey, supplierOrderId, syncedAt` |
| `OrderSyncFailed` | `orderSyncStatus = FAILED` | `orderKey, orderFailures[]` |
| `FulfillmentStarted` | Fulfillment 시작 | `fulfillmentKey, orderKey, startAt` |
| `FulfillmentShippingUpdated` | 배송 상태 변화 | `fulfillmentKey, trackingInfo` |
| `FulfillmentCompleted` | `fulfillmentStatus = COMPLETED` | `fulfillmentKey, endAt` |
| `FulfillmentFailed` | 실패 | `fulfillmentKey, failures[]` |
| `ResolutionApplied` | `resolutionSupplierStatus = APPLIED` | `resolutionKey, orderKey, appliedAt` |
| `ProductStockChanged` | 재고 변동 | `productKey, newStock` |
| `ProductSaleStatusChanged` | 판매 상태 변화 (SUSPENDED 등) | `productKey, vendor=B2B_STOREFRONT, newStatus` |

**SF 측 구현 원칙**:
- **멱등성 키**: `(eventType, bazaarEventId)` — 동일 이벤트 재처리 안 함
- **순서 보장 X**: 이벤트 순서는 At-Least-Once라 보장 안 됨. SF가 상태 머신으로 방어
- **dead-letter**: 처리 실패 이벤트는 별도 큐로 격리

**바자르 측 이벤트 스키마 확인 필요**: `bazaar-core-domain/src/main/kotlin/kr/co/aladin/bazaar/core/domain/outbox/dto/` 조사 필요 (아직 안 함).

---

## 10. 바자르 측 필요 변경 사항

SF 연동을 위해 **바자르 코드에 필요한 변경** 예상:

### 10-1. 필수 (Phase 1 MVP)

| 변경 | 범위 | 파일 |
|------|-----|------|
| `Vendor.B2B_STOREFRONT` enum 추가 (+ 활성화) | 1 라인 | `Vendor.kt:17` |
| `VendorAccount.kt` 매핑 추가 | 소 | `bazaar-base/...` |
| SF용 주문 생성 API (REST endpoint) | 중 | `bazaar-apps/admin-api/` |
| SF용 상품 조회 API (Query) | 중 | `bazaar-apps/admin-api/` |
| SF용 Resolution 요청 API | 중 | `bazaar-apps/admin-api/` |
| `bazaar-apps/admin-api` Spring 설정 — 신규 SF endpoint | 소 | `application.yml` |
| Outbox 이벤트에 SF 대상 확장 (필터링 로직) | 소~중 | usecase/publisher |

### 10-2. 권장 (Phase 2)

| 변경 | 범위 |
|------|-----|
| `OrderRootEntity`에 `tenantContext` 필드 (B2B 테넌트 ID) | 마이그레이션 + 스키마 |
| `Vendor.B2B_BULK_ORDER` 활성화 (견적 몰) | 1 라인 |
| `FulfillmentType` — B2B 특화 타입 필요 시 추가 | — |

### 10-3. 미결 (추가 조사 필요)

- 현재 `addAllOpenMarketVendors()` 로직 — SF는 전체 벤더에 자동 추가되면 안 됨. `addInHouseVendor()` 분리 메서드 추가 필요
- `isProductGradeValidForOpenMarket()` — SF도 중고 상품 판매? 새 메서드 `isProductGradeValidForB2B()`
- `VendorAccount` 개념 — SF는 1개 계정만 필요한지

---

## 11. MVP 단계별 로드맵

| Phase | 시점 | 바자르 변경 | SF 구현 |
|------|-----|----------|--------|
| **Phase 0** | 2026-04 ~ 05 | 없음 — 설계 합의만 | 본 문서 + 김규태 협의 |
| **Phase 1 MVP** | 2026 Q2~Q3 | `Vendor.B2B_STOREFRONT` 활성화 + SF용 REST API 3개 (Order·Resolution·Product Query) | SF → 바자르 어댑터 (Port 4개 구현) |
| **Phase 2a** | 2026 Q4 | `tenantContext` 필드 추가 | 클레임 오케스트레이션 확장 (반품·교환) |
| **Phase 2b** | 2027 Q1 | `Vendor.B2B_BULK_ORDER` 활성화 | 견적 몰 라이브 |
| **Phase 3+** | 2027 Q2+ | 필요 시 `CUSTOMER_SUPPORT` Scope 확장 | CS 도구 연계 |

---

## 12. 김규태 팀장과의 협의 체크리스트

### 큰 방향 (30분)

- [ ] **Vendor.B2B_STOREFRONT** enum 추가 동의 (`VendorType.IN_HOUSE_COMMERCE`, Scope `FULL_COMMERCE + AFTER_SALES`)
- [ ] **B2B_BULK_ORDER** 활성화 시점 — Phase 2b(견적 몰) 기준
- [ ] 바자르 측 SF용 REST API 추가 — `bazaar-apps/admin-api/`에 endpoint 추가 방향
- [ ] **책임 경계 원칙**: 상품/벤더 성격 정책은 바자르, 고객/테넌트/채널 정책은 SF
- [ ] SF가 **Outbox 구독자로 등록** — 이벤트 소비 방식(Kafka? DB polling? HTTP callback?)

### 세부 설계 (60분)

- [ ] **ProductSnapshot의 price 필드** — 알라딘 원가가 바자르 어디에? (code 추적 필요)
- [ ] **tenantContext** 컬럼 추가 시점 — MVP부터 넣을지 Phase 2부터
- [ ] SF Order 생성 시 **`vendorReference.referenceId`는 SF 주문 UUID**로 통일
- [ ] `OrderItem.orderItemKey`와 SF OrderItem의 매핑
- [ ] **isShippingType 이외 FulfillmentType** (eBook 즉시 다운로드 등) SF 지원 범위
- [ ] Shipping 출고지·반품지 `Location` 도메인 SF 노출 여부

### 기술 세부 (60분 별도)

- [ ] Outbox 이벤트 **페이로드 스키마** 정식 계약 (JSON Schema 합의)
- [ ] **멱등성 키** 전달 방식 (event_id · order_id 등)
- [ ] **Authentication·Authorization** — SF → 바자르 API 인증 (JWT? Service Account?)
- [ ] **Rate Limit·SLA** (예: 주문 초당 10건 등)
- [ ] **에러 응답 포맷** (공통 Error 코드 스키마)

---

## 13. 미결 질문 (세부 조사 필요)

본 문서는 ARCHITECTURE.md + 도메인 Aggregate 4개 분석 기반. **아래 항목은 실 코드 더 봐야 확정**:

| # | 질문 | 조사 대상 |
|---|------|---------|
| Q1 | 상품 가격(원가) 어디에 저장되나 — bazaar-core-domain? supplier-aladin에서 매번 조회? | `ProductVendorItemEntity`, `AladinItemMapper` |
| Q2 | Outbox 이벤트 페이로드 실제 구조 | `outbox/dto/`, `bazaar-usecase/publisher/` |
| Q3 | `supplier-aladin-mssql` 정확한 접근 범위 (Read-only만? Write도?) | `CoolDataSourceConfig`, 어댑터 구현체 |
| Q4 | `Vendor.isSupportsAny` 로직 — SF 등록 시 기존 로직과 충돌 없는지 | `Vendor.kt:27-30`, 호출처 전수 |
| Q5 | `Reconciler` 도메인 역할 — SF에도 필요한가 | `ReconcilerRootEntity`, `usecase/reconciler` |
| Q6 | `Location` 도메인 (출고지·반품지) — SF가 지정? 자동? | `LocationRootEntity` |
| Q7 | `Category` 도메인 — 카테고리 생성·변경 주체 | `CategoryRootEntity`, `addAllOpenMarketVendors` 호출 흐름 |
| Q8 | `FulfillmentDomainSource` 값들 — SF는 어느 source로 분류? | `FulfillmentDomainSource` enum |
| Q9 | 바자르 측 테스트 커버리지 — SF 연동 시 회귀 방지 | `bazaar-core-domain/src/test/` |
| Q10 | `REFACTORING_CANDIDATES.md`에 SF 영향권 이슈 있는지 | `bazaar-core-domain/REFACTORING_CANDIDATES.md` |
| Q11 | `docs/tbd/PRODUCT_CONTENT_ARCHITECTURE.md` 내용 — SF 관련 방향성 | 해당 파일 |

---

## 14. 참조 파일 경로

### 바자르 측 (실제 읽은 파일)

| 파일 | 위치 | 핵심 내용 |
|------|-----|--------|
| ARCHITECTURE.md | `bazaar/BazaarServer/docs/architecture/` | 전체 아키텍처·DDD·도메인 |
| CLAUDE.md | `bazaar/BazaarServer/` | 모듈 요약 |
| Vendor.kt | `bazaar-base/.../constants/Vendor.kt` | Vendor enum + VendorType + VendorBusinessScope |
| ProductAggregate.kt | `bazaar-core-domain/.../product/` | 상품 비즈니스 로직 |
| ProductRootEntity.kt | `bazaar-core-domain/.../product/entity/` | Product 모델 |
| OrderAggregate.kt | `bazaar-core-domain/.../order/` | 주문 오케스트레이션 |
| OrderRootEntity.kt | `bazaar-core-domain/.../order/entity/` | Order 모델 (vendor/supplier 2중 참조) |
| FulfillmentRootEntity.kt | `bazaar-core-domain/.../fulfillment/entity/` | 이행 모델 (Integrated/Standalone) |
| ResolutionRootEntity.kt | `bazaar-core-domain/.../resolution/entity/` | 후처리 모델 |

### SF 측 참조 문서

- [`../domain/b2b-store-domain-decisions.md`](../domain/b2b-store-domain-decisions.md) — D-01~D-20 마스터
- [`../domain/b2b-store-mvp-definition-0422.md`](../domain/b2b-store-mvp-definition-0422.md) — MVP 정의
- [`b2b-store-ddd-classification.md`](./b2b-store-ddd-classification.md) — DDD 분류
- [`b2b-store-tenant-model.md`](./b2b-store-tenant-model.md) — 테넌트 모델

---

## 종합 — 이번 분석의 가장 큰 수확

**바자르 팀이 이미 `VendorType.IN_HOUSE_COMMERCE`와 `Vendor.B2B_BULK_ORDER`를 예약해뒀다**는 발견. 이건:

1. **김규태 팀장이 B2B 확장을 사전 설계에 반영** — 협의 난이도 낮음
2. SF는 **"처음 시도하는 경로"가 아니라 "예약된 경로를 활성화"**하는 작업
3. 바자르 측 변경이 최소 (Vendor.kt 한 라인 + API 몇 개)
4. **옵션 A(신규 Vendor 등록)가 정석**이라는 결론

다음 스텝:
1. 본 문서를 김규태와 공유 → 1시간 협의
2. 미결 11개(§13) 중 Q1~Q4 우선 조사
3. Phase 1 MVP의 API 4개 계약 정식화
4. Outbox 이벤트 스키마 확정

본 문서는 **살아있는 문서**. 세부 조사 진행되는 대로 §13 미결이 확정 절로 이동.
