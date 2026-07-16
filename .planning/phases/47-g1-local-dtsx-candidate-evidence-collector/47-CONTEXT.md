# Phase 47 Context - G1 로컬 DTSX 후보 증거 수집기

## 배경

사용자가 G1 read-only evidence 수집을 승인했다. 다만 현재 세션에서 운영 SQL Agent, 운영 DTSX 배포본, SP definition, golden output 저장소에 직접 접근할 수 있는 확정 접속 정보는 아직 확인되지 않았다.

로컬 `/Users/jm/Documents/workspace/ssis`에는 우선 대상 DTSX 후보 파일이 존재한다. 이 파일들은 운영 canonical 증거는 아니지만, 승인된 operator export와 비교할 수 있는 checksum 기준선으로는 의미가 있다.

## 확인된 로컬 DTSX 후보

- `dev1-ssis-cool/src/DTS_NaverDBFile/DTS_NaverDBFile_Make_V2.dtsx`
- `dev1-ssis-cool/src/DTS_NaverDBFile/DTS_NaverDBFile_Make_V2_Today.dtsx`
- `dev1-ssis-cool/src/DTS_NaverDBFile/DTS_NaverShopDBFile_Make.dtsx`
- `dev1-ssis-cool/src/DTS_NaverDBFile/DTS_NaverShopDBFile_Make_Today.dtsx`
- `dev1-ssis-cool/src/DTS_GoogleShop_DBFile/DTS_GoogleShop_DBFile_Make_TSV_V2.dtsx`
- `dev1-ssis-cool/src/DTS_GoogleShop_DBFile/DTS_GoogleShop_DBFile_Make_Today_TSV_V2.dtsx`
- `dev1-ssis-cool/src/DTS_DaumDBFile_Make/KakaoDaum.dtsx`

## 범위

- 로컬 후보 DTSX checksum fragment directory 생성.
- 운영 증거와 혼동되지 않도록 source type을 `LOCAL_REPO_CANDIDATE`로 분리.
- G1 validator/readiness는 계속 차단 상태를 유지.

## 비범위

- SQL Agent 조회.
- SP definition 조회.
- golden output 생성 또는 partner endpoint publish.
- 운영 DTSX 실행 또는 production file 변경.
