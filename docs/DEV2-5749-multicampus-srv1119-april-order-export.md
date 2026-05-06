# DEV2-5749 멀티캠퍼스 농어촌공사 4월 내역 추출 SQL

- 티켓: [DEV2-5749](https://aladincommunication.youtrack.cloud/issue/DEV2-5749)
- 요청: 멀티캠퍼스 농어촌공사 북러닝 4월 신청 내역 추출
- 교육그룹코드: `SRV1119`
- 기준 기간: `2026-04-01` 이상, `2026-05-01` 미만

## 추출 SQL

```sql
-- 주문 정보 추출
SELECT
    O.OID,
    O.OrderNo,
    O.OrderDate,
    O.OrderStatus,
    O.ShopCode,
    O.Custkey,
    O.DeliveryDate,
    O.ExpectDeliveryDate,
    OP.PriceSum,
    ISNULL((
        SELECT SUM(P.PayAmount)
        FROM dbo.OrdersPay P WITH (NOLOCK)
        WHERE P.OID = O.OID
          AND P.PayType <> 155
    ), 0) AS RealPay,
    ISNULL((
        SELECT SUM(P.PayAmount)
        FROM dbo.OrdersPay P WITH (NOLOCK)
        WHERE P.OID = O.OID
          AND P.PayType = 155
    ), 0) AS MulticamPoint
INTO #tmpOrders
FROM dbo.Orders O WITH (NOLOCK)
INNER JOIN dbo.OrdersPrice OP WITH (NOLOCK)
    ON OP.OID = O.OID
WHERE O.OID >= dbo.fn_OID_FirstOfDate('2026-04-01')
  AND O.OID <  dbo.fn_OID_FirstOfDate('2026-05-01')
  AND O.OrderFlag = 1
  AND O.OrderStatus >= 5
  AND O.AccidentType = 0
  AND O.AssociateCode = 12942;

-- 최종 결과 추출
SELECT
    P.OpnRngMapngTgtCd AS [교육그룹코드],
    P.PartnerCodeDesc AS [교육그룹명],
    T.OrderNo AS [주문번호],
    T.OrderDate AS [주문일],
    T.OrderStatus AS [단계],
    C.CustomerName AS [주문인],
    D.ReceiverName AS [수취인],
    OI.PriceStd AS [정가합],
    OI.PriceSales AS [판매가합],
    OI.InPrice AS [입고가합],
    T.MulticamPoint AS [포인트결제금액합],
    T.RealPay AS [개인결제금액합],
    T.DeliveryDate AS [출고일],
    T.ExpectDeliveryDate AS [출고예정일],
    CASE
        WHEN T.ShopCode IN (109022, 981283) THEN N'전자책'
        ELSE N'종이책'
    END AS [주문(종이책/전자책)]
FROM #tmpOrders T
INNER JOIN dbo.Customer C WITH (NOLOCK)
    ON C.Custkey = T.Custkey
INNER JOIN dbo.MultiCam_Customer PC WITH (NOLOCK)
    ON PC.Custkey = C.Custkey
INNER JOIN dbo.MultiCam_Partner P WITH (NOLOCK)
    ON P.PartnerCode = PC.PartnerCode
LEFT JOIN dbo.OrdersDeliveryAddress D WITH (NOLOCK)
    ON D.OID = T.OID
CROSS APPLY (
    SELECT
        SUM(R.PriceStd * R.Qty) AS PriceStd,
        SUM(R.PriceSales * R.Qty) AS PriceSales,
        SUM(R.InPrice * R.Qty) AS InPrice
    FROM (
        SELECT
            OIS.PriceStd,
            OIS.InPrice,
            OIS.Qty,
            CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM dbo.OrdersItem OIP WITH (NOLOCK)
                    WHERE OIP.OID = OIS.OID
                      AND OIP.PackageItemId = OIS.ItemId
                      AND OIP.CancelFlag = 0
                )
                THEN (
                    SELECT SUM(OIP.PriceSales)
                    FROM dbo.OrdersItem OIP WITH (NOLOCK)
                    WHERE OIP.OID = OIS.OID
                      AND OIP.PackageItemId = OIS.ItemId
                      AND OIP.CancelFlag = 0
                )
                ELSE OIS.PriceSales
            END AS PriceSales
        FROM dbo.OrdersItem OIS WITH (NOLOCK)
        WHERE OIS.OID = T.OID
          AND OIS.CancelFlag = 0
          AND OIS.PackageItemId IS NULL
    ) R
) OI
WHERE P.OpnRngMapngTgtCd = 'SRV1119'
ORDER BY
    T.OID;

DROP TABLE #tmpOrders;
```
