# Phase 1 Research: DTSX Evidence Lock

## RESEARCH COMPLETE

## What We Need To Know To Plan Phase 1

Phase 1 is an evidence-lock phase. The only safe deliverable is a ledger and read-only evidence request. Local DTSX files prove candidate packages, but they do not prove active production schedules.

## Current Local Evidence

### Excel Rows

| Excel physical row | 업무 번호 | Partner | Trigger | Direction/format | Current endpoint |
|---:|---:|---|---|---|---|
| 15 | 13 | 네이버책 가격비교 | COOL DB스케줄 | `인바운드`, `https(jsonl)` | `www2.aladin.co.kr/b2b/navershoppingbook/product_aladdin.jsonl.js` |
| 16 | 14 | 네이버쇼핑 가격비교 | COOL DB스케줄 | `인바운드`, `https(txt)` | `www2.aladin.co.kr/b2b/navershopping/product_aladin.txt` |
| 17 | 15 | 네이버 판매량/베스트순위 | COOL DB스케줄 | `인바운드`, `ftp(??)` | `ftp.aladin.co.kr/naver/product_aladdin_unicode.txt` |
| 18 | 16 | 구글 | COOL DB스케줄 | `인바운드`, `ftp(??)` | `ftp.aladin.co.kr` |
| 19 | 17 | 다음 | COOL DB스케줄 | `인바운드`, `ftp(??)` | `ftp.aladin.co.kr` |

### DTSX Candidates

- `DTS_NaverDBFile_Make_V2.dtsx`
- `DTS_NaverDBFile_Make_V2_Today.dtsx`
- `DTS_NaverShopDBFile_Make.dtsx`
- `DTS_NaverShopDBFile_Make_Today.dtsx`
- `DTS_NaverDBFile_BestSellerMake.dtsx`
- `naver.dtsx`
- `DTS_GoogleShop_DBFile_Make_TSV_V2.dtsx`
- `DTS_GoogleShop_DBFile_Make_Today_TSV_V2.dtsx`
- `KakaoDaum.dtsx`
- `DTS_DaumDBFile_OldDataDelete.dtsx`

## Spring Version Baseline

- Spring Boot project page showed Spring Boot `4.1.0` as the current Boot 4 line on 2026-06-19.
- Spring Boot 4.1.0 system requirements require Java 17+ and Spring Framework 7.0.8+.
- Spring Boot 4 migration guide says Kotlin 2.2+ is required.
- Spring Batch project page showed Spring Batch `6.0.4`; Spring Batch 6 docs list features important for this migration: failed job recovery, graceful shutdown, local chunking, remote step support, and Jackson 3 support.

## Evidence Gaps

- SQL Agent `msdb` enabled jobs, steps, commands, schedules
- Operational DTSX deployment location and drift from repo
- SP definition and side effects
- Existing SSIS output golden files
- Current readback path and permission model
- Runtime account, network allowlist, secret source

## Planning Implications

- Phase 1 must not generate production code.
- Phase 1 must produce precise read-only queries/requests for approval.
- Row 15 remains blocked until active job evidence exists.
- The ledger should be the downstream source for Phase 2 architecture and Phase 4 job design.
