---
service: aladin-infra
service_id: aladin-infra
title: 알라딘 인프라 로그인 히스토리 인벤토리
tags:
  - inventory
  - aladin-infra
  - webcatalog
  - login-history
  - appdevice
---

# 알라딘 인프라 로그인 히스토리 인벤토리

알라딘 인앱(쇼핑앱/마켓앱/북플앱/뷰어앱/투비앱)과 웹의 로그인 활동 로그가 어디 있고, 디바이스 OS 정보가 어디서 결합되는지를 정리한다. `aaintraweb`의 `CustomerInBox.aspx > 로그인 탭`이 보여주는 데이터를 재현하거나, 만권당 운영 분석(예: 특정 OS 버전 사용자 추출)에 사용할 때 참조한다.

## 핵심 테이블

| 테이블 | 역할 | 특징 |
|---|---|---|
| `CustomerLoginHistory` (WebCatalog) | 실제 로그인 활동 로그 | 매우 큼, 인덱스 부족(SP 코멘트에 명시), `Custkey + LoginDate` 필터 필수 |
| `Community.dbo.AppDevice` | 디바이스 마스터 (`OsType` / `OsVer` / `DeviceInfo`) | UUID 기준 |
| `CustomerLoginMode` | `LoginMode` 코드 → 설명 룩업 | 보조 |

## 조인 패턴

`CustomerLoginHistory.UUID` 또는 `CustomerLoginHistory.UserAgent` 가 `AppDevice.UUID` 와 매칭되는 케이스가 섞여 있어 `OR` 조건이 필요하다.

```sql
FROM CustomerLoginHistory C WITH(NOLOCK)
OUTER APPLY (
    SELECT TOP(1) OsType, OsVer, DeviceInfo
    FROM Community.dbo.AppDevice D WITH(NOLOCK)
    WHERE D.UUID = C.UUID OR D.UUID = C.UserAgent
) D
```

## `LoginType` 매핑

| LoginType | AppName | 비고 |
|---|---|---|
| 1 | PC 웹 / 모바일 웹 | UserAgent에 `Mobile`/`iPhone`/`Android` 포함 여부로 분기 |
| 5 | **쇼핑앱** | 알라딘 메인 쇼핑앱. 사용자 회화에서 “알라딘앱”이라 부르는 대상 |
| 6 | 북플앱 | |
| 7 | 뷰어앱 | e-book 뷰어. 만권당 콘텐츠 소비 |
| 13 | 마켓앱 | `AladinMarket/x.x.x` UserAgent 토큰을 쓰는 앱 |
| 14 | 투비앱 | |

UserAgent의 `AladinMarket/` 토큰은 **마켓앱(13)**이지 쇼핑앱이 아니다. “알라딘앱 사용자”라는 표현이 쇼핑앱을 의미한다면 `LoginType=5`를 쓰고, UA 패턴은 보조 단서로만 사용한다.

## `Community.dbo.AppDevice` 컬럼 핵심

- `OsType`: 1 = iOS, 0 = Android
- `OsVer`: `'15.3.1'`, `'14.7.1'` 형식 (점 구분). UA 파싱 없이 직접 사용 가능.
- `DeviceInfo`: 예) `iPhone12,1`

## 함정 테이블 (시간 낭비 방지)

| 테이블 | 사용하면 안 되는 이유 |
|---|---|
| `mobile_app_stats` | 2012년 6건만 있는 죽은 테이블 |
| `CustomerDeviceAccess[_Info]` | 활동 로그가 아닌 **디바이스 인증 마스터** (5년 597K 행 ≈ 일 325건) |
| `EbookDeviceAccessHistory` | 만권당 **뷰어앱 전용** (iOS UA 0건, 안드로이드 Dalvik만 잡힘) |
| `TicketLog_AladinMarket` | 알라딘마켓 **정산 로그** (`OID/PaySum` 등) — 로그인 로그가 아님 |

## 발견 경로

- 화면: `https://www.aladin.co.kr/aaintraweb/PageTracker/CustomerInBox.aspx?QueryType=8`
- 코드: `aladin/dev1-web-aladin/WebRelease/AaIntraWeb/PageTracker/CustomerInBox.aspx.cs:172` → `ConnStr.WebCatalog`
- 호출 SP: `Customer_InBox_Timeline_V2 @QueryType=8` (WebCatalog DB)
- SP 추가 이력: 2023-03-10 (작성자 jihye)

## `Customer_InBox_Timeline_V2 @QueryType=8` 동등 쿼리

화면을 raw 데이터로 재현해야 할 때 사용한다. `Custkey` 단건 조회용.

```sql
SET NOCOUNT ON;
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;

DECLARE @Custkey   int           = 0;          -- 조회 대상
DECLARE @StartDate smalldatetime = DATEADD(MONTH, -3, GETDATE());

SELECT
    C.LoginDate,
    C.LoginType,
    CASE C.LoginType
        WHEN 1  THEN
            CASE WHEN (CHARINDEX('Mobile',  ISNULL(C.UserAgent,'')) +
                       CHARINDEX('iPhone',  ISNULL(C.OS,''))        +
                       CHARINDEX('Android', ISNULL(C.OS,''))) > 0
                 THEN '모바일 웹' ELSE 'PC 웹' END
        WHEN 5  THEN '쇼핑앱'
        WHEN 6  THEN '북플앱'
        WHEN 7  THEN '뷰어앱'
        WHEN 13 THEN '마켓앱'
        WHEN 14 THEN '투비앱'
        ELSE dbo.fn_LoginTypeDesc(C.LoginType)
    END AS AppName,
    CASE C.SNSType
        WHEN 0 THEN '알라딘' WHEN 1 THEN '트위터' WHEN 2 THEN '페이스북'
        WHEN 3 THEN '네이버' WHEN 4 THEN '카카오' WHEN 5 THEN '구글'
        WHEN 6 THEN '삼성패스' WHEN 7 THEN '페이코' WHEN 8 THEN '애플'
        ELSE '' END AS SNS,
    CASE WHEN C.LoginType IN (5,6,7,13,14)
         THEN D.DeviceInfo + ' (' +
              (CASE WHEN D.OsType = 1 THEN 'iOS ' ELSE 'Android ' END) + D.OsVer + ')'
         ELSE CASE WHEN ISNULL(C.OS,'') <> ''
                   THEN ISNULL(C.OS,'') + ' ' + ISNULL(C.OSVer,'')
                   ELSE C.OS END
    END AS LoginEnv,
    D.OsType, D.OsVer, D.DeviceInfo,
    C.UUID, C.UserAgent, C.RequestUrl, C.ReferrerUrl, C.IpAddr, C.[UID],
    CASE WHEN C.LoginMode > 0
         THEN (SELECT LoginModeDesc FROM CustomerLoginMode WHERE LoginMode = C.LoginMode)
         ELSE '' END AS LoginMode
FROM CustomerLoginHistory C WITH(NOLOCK)
OUTER APPLY (
    SELECT TOP(1) OsType, OsVer, DeviceInfo
    FROM Community.dbo.AppDevice D WITH(NOLOCK)
    WHERE D.UUID = C.UUID OR D.UUID = C.UserAgent
) D
WHERE C.Custkey   = @Custkey
  AND C.LoginDate > @StartDate
ORDER BY C.LoginDate DESC;
```

## 활용 예시 — 만권당 유료 사용자 중 iOS 10~14 + 쇼핑앱 로그인

만권당 유료 회원 중 구버전 iOS(10~14)에서 쇼핑앱을 쓰는 사용자를 추출한다. `MaxPass`(약 1만 행 수준)를 시작점으로 잡아 `CustomerLoginHistory` 풀스캔을 피한다.

유료 정의는 `MaxPass.IsActive=1 AND IsUsed=1 AND GETDATE() BETWEEN UseStartDate AND UseEndDate AND ISNULL(OID,0) > 0`. `OID > 0`이면 `EventId` 동반 여부와 무관하게 유료(이용권 결제 포함)로 본다. `EventId`만 있고 `OID NULL`이면 이벤트 무료 발급으로 제외한다.

```sql
SET NOCOUNT ON;
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;

;WITH PaidMaxPass AS (
    SELECT Custkey, MAX(UseEndDate) AS MaxPassEndDate
    FROM MaxPass WITH(NOLOCK)
    WHERE IsActive = 1
      AND IsUsed   = 1
      AND GETDATE() BETWEEN UseStartDate AND UseEndDate
      AND ISNULL(OID, 0) > 0
    GROUP BY Custkey
)
SELECT
    p.Custkey,
    d.OsType,
    d.OsVer,
    d.DeviceInfo,
    ca.LoginDate AS LastShoppingAppLogin,
    p.MaxPassEndDate
FROM PaidMaxPass p
CROSS APPLY (
    SELECT TOP(1) c.LoginDate, c.UUID, c.UserAgent
    FROM CustomerLoginHistory c WITH(NOLOCK)
    WHERE c.Custkey   = p.Custkey
      AND c.LoginType = 5                                   -- 쇼핑앱
      AND c.LoginDate >= DATEADD(DAY, -90, GETDATE())
    ORDER BY c.LoginDate DESC
) ca
OUTER APPLY (
    SELECT TOP(1) OsType, OsVer, DeviceInfo
    FROM Community.dbo.AppDevice WITH(NOLOCK)
    WHERE UUID = ca.UUID OR UUID = ca.UserAgent
) d
WHERE d.OsType = 1                                          -- iOS만
  AND (
        d.OsVer LIKE '10.%' OR d.OsVer = '10' OR
        d.OsVer LIKE '11.%' OR d.OsVer = '11' OR
        d.OsVer LIKE '12.%' OR d.OsVer = '12' OR
        d.OsVer LIKE '13.%' OR d.OsVer = '13' OR
        d.OsVer LIKE '14.%' OR d.OsVer = '14'
      )
ORDER BY ca.LoginDate DESC;
```

성능 노트:
- 시작점이 `MaxPass`라 `CustomerLoginHistory` 풀스캔이 회피된다.
- `CROSS APPLY` 안의 `Custkey + LoginDate` 조건이 인덱스를 탄다.
- 화면 SP는 기본 3개월 윈도우를 쓰며, 본 활용 쿼리는 운영 판단으로 90일 윈도우를 사용한다.
- iOS 10~14가 아닌 다른 OS 버전 분석이 필요하면 마지막 `OsVer LIKE` 블록만 교체한다.
