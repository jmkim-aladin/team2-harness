# 원장: IDC DB 이관 B2B SSIS 13-17

**Created:** 2026-06-19
**Project:** `partner-integration-batch`
**Purpose:** SSIS와 신규 Kotlin/Spring Batch 구현의 동등성을 증명하기 위한 배치 명세 원장.

## 원장 규칙

- DTSX는 Kotlin 코드로 자동 변환하지 않는다. DTSX는 현재 운영 배치 명세의 근거로 역공학한다.
- 로컬 repo DTSX는 후보 근거다. 운영 canonical은 SQL Agent `msdb` enabled job/step/package 확인 후 확정한다.
- 신규 구현은 Kotlin + Spring Boot 4.1.x + Spring Batch 6.0.x 기준이다.
- v1은 기존 파일/API/FTP/WWW 계약을 유지하거나 compatibility bridge로 보존한다. 제공 방식 변경은 이관 후 별도 phase다.
- 기존 SP/SQL 호출은 `LegacyDbAdapter`에만 둔다.
- 동등성 완료는 기존 SSIS golden output과 신규 output의 비교로만 인정한다.

## 대상 매핑

| Excel physical row | 업무 번호 | 파트너/업무 | 방향/방식 | 현재 제공 경로 | repo/DTSX 후보 | 신규 Job 후보 | Canonical 상태 |
|---:|---:|---|---|---|---|---|---|
| 15 | 13 | 네이버책 가격비교 | Excel 기준 `인바운드`, `https(jsonl)` | `www2.aladin.co.kr/b2b/navershoppingbook/product_aladdin.jsonl.js` | `DTS_NaverDBFile_Make_V2.dtsx`, `DTS_NaverDBFile_Make_V2_Today.dtsx` | `naverBookFeedJob` | SQL Agent 확인 필요 |
| 16 | 14 | 네이버쇼핑 가격비교 | Excel 기준 `인바운드`, `https(txt)` | `www2.aladin.co.kr/b2b/navershopping/product_aladin.txt` | `DTS_NaverShopDBFile_Make.dtsx`, `DTS_NaverShopDBFile_Make_Today.dtsx` | `naverShoppingFeedJob` | SQL Agent 확인 필요 |
| 17 | 15 | 네이버 판매량/베스트순위 등 | Excel 기준 `인바운드`, `ftp(??)` | `ftp.aladin.co.kr/naver/product_aladdin_unicode.txt` | `DTS_NaverDBFile_BestSellerMake.dtsx`, `DTS_NaverDBFile_Make_V2.dtsx` 내부 bestseller flow, `naver.dtsx` 후보 | `naverRankingFeedJob` | Blocked: scope 모호 |
| 18 | 16 | 구글 상품정보 | Excel 기준 `인바운드`, `ftp(??)` | `ftp.aladin.co.kr` | `DTS_GoogleShop_DBFile_Make_TSV_V2.dtsx`, `DTS_GoogleShop_DBFile_Make_Today_TSV_V2.dtsx` | `googleShoppingFeedJob` | SQL Agent 확인 필요 |
| 19 | 17 | 다음/KakaoDaum 상품정보 | Excel 기준 `인바운드`, `ftp(??)` | `ftp.aladin.co.kr` | `KakaoDaum.dtsx`, `DTS_DaumDBFile_OldDataDelete.dtsx` | `kakaoDaumFeedJob`, `feedRetentionJob` | SQL Agent 확인 필요 |

## DTSX Operation Classification

| 업무 번호 | 확인된 주요 operation | 신규 Batch 분해 |
|---:|---|---|
| 13 | `Naver_BestSeller_V2`, `Naver_Product_V2`, `Naver_Relative_V2`, `Naver_Product_Sales_Make`, file transform to JSONL/JSONL.js | `legacyPrepareSnapshot` tasklet -> JSONL streaming writer -> validate -> publish bridge |
| 14 | `Truncate Table NaverShopProduct`, `NaverShop_Product_Get`, `NaverShop_SaleStat_Get`, exception/remove item flow, old file cleanup | staging tasklet -> TXT writer -> validation -> publish bridge -> retention policy |
| 15 | `Naver_BestSeller*`/product/relative 후보 혼재 | active package 확정 후 분해 |
| 16 | `Truncate Table GoogleShopProduct_V2`, `GoogleShop_Product_TargetItems_Get_V2`, `GoogleShop_Product_Get_V2 @isToday, @groupId`, split file generation | staging tasklet -> partition/range reader -> TSV writer/MultiResource writer -> validation |
| 17 | `KakaoDaum_Book_Event`, `KakaoDaum_Book_EventBook`, `KakaoDaum_Book_Selling` with ebook/non-ebook, six XML outputs, old data delete | six XML step outputs -> XML validation -> publish bridge -> retention |

## Required Evidence

| Evidence | Purpose | Status | Approval |
|---|---|---|---|
| SQL Agent `msdb` enabled job/step/package/schedule | repo DTSX 후보를 운영 canonical로 확정 | Missing; request bundle `docs/g1-evidence/request-bundle.json` generated for approval/operator handoff | Required |
| Local DTSX inventory JSON | repo DTSX 후보의 package/connection/variable/task/precedence/SQL 후보 구조화 | Generated: `docs/dtsx-inventory/priority-13-17-inventory.json` | Not required |
| Local Spring Batch migration spec JSON | DTSX task/edge를 Spring Batch mapping 후보로 분류 | Generated: `docs/dtsx-spec/priority-13-17-migration-spec.json` | Not required |
| Local DTSX spec coverage gate | Script Task/loop/unknown 등 manual-review step이 readiness를 통과하지 못하게 차단 | Implemented; sample report `docs/dtsx-spec-coverage/sample-report.json`; current priority spec is `BLOCKED_MANUAL_REVIEW` with 17 manual-review steps | Not required |
| Local legacy SQL call adapter plan | DTSX SQL/SP 후보가 Spring Batch core 직접 JDBC가 아니라 `LegacyDbAdapter` 경계로 묶이는지 확인 | Implemented; sample report `docs/legacy-sql/sample-report.json`; 46 SQL candidates, 34 procedure candidates, 12 unresolved SQL candidates requiring manual adapter review | Not required |
| Local legacy SQL statement risk classification | unresolved SQL 후보를 SELECT/mutation/unknown으로 분류해 side-effect 검토 우선순위를 만든다 | Implemented; sample report records 3 SELECT, 9 mutation, 0 unknown unresolved SQL candidates | Not required |
| Local DTSX manual-review worklist | 17개 manual-review step을 Kotlin/Spring Batch 설계 work item으로 분해 | Implemented; runtime report `build/dtsx-manual-worklist/report.json`; 7 copy, 4 transcode, 2 cleanup, 1 partition writer, 3 generation items | Not required |
| Local manual operation services | copy/transcode/cleanup/partition/generation Script Task 및 loop 치환 기반 구현 | Implemented; copy verifies byte/SHA, transcode requires explicit charset/newline, cleanup defaults dry-run, partition writer requires split/naming rules, derived generator requires explicit delimited contract; covers all 17 manual-review worklist items as building blocks | Not required |
| Local manual operation Tasklet adapters | manual operation services를 Spring Batch Step 실행 단위로 연결 | Implemented; records operation status/counts in step execution context and fails step on blocking status | Not required |
| Local manual implementation coverage gate | 17개 manual-review work item이 구현된 Tasklet adapter 범주에 모두 매핑되는지 확인 | Implemented; actual priority 13-17 report `PASSED`, 17 work items, 17 implemented mappings, 0 unsupported | Not required |
| Local manual operation step plan | 17개 manual-review work item을 Spring Batch job/manual step/adapter method 계획으로 고정 | Implemented; actual priority 13-17 report `BLOCKED_G1`, 16 planned manual steps, 1 `NAVER_RANKING` step blocked until G1, 0 unsupported | Not required |
| Local integration exchange catalog | file-only가 아닌 partner integration contract model 확인 | Implemented; sample report `docs/exchange-catalog/sample-report.json`; 19 outbound file exchanges, `NAVER_RANKING` blocked, inbound/API non-file contracts representable without fileName | Not required |
| Local golden comparison harness | candidate/golden artifact byte/line/SHA comparison report 생성 | Implemented; sample report `docs/golden-comparison/sample-report.json` | Not required |
| Local contract format validation | expected files, encoding, newline, JSONL/XML/TSV 기본 포맷 검증 | Implemented; sample report `docs/contract-format/sample-report.json` | Not required |
| Local equivalence gate | 구조 검증, contract format, golden 비교가 모두 통과할 때만 동등성 인정 | Implemented; sample report `docs/equivalence/sample-equivalence-report.json` | Not required |
| Local G1 evidence pack validator | SQL Agent/DTSX/SP/golden/publish/runtime evidence shape 검증 | Implemented; synthetic sample report `docs/g1-evidence/sample-report.json` remains blocked | Not required |
| Local G1 read-only evidence request bundle | 승인 전 operator handoff용 필수 fragment/target/read-only query template/금지 액션 manifest 생성 | Generated: `docs/g1-evidence/request-bundle.json`; approvalRequired=true, 7 fragments, 7 targets, 4 read-only query templates, 6 forbidden actions | Not required |
| Local G1 approval packet | readiness blocker와 G1 request bundle을 승인용 decision artifact로 결합 | Generated: `docs/g1-evidence/approval-packet.json`; status=`APPROVAL_REQUIRED`, blocking gates=7, required fragments=7, target requests=7, read-only query ids=4, forbidden actions=6 | Not required |
| Local G1 import approval guard | operator-supplied evidence import가 승인 decision 없이 G1 통과 근거가 되지 않도록 차단 | Implemented; `--partner.integration.g1-import.require-approval=true` requires approval packet plus approved decision; committed decision template remains `PENDING` | Not required |
| Local G1 import approval readiness gate | readiness가 G1 validation pass뿐 아니라 승인된 import report까지 요구하도록 차단 | Implemented; sample readiness includes `G1_IMPORT_APPROVAL` blocked by `approvalDecisionStatus=PENDING` | Not required |
| Local G1 DTSX 후보 checksum 기준선 | 로컬 repo DTSX 후보와 운영 read-only export의 drift 비교 기준 | Implemented; build report `build/g1-evidence/local-dtsx-candidates-report.json`; 7 candidates found, 0 missing; validator conclusion is `BLOCKED_LOCAL_CANDIDATE` so it cannot prove G1 | Not required |
| Local G1 approval decision artifact | 사용자 승인 내용을 수동 JSON 편집 없이 build-only approval decision으로 생성 | Implemented; runner writes `build/g1-evidence/approval-decision-approved.json`, committed template remains `PENDING`, guarded local DTSX candidate import records `APPROVED_READ_ONLY_EXPORT` but validation remains `BLOCKED_LOCAL_CANDIDATE` | Not required |
| Local G1 operator export preflight | 실제 operator source-root import 전에 template/local 후보/누락 fragment를 차단 | Implemented; template source-root reports `BLOCKED_TEMPLATE_PLACEHOLDER`, local DTSX candidate source-root reports `BLOCKED_LOCAL_REPO_CANDIDATE`; only complete non-placeholder `READ_ONLY_EXPORT` reports `PASSED_READY_TO_IMPORT` | Not required |
| Local G1 operator preflight readiness gate | preflight를 migration readiness 필수 gate로 요구 | Implemented; sample readiness now has 11 gates and blocks `G1_OPERATOR_PREFLIGHT` with `BLOCKED_LOCAL_REPO_CANDIDATE` until real operator export source-root passes preflight | Not required |
| Local legacy SQL adapter plan readiness gate | unresolved SQL/SP adapter plan이 readiness를 우회하지 못하도록 차단 | Implemented; readiness includes `LEGACY_SQL_ADAPTER_PLAN`, currently blocked by `BLOCKED_UNRESOLVED_SQL` with 12 unresolved SQL candidates | Not required |
| Local G1 evidence template pack | 승인 후 operator가 채울 G1 read-only export skeleton 생성 | Generated: `docs/g1-evidence/template-pack.json`; validates as `FAILED` until real evidence replaces placeholders | Not required |
| Local G1 evidence directory importer | operator read-only export fragments를 단일 G1 pack으로 조립하고 validator 실행 | Implemented; guide `docs/g1-evidence/import-fragments.md`; runtime reports under `build/g1-evidence/` | Not required |
| Local G1 fragment template directory generator | operator가 채울 read-only export fragment file set 생성 | Implemented; runner writes 7 required fragments and blocks non-empty roots unless overwrite is explicit | Not required |
| Local publish/readback harness | local target에 publish 후 byte/SHA readback smoke 증거 생성 | Implemented; sample report `docs/publish-readback/sample-report.json` | Not required |
| Local smoke matrix runner | 13, 14, 16, 17 local skeleton 전체 실행과 15 blocked 상태를 단일 report로 검증 | Implemented; latest report `conclusion=PASSED`, 7 runnable targets, 1 blocked target, 19/19 artifacts, 7/7 contract-format targets passed | Not required |
| Local migration readiness bundle | smoke/DTSX coverage/legacy SQL plan/manual implementation/manual step plan/exchange catalog/G1/preflight/import approval/equivalence/publish-readback gate 상태를 단일 report로 묶음 | Implemented; sample report `docs/readiness/sample-report.json`; current sample has 11 gates and is `BLOCKED`; DTSX manual-review coverage now resolves only when manual implementation coverage and manual step plan are both `PASSED`, and current sample remains blocked by manual step plan G1 block, legacy SQL, G1, operator preflight, import approval, and golden evidence | Not required |
| Local domain run lock | 동일 feed/businessDate 동시 실행 차단 | Implemented; lock key `integrationId + businessDate`, local file-backed atomic create, listener release | Not required |
| Local rebuild/retransfer intent separation | rebuild와 retransfer 요청이 같은 generation path로 섞이지 않도록 차단 | Implemented; `forceRebuild`, `retransferArtifactId`, validator rules, retransfer preflight guard | Not required |
| Local manifest-based retransfer | 기존 validated artifact를 새 artifact 생성 없이 재전송 | Implemented; manifest artifact lookup, validation lookup, retransfer no-op generation, publish attempt records source artifact id | Not required |
| 운영 DTSX 배포본 | repo와 운영 drift 확인 | Missing | Required |
| SP definition for `Naver_*`, `NaverShop_*`, `GoogleShop_*`, `KakaoDaum_*` | side effect, output column, sort order 확인 | Missing | Required |
| Existing SSIS output golden files | byte-level equivalence 기준 | Missing | Required |
| Current publish/readback path access | v1 compatibility bridge 검증 | Missing | Required |
| Runtime account/secret/network allowlist | private 통신 실행 가능성 | Missing | Required |

## Equivalence Criteria

신규 batch가 SSIS와 동일하다고 인정하려면 각 feed/mode/businessDate별로 아래 근거가 필요하다.

- row count 일치 또는 허용 차이 사유 기록
- byte count/checksum 일치 또는 허용 차이 사유 기록
- encoding, newline, delimiter, escaping, null 표현, sort order 확인
- file name/fixed path/full-today naming 규칙 확인
- staging side effect 재실행 안전성 확인
- publish 전 검증 통과
- publish 후 readback smoke 통과
- local bridge smoke는 source/target byte count와 SHA-256 readback match를 기록
- manifest에 `runId`, `jobExecutionId`, `feedId`, `mode`, `businessDate`, `artifactId`, `sha256`, `rowCount`, `publishStatus`, `readbackStatus` 기록

## Open Decisions

- SQL Agent read-only 확인 승인 여부
- `partner-integration-batch` repo 생성 승인 여부
- JobRepository/manifest/artifact 저장소
- full/today를 별도 Job으로 둘지 JobParameter mode로 둘지
- row 15 exact scope
- feed-by-feed cutover vs bundled cutover
