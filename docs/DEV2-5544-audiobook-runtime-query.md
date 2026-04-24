# DEV2-5544 오디오북 런닝타임/mp3 파일 수 추출

- **티켓**: [DEV2-5544](https://aladincommunication.youtrack.cloud/issue/DEV2-5544)
- **요청자**: jjk (B2B솔루션팀)
- **요청일**: 2026-04-10
- **DB**: EbookCms (개발)

## 테이블 구조

| 테이블 | 역할 | 주요 컬럼 |
|--------|------|-----------|
| `Product` | 상품 마스터 | `ProductNo`, `ItemId`, `Title`, `IsAudioBook` |
| `ProductAudioBookToc` | 오디오북 TOC (mp3 파일 단위) | `ProductNo`, `Duration`(초), `IsPrev`, `Status` |

- `Product.ProductNo` → `ProductAudioBookToc.ProductNo` JOIN
- `Duration`: 초 단위
- `IsPrev = 1`: 프리뷰 파일 (제외 대상)
- `Status = 1`: 활성 파일

## SQL

```sql

CREATE TABLE #TempItemIds
(
    No Int NOT NULL,
    ItemId INT NOT NULL
);

INSERT INTO #TempItemIds (No, ItemId) VALUES (1, 390349785);


select count(*) from #TempItemIds;
drop table #TempItemIds


SET NOCOUNT ON;
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;

SELECT
    p.ItemId,
    p.Title,
    COUNT(t.ContentNo)                          AS Mp3FileCount,
    SUM(t.Duration)                             AS TotalDurationSec,
    RIGHT('0' + CAST(SUM(t.Duration)/3600 AS VARCHAR), 2)
      + ':' + RIGHT('0' + CAST((SUM(t.Duration)%3600)/60 AS VARCHAR), 2)
      + ':' + RIGHT('0' + CAST(SUM(t.Duration)%60 AS VARCHAR), 2)
                                                AS TotalDuration_HHMMSS
FROM Product p
JOIN ProductAudioBookToc t ON p.ProductNo = t.ProductNo
WHERE p.ItemId IN (
    -- 여기에 ItemID 벌크 입력 (첨부 엑셀에서 추출)
    123456, 789012
)
AND p.IsAudioBook = 1
AND t.Status = 1
AND ISNULL(t.IsPrev, 0) = 0
GROUP BY p.ItemId, p.Title
ORDER BY p.ItemId;
```

## 결과 컬럼

| 컬럼 | 설명 |
|------|------|
| `ItemId` | 상품 ItemID |
| `Title` | 오디오북 제목 |
| `Mp3FileCount` | mp3 파일 수 (프리뷰 제외) |
| `TotalDurationSec` | 총 런닝타임 (초) |
| `TotalDuration_HHMMSS` | 총 런닝타임 (HH:MM:SS) |

## 사용법

1. 첨부 엑셀(`오디오북 런닝타임_mp3파일수_20260410.xlsx`)에서 ItemID 목록 추출
2. `IN (...)` 절에 콤마 구분으로 입력
3. EbookCms DB에서 실행
