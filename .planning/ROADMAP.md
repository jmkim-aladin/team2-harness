# Roadmap: IDC DB 이관 B2B SSIS 13-17 Spring Batch 전환

## Overview

**Phases:** 50
**v1 Requirements:** 24
**Coverage:** 24/24 mapped

### Phase 1: DTSX Evidence Lock
**Goal:** Excel 13-17번과 실제 운영 DTSX/package/job/schedule을 배치 명세 원천으로 확정한다.
**Mode:** mvp

**Requirements:** INV-01, INV-02, INV-03, INV-04

**Success Criteria:**
1. Excel row -> repo -> dtproj -> dtsx 후보 매핑표가 존재한다.
2. 각 DTSX의 Control Flow/Data Flow/SQL/SP/Script/File/Cleanup/Publish operation이 분류된다.
3. SQL Agent `msdb` read-only 확인 필요 항목과 승인 요청 목록이 정리된다.
4. row 15는 active package 확인 전까지 blocked로 표시된다.

### Phase 2: Spring Batch Architecture Baseline
**Goal:** DTSX 명세를 신규 별도 repo의 Spring Batch `Job/Step/Tasklet/Reader/Writer` 모델로 재설계할 공통 구조를 확정한다.
**Mode:** mvp

**Requirements:** ARCH-01, ARCH-02, ARCH-03, ARCH-04, BATCH-01, BATCH-02, BATCH-03, BATCH-04, OPS-01, OPS-02, OPS-04

**Success Criteria:**
1. 신규 repo `partner-integration-batch`의 소유 서비스, package/component boundary가 정의된다.
2. `LegacyDbAdapter` 경계와 typed method 규칙이 문서화된다.
3. feed contract, artifact store, manifest, validation, delivery bridge interface가 정의된다.
4. v1 delivery compatibility bridge와 post-migration delivery modernization이 분리된다.
5. JobRepository/manifest 저장소 후보와 운영 책임 결정 항목이 정리된다.

### Phase 3: Validation Harness Specification
**Goal:** 기존 SSIS와 신규 batch 동등성을 검증할 golden-file/shadow-run 기준을 정의한다.
**Mode:** mvp

**Requirements:** VAL-01, VAL-02, VAL-03

**Success Criteria:**
1. row count, byte count, checksum, aggregate total, reject count, duration 비교 기준이 정의된다.
2. encoding, newline, delimiter, escaping, null handling, sort order 검증 기준이 정의된다.
3. golden output 확보와 read-only DB/SP 확인 승인 gate가 정리된다.
4. rebuild와 retransfer 검증 경로가 분리된다.

### Phase 4: Feed Job Design And First Conversion Plan
**Goal:** feed별 Job 후보와 구현 순서를 확정하고 첫 vertical slice 계획을 만든다.
**Mode:** mvp

**Requirements:** FEED-01, FEED-02, FEED-03, FEED-04, FEED-05

**Success Criteria:**
1. `kakaoDaumFeedJob`을 첫 vertical slice로 선정하거나 대체 사유를 문서화한다.
2. NaverBook, NaverShopping, Google, Kakao/Daum feed별 Job/Step/output contract가 정의된다.
3. Google split 기준과 row 15 scope는 확인 필요 항목으로 분리된다.
4. full/today mode를 별도 Job으로 둘지 JobParameter로 둘지 결정한다.

### Phase 5: Shadow Run And Operational Hardening
**Goal:** 신규 batch 후보를 기존 SSIS와 병행 검증하고 운영 재시작/재전송/rollback 기준을 갖춘다.
**Mode:** mvp

**Requirements:** VAL-04, OPS-03

**Success Criteria:**
1. shadow run은 partner-facing final path가 아니라 isolated candidate area를 사용한다.
2. 각 run에 manifest, audit log, checksum, row count, duration, publish/readback status가 남는다.
3. 실패 지점별 restart, rerun, retransfer 절차가 문서화된다.
4. SSIS schedule restore rollback 절차가 문서화된다.

### Phase 6: Incremental Cutover Plan
**Goal:** feed/job 단위로 사람 승인 후 SSIS에서 Spring Batch로 전환하는 cutover 계획을 만든다.
**Mode:** mvp

**Requirements:** OPS-03, OPS-04

**Success Criteria:**
1. feed별 cutover gate, owner, backup owner, rollback owner가 지정된다.
2. production schedule disable/enable 절차가 승인 전 단계와 승인 후 단계로 분리된다.
3. validation report와 rollback rehearsal 없이는 cutover가 불가능하도록 checklist가 정의된다.
4. partner-visible 계약 변경이 없음을 v1 release note에 명시한다.

### Phase 7: Post-Migration Delivery Modernization
**Goal:** DB 이관 후 파일 제공 방식을 별도 프로젝트/phase로 재설계한다.
**Mode:** mvp

**Requirements:** DELIV-01, DELIV-02, DELIV-03

**Success Criteria:**
1. private web endpoint, SFTP/FTPS, S3+CloudFront 계열 후보가 비교된다.
2. retention lifecycle, partner communication, DNS/URL/protocol 변경 영향이 별도 승인 항목으로 분리된다.
3. v1 migration cutover와 delivery modernization release가 섞이지 않는다.

### Phase 8: Repo Skeleton Implementation
**Goal:** 신규 Kotlin Spring Batch repo를 생성하고 첫 Kakao/Daum local vertical slice를 구현한다.
**Mode:** mvp

**Requirements:** ARCH-01, ARCH-02, ARCH-03, BATCH-01, BATCH-02, FEED-05, OPS-01, VAL-04

**Success Criteria:**
1. `/Users/jm/Documents/workspace/b2b/partner-integration-batch` repo skeleton이 존재한다.
2. Spring Boot 4.1.x, Spring Batch 6.0.x, Kotlin 2.2.x 기준으로 빌드된다.
3. `kakaoDaumFeedJob` local shadow flow가 실행된다.
4. 여섯 Kakao/Daum XML artifact와 manifest ledger가 생성된다.
5. golden comparison이 없으면 SSIS 동등성 완료를 주장하지 않는다.

### Phase 9: Feed Skeleton Expansion
**Goal:** 우선 대상 13, 14, 16, 17의 local Spring Batch skeleton을 실행 가능하게 만들고 15는 G1 blocked로 명시한다.
**Mode:** mvp

**Requirements:** FEED-01, FEED-02, FEED-03, FEED-04, FEED-05, BATCH-01, VAL-04

**Success Criteria:**
1. `naverBookFeedJob` FULL/TODAY local smoke가 성공한다.
2. `naverShoppingFeedJob` FULL/TODAY local smoke가 성공한다.
3. `googleShoppingFeedJob` FULL/TODAY local smoke가 성공한다.
4. `kakaoDaumFeedJob` FULL local smoke가 성공한다.
5. `naverRankingFeedJob`은 G1 전 실행 차단된다.
6. local smoke artifact 19개와 manifest run 7개가 생성된다.

### Phase 10: DTSX Inventory Extractor
**Goal:** 로컬 DTSX XML에서 package, connection manager, executable, SQL/SP 후보를 추출해 Spring Batch 재설계 근거 JSON을 만든다.
**Mode:** mvp

**Requirements:** INV-01, INV-02, INV-03

**Success Criteria:**
1. Kotlin read-only DTSX parser가 존재한다.
2. 우선 대상 13-17 DTSX 후보 inventory JSON이 생성된다.
3. package별 connection/task/SQL 후보 count가 검증된다.
4. connection password 원문이 inventory에 남지 않는다.
5. G1 전까지 SQL Agent canonical/equivalence 완료를 주장하지 않는다.

### Phase 11: Control Flow Evidence Extraction
**Goal:** DTSX inventory에 variables와 precedence constraints를 추가해 Spring Batch transition 설계 근거를 강화한다.
**Mode:** mvp

**Requirements:** INV-02, INV-03

**Success Criteria:**
1. DTSX variable name/value/expression이 inventory에 포함된다.
2. precedence constraint `from`/`to` edge가 inventory에 포함된다.
3. 우선 대상 13-17 inventory JSON이 tracked docs 위치에 생성된다.
4. parser 테스트와 inventory 재생성이 통과한다.
5. G1 전까지 active deployment/equivalence 완료를 주장하지 않는다.

### Phase 12: Spring Batch Spec Generation
**Goal:** DTSX inventory를 Spring Batch Job/Flow/Tasklet/Chunk Step 전환 명세로 변환한다.
**Mode:** mvp

**Requirements:** BATCH-01, INV-02, INV-03

**Success Criteria:**
1. DTSX executable type이 operation type으로 분류된다.
2. precedence constraints 기반 step transition 후보가 생성된다.
3. Spring Batch mapping 후보가 `JOB`, `FLOW`, `TASKLET_JDBC`, `CHUNK_STEP`, `TASKLET_KOTLIN_SERVICE`, `PARTITION_OR_DECIDER`로 기록된다.
4. Script Task/loop/unknown은 manual review로 표시된다.
5. 우선 대상 13-17 migration spec JSON이 tracked docs 위치에 생성된다.

### Phase 13: Golden Comparison Harness
**Goal:** Spring Batch candidate output과 SSIS golden output을 비교할 byte/count/checksum 검증 도구를 구현한다.
**Mode:** mvp

**Requirements:** VAL-01, VAL-02, VAL-03

**Success Criteria:**
1. candidate/golden 디렉터리 비교 report model이 존재한다.
2. byte count, line count, SHA-256, missing file, checksum mismatch가 기록된다.
3. missing golden/candidate가 있으면 equivalence pass가 아니라 blocked로 기록된다.
4. command-line runner로 JSON report를 생성할 수 있다.
5. 샘플 report와 테스트가 통과한다.

### Phase 14: Equivalence Gate
**Goal:** 구조 검증과 golden 비교가 모두 통과할 때만 SSIS 동등성을 인정하는 최종 gate를 구현한다.
**Mode:** mvp

**Requirements:** VAL-01, VAL-02, VAL-03

**Success Criteria:**
1. `ValidationReport`와 `GoldenComparisonReport`를 결합한 equivalence report model이 존재한다.
2. 구조 검증 pass + golden pass일 때만 `EQUIVALENT`가 나온다.
3. golden report 누락/미완료는 `BLOCKED`로 남는다.
4. checksum/content mismatch는 `NOT_EQUIVALENT`로 남는다.
5. command-line runner와 sample report가 검증된다.

### Phase 15: Contract Format Validation
**Goal:** expected file contract의 기본 포맷을 검증하고 final equivalence gate에 포함한다.
**Mode:** mvp

**Requirements:** VAL-03

**Success Criteria:**
1. integration/mode/businessDate 기준 expected files가 검증된다.
2. encoding decode, newline, JSONL parse, XML well-formedness, TSV separator 기준이 검증된다.
3. contract-format JSON report가 생성된다.
4. final equivalence gate가 contract-format pass도 요구한다.
5. 샘플 report와 테스트가 통과한다.

### Phase 16: G1 Evidence Pack Validation
**Goal:** SQL Agent, 운영 DTSX, SP definition, golden output, publish/readback, runtime/network evidence를 오프라인 evidence pack으로 검증한다.
**Mode:** mvp

**Requirements:** INV-04, VAL-01, VAL-02, OPS-04

**Success Criteria:**
1. G1 evidence pack model이 존재한다.
2. runnable feed/mode 대상별 SQL Agent, deployed DTSX, SP definition, golden output, publish target evidence가 검증된다.
3. runtime account/private network/secret source evidence가 검증된다.
4. synthetic sample pack은 pass가 아니라 blocked로 남는다.
5. 샘플 report와 테스트가 통과한다.

### Phase 17: Local Publish Readback Harness
**Goal:** v1 compatibility bridge의 로컬 publish/readback smoke를 구현해 산출물 전달 무결성 증거를 원장에 추가한다.
**Mode:** mvp

**Requirements:** ARCH-04, VAL-04, OPS-01

**Success Criteria:**
1. local source root -> local target root publish/readback runner가 존재한다.
2. readback은 byte count와 SHA-256으로 검증된다.
3. source missing, no files, copy/readback mismatch가 pass로 처리되지 않는다.
4. sample source/report가 생성되고 민감정보가 포함되지 않는다.
5. 전체 테스트와 sample runner가 통과한다.

### Phase 18: G1 Evidence Template Generation
**Goal:** G1 승인 직후 read-only export를 빠짐없이 채울 수 있는 evidence pack template generator를 구현한다.
**Mode:** mvp

**Requirements:** INV-04, VAL-01, VAL-02, OPS-04

**Success Criteria:**
1. G1 required target 목록을 validator와 template generator가 공유한다.
2. template generator가 모든 required integration/mode의 SQL Agent, deployed DTSX, SP, golden output, publish target, runtime evidence placeholder를 만든다.
3. template은 `READ_ONLY_EXPORT` shape이지만 placeholder 상태에서는 validator를 통과하지 않는다.
4. command-line runner와 deterministic sample template이 생성된다.
5. 전체 테스트와 template validation check가 통과한다.

### Phase 19: G1 Evidence Directory Import
**Goal:** operator가 제공한 read-only export fragment directory를 단일 G1 evidence pack으로 조립하고 기존 validator로 검증한다.
**Mode:** mvp

**Requirements:** INV-04, VAL-01, VAL-02, OPS-04

**Success Criteria:**
1. 고정 fragment 파일명 계약이 문서화된다.
2. importer가 fragment directory를 `G1EvidencePack`으로 조립한다.
3. 필수 fragment 누락 시 pack을 쓰기 전에 실패하고 import report를 남긴다.
4. import runner가 validation report와 import report를 생성한다.
5. 전체 테스트와 template fragment import sample check가 통과한다.

### Phase 20: G1 Fragment Template Directory Generation
**Goal:** operator가 채울 수 있는 G1 read-only evidence fragment template directory를 앱에서 직접 생성한다.
**Mode:** mvp

**Requirements:** INV-04, VAL-01, VAL-02, OPS-04

**Success Criteria:**
1. fragment writer가 `G1EvidencePack`을 필수 fragment 파일 7개로 분리해 쓴다.
2. non-empty output root는 명시 overwrite 없이는 차단된다.
3. fragment template runner가 deterministic businessDate/evidencePackId/capturedAt 입력을 지원한다.
4. 생성된 fragment template directory는 importer로 round-trip 가능하다.
5. 전체 테스트와 runner round-trip check가 통과한다.

### Phase 21: Domain Run Lock
**Goal:** 동일 feed/businessDate의 동시 실행을 차단하는 Spring Batch domain lock을 구현한다.
**Mode:** mvp

**Requirements:** OPS-02, OPS-01

**Success Criteria:**
1. lock key는 `integrationId + businessDate`로 정의된다.
2. local file-backed repository가 atomic create로 중복 lock을 거부한다.
3. job flow가 artifact generation 전에 lock을 획득한다.
4. job 종료 시 listener가 lock을 release한다.
5. lock repository tests, listener test, local job smoke, 전체 테스트가 통과한다.

### Phase 22: Rebuild Retransfer Intent Separation
**Goal:** rebuild와 retransfer 요청이 같은 generate path로 섞이지 않도록 JobParameters와 preflight gate를 분리한다.
**Mode:** mvp

**Requirements:** BATCH-02, BATCH-03, OPS-03

**Success Criteria:**
1. `forceRebuild`와 `retransferArtifactId` JobParameter가 파싱된다.
2. `runPurpose=RETRANSFER`는 `retransferArtifactId` 없이는 거부된다.
3. `retransferArtifactId`는 non-`RETRANSFER` run에서 거부된다.
4. `forceRebuild`와 `retransferArtifactId` 동시 사용은 거부된다.
5. retransfer 요청은 artifact generation 전에 실패해 새 artifact를 생성하지 않는다.
6. 전체 테스트와 rebuild/retransfer local smoke가 통과한다.

### Phase 23: Manifest Based Retransfer
**Goal:** `runPurpose=RETRANSFER`가 새 artifact를 생성하지 않고 기존 validated artifact를 manifest에서 찾아 publish 경로로 넘기도록 구현한다.
**Mode:** mvp

**Requirements:** BATCH-03, OPS-03, OPS-01

**Success Criteria:**
1. manifest repository가 artifact id와 validation report를 조회할 수 있다.
2. retransfer는 generation step에서 새 artifact를 생성하지 않는다.
3. retransfer source artifact는 integration/mode/businessDate/contractVersion과 passed validation report가 맞아야 한다.
4. publish attempt는 retransfer runId와 원본 artifactId를 기록한다.
5. publish disabled 상태에서는 안전하게 실패하고, local smoke에서는 compatibility publish enabled로 성공 검증한다.
6. 전체 테스트와 retransfer success smoke가 통과한다.

### Phase 24: Local Smoke Matrix Runner
**Goal:** 우선 대상 local skeleton 전체를 한 번에 실행하고 13, 14, 16, 17 artifact count와 15 blocked 상태를 JSON report로 증명한다.
**Mode:** mvp

**Requirements:** FEED-01, FEED-02, FEED-03, FEED-04, FEED-05, VAL-04

**Success Criteria:**
1. local smoke matrix runner가 7개 runnable target을 순차 실행한다.
2. `naverBookFeedJob`, `naverShoppingFeedJob`, `googleShoppingFeedJob`, `kakaoDaumFeedJob` 결과가 report에 남는다.
3. expected artifact count 19와 actual artifact count 19가 일치한다.
4. `naverRankingFeedJob`은 G1 전 `BLOCKED_EXPECTED`로 기록되고 실행하지 않는다.
5. runner는 `golden-comparison-required=false`일 때만 실행되어 local smoke와 SSIS equivalence를 혼동하지 않는다.
6. 전체 테스트와 실제 bootRun matrix smoke가 통과한다.

### Phase 25: Local Smoke Contract Gate
**Goal:** local smoke matrix가 artifact count뿐 아니라 runnable target별 contract-format validation까지 통과해야 `PASSED`가 되도록 강화한다.
**Mode:** mvp

**Requirements:** VAL-03, VAL-04, FEED-01, FEED-02, FEED-03, FEED-05

**Success Criteria:**
1. local smoke target result에 contract-format report id와 conclusion이 기록된다.
2. runnable target은 artifact count와 contract-format validation이 모두 통과해야 `PASSED`가 된다.
3. matrix report에 `contractFormatPassedTargetCount`가 기록된다.
4. 실제 bootRun matrix에서 7개 runnable target의 contract-format validation이 모두 `PASSED`가 된다.
5. 전체 테스트와 실제 bootRun matrix smoke가 통과한다.

### Phase 26: Migration Readiness Bundle
**Goal:** local smoke, G1 evidence, equivalence, local publish/readback report를 하나로 묶어 SSIS 이관 readiness 상태를 명시한다.
**Mode:** mvp

**Requirements:** VAL-01, VAL-02, VAL-03, VAL-04, OPS-01, OPS-04

**Success Criteria:**
1. readiness report model이 존재한다.
2. local smoke, G1 evidence, equivalence, local publish/readback report가 gate result로 요약된다.
3. 누락/blocked evidence는 `READY_FOR_SHADOW_RUN`으로 처리되지 않는다.
4. sample-only G1과 missing golden comparison은 `BLOCKED`로 남는다.
5. readiness tests, 실제 bootRun readiness smoke, 전체 테스트가 통과한다.

### Phase 27: DTSX Spec Coverage Gate
**Goal:** DTSX migration spec의 manual-review/unknown/loop/script step이 readiness를 우회하지 못하도록 coverage gate를 추가한다.
**Mode:** mvp

**Requirements:** INV-02, INV-03, BATCH-01, VAL-03, VAL-04

**Success Criteria:**
1. DTSX spec coverage report model이 존재한다.
2. package별 total/mapped/manual-review step count가 기록된다.
3. manual-review step이 남으면 coverage는 `PASSED`가 아니라 blocked가 된다.
4. readiness bundle이 DTSX spec coverage report를 필수 gate로 요구한다.
5. focused tests, 실제 coverage/readiness bootRun, 전체 테스트가 통과한다.

### Phase 28: DTSX Manual Review Worklist
**Goal:** coverage blocker인 17개 manual-review DTSX step을 Kotlin/Spring Batch 설계 work item으로 분해한다.
**Mode:** mvp

**Requirements:** INV-02, INV-03, BATCH-01, BATCH-02, VAL-04

**Success Criteria:**
1. manual-review worklist report model이 존재한다.
2. Script/copy/Unicode/cleanup/loop/make step이 권장 resolution type으로 분류된다.
3. work item별 target component name과 required evidence가 기록된다.
4. 실제 priority 13-17 spec에서 17개 work item이 생성된다.
5. focused tests와 실제 worklist bootRun이 통과한다.

### Phase 29: Manual File Operation Building Blocks
**Goal:** copy/transcode/cleanup manual-review work item을 뒷받침할 로컬 Kotlin 서비스를 구현한다.
**Mode:** mvp

**Requirements:** BATCH-01, BATCH-02, VAL-02, VAL-04, OPS-01

**Success Criteria:**
1. artifact copy operation이 relative path와 overwrite 정책을 검증하고 byte/SHA readback을 확인한다.
2. encoding transcode operation이 source/target charset과 newline 정책을 명시적으로 처리한다.
3. retention cleanup operation이 explicit relative path와 cutoff를 사용하며 dry-run을 기본값으로 둔다.
4. focused tests와 전체 테스트가 통과한다.
5. production/partner-facing endpoint에는 접근하지 않는다.

### Phase 30: Partitioned Multi-File Writer
**Goal:** Google TSV split loop manual-review work item을 뒷받침할 로컬 Kotlin writer 서비스를 구현한다.
**Mode:** mvp

**Requirements:** BATCH-01, BATCH-02, VAL-02, VAL-04, OPS-01

**Success Criteria:**
1. partitioned writer가 partition key와 deterministic file naming rule을 요구한다.
2. max-record 또는 max-byte split rule로 여러 파일을 생성한다.
3. overwrite, symlink, path escape, invalid record를 차단한다.
4. 생성 파일별 byte/SHA readback stats를 기록한다.
5. focused tests와 전체 테스트가 통과한다.

### Phase 31: Derived File Generation Building Block
**Goal:** NaverShop derived-file-generation manual-review work item 3건을 뒷받침할 로컬 Kotlin 서비스를 구현한다.
**Mode:** mvp

**Requirements:** BATCH-01, BATCH-02, VAL-02, VAL-04, OPS-01

**Success Criteria:**
1. derived generator가 source name과 target file contract를 명시적으로 요구한다.
2. field count, delimiter, newline, charset, null token 규칙을 적용한다.
3. overwrite, symlink, invalid field value를 차단한다.
4. 생성 파일의 byte/SHA readback stats를 기록한다.
5. focused tests와 전체 테스트가 통과한다.

### Phase 32: Manual Operation Tasklet Adapters
**Goal:** manual operation building block을 Spring Batch Tasklet 실행 단위로 연결한다.
**Mode:** mvp

**Requirements:** BATCH-01, BATCH-02, VAL-02, VAL-04, OPS-01

**Success Criteria:**
1. copy/transcode/cleanup/partition/generation operation이 Tasklet으로 실행 가능하다.
2. operation status, file count, record count, byte count가 step execution context에 기록된다.
3. blocking operation status는 step failure로 전파된다.
4. focused tests와 전체 테스트가 통과한다.
5. production/partner-facing endpoint에는 접근하지 않는다.

### Phase 33: Manual Implementation Coverage Gate
**Goal:** 17개 DTSX manual-review work item이 모두 구현된 Tasklet adapter 범주에 매핑되는지 report로 검증한다.
**Mode:** mvp

**Requirements:** INV-03, BATCH-01, BATCH-02, VAL-04

**Success Criteria:**
1. manual implementation coverage report model이 존재한다.
2. worklist resolution별 `ManualOperationTasklets` method 매핑이 기록된다.
3. unsupported resolution이 있으면 coverage는 passed가 아니라 blocked가 된다.
4. 실제 priority 13-17 worklist에서 17/17 implemented, 0 unsupported가 확인된다.
5. focused tests, 실제 runner, 전체 테스트가 통과한다.

### Phase 34: Integration Exchange Contract Catalog
**Goal:** file-only가 아닌 partner integration exchange 모델을 로컬 계약 catalog로 구현한다.
**Mode:** mvp

**Requirements:** ARCH-03, ARCH-04, FEED-01, FEED-05, OPS-01

**Success Criteria:**
1. 현재 우선 대상 runnable output 19개가 outbound file exchange contract로 기록된다.
2. `NAVER_RANKING`은 G1 전 blocked integration으로 남는다.
3. inbound/API 같은 non-file exchange contract가 fileName 없이 표현된다.
4. exchange catalog JSON report runner가 존재한다.
5. focused tests, 실제 runner, 전체 테스트가 통과한다.

### Phase 35: Exchange Catalog Readiness Gate
**Goal:** migration readiness bundle이 exchange catalog를 필수 gate로 요구하게 만들어 file-only readiness 회귀를 차단한다.
**Mode:** mvp

**Requirements:** ARCH-03, ARCH-04, VAL-03, VAL-04, OPS-01

**Success Criteria:**
1. readiness gate 목록에 `EXCHANGE_CATALOG`가 추가된다.
2. exchange catalog report가 누락되면 readiness는 `BLOCKED`로 남는다.
3. exchange catalog가 empty 또는 file-only이면 readiness는 `BLOCKED`로 남는다.
4. 유효한 exchange catalog는 19개 contract와 1개 blocked integration을 통과 gate로 기록한다.
5. focused tests, 실제 readiness runner, 전체 테스트가 통과한다.

### Phase 36: Manual Implementation Readiness Gate
**Goal:** migration readiness bundle이 DTSX manual implementation coverage를 필수 gate로 요구하게 만들어 17개 manual-review work item 구현 범위가 readiness에 직접 드러나게 한다.
**Mode:** mvp

**Requirements:** INV-03, BATCH-01, BATCH-02, VAL-04

**Success Criteria:**
1. readiness gate 목록에 `DTSX_MANUAL_IMPLEMENTATION`이 추가된다.
2. manual implementation coverage report가 누락되면 readiness는 `BLOCKED`로 남는다.
3. unsupported resolution이 있으면 readiness는 `BLOCKED`로 남는다.
4. `FAILED_EMPTY_WORKLIST`는 readiness failure로 처리된다.
5. 실제 readiness runner가 local smoke/manual implementation/exchange catalog/local publish-readback 4개 passed gate와 DTSX spec/G1/equivalence 3개 blocked gate를 기록한다.
6. focused tests, 실제 readiness runner, 전체 테스트가 통과한다.

### Phase 37: DTSX Manual Operation Step Plan
**Goal:** 17개 DTSX manual-review work item을 Spring Batch job/manual step/adapter method 계획으로 고정하고, G1 전 row 15 관련 step은 blocked evidence로 분리한다.
**Mode:** mvp

**Requirements:** INV-03, BATCH-01, BATCH-02, FEED-01, FEED-02, FEED-03, FEED-04, FEED-05

**Success Criteria:**
1. manual-review worklist를 입력으로 받아 step plan report를 생성한다.
2. 각 work item은 `jobName`, `plannedStepName`, `adapterMethodName`, `integrationId`, `mode`를 가진다.
3. `NAVER_RANKING` 관련 work item은 G1 전 `BLOCKED_G1`로 기록된다.
4. unknown package 또는 unsupported resolution은 pass가 아니라 blocked로 기록된다.
5. 실제 priority 13-17 worklist에서 16개 planned step과 1개 G1 blocked step이 기록된다.
6. focused tests, 실제 runner, 전체 테스트가 통과한다.

### Phase 38: Manual Step Plan Readiness Gate
**Goal:** migration readiness bundle이 DTSX manual operation step plan report를 필수 gate로 요구하게 만들어 manual step wiring 계획 없는 readiness 회귀를 차단한다.
**Mode:** mvp

**Requirements:** INV-03, BATCH-01, BATCH-02, VAL-04, OPS-04

**Success Criteria:**
1. readiness gate 목록에 `DTSX_MANUAL_STEP_PLAN`이 추가된다.
2. manual step plan report가 누락되면 readiness는 `BLOCKED`로 남는다.
3. `PASSED` step plan은 planned/blocked/unsupported count를 통과 gate로 기록한다.
4. `BLOCKED_G1` step plan은 readiness `BLOCKED`로 남고 row 15 G1 blocker를 메시지로 기록한다.
5. unsupported mapping은 readiness `BLOCKED`, empty worklist는 readiness failure로 처리된다.
6. 실제 readiness runner가 8 gates, 4 passed, 4 blocked를 기록한다.
7. focused tests, 실제 readiness runner, 전체 테스트가 통과한다.

### Phase 39: G1 Read-only Evidence Request Bundle
**Goal:** G1 승인 전 운영자에게 전달할 read-only evidence 수집 요청 bundle을 코드로 생성해, 수집 대상/금지 액션/필수 fragment/import command를 기계 검증 가능한 형태로 고정한다.
**Mode:** mvp

**Requirements:** INV-03, VAL-04, OPS-04

**Success Criteria:**
1. G1 request bundle은 approvalRequired=true와 READ_ONLY_OPERATOR_EXPORT 모드를 기록한다.
2. bundle은 필수 fragment 7개와 G1 required target 7개를 모두 포함한다.
3. bundle은 SQL Agent, SP definition, deployed DTSX checksum, golden output checksum용 read-only query template을 포함한다.
4. bundle은 DB write, SQL Agent disable/schedule change, DTSX execution, partner publish, prod file modification 금지 액션을 명시한다.
5. command runner가 `--partner.integration.g1-request.*` 옵션으로 deterministic JSON을 생성한다.
6. focused tests, 실제 runner, 전체 테스트가 통과한다.

### Phase 40: G1 Approval Packet
**Goal:** 현재 readiness blocker와 G1 request bundle을 하나의 승인용 decision artifact로 묶어, G1 read-only evidence 수집 승인 전후 경계를 명확히 한다.
**Mode:** mvp

**Requirements:** INV-03, VAL-04, OPS-04

**Success Criteria:**
1. approval packet model이 readiness report id/conclusion, blocking gates, request id, required fragment count, target request count, read-only query ids, forbidden actions를 기록한다.
2. blocked readiness 또는 approvalRequired request bundle은 `APPROVAL_REQUIRED`로 남는다.
3. command runner가 `--partner.integration.g1-approval.*` 옵션으로 readiness report와 request bundle을 읽어 deterministic JSON을 생성한다.
4. sample approval packet `docs/g1-evidence/approval-packet.json`은 4 blocking gates, 7 fragments, 7 targets, 4 read-only query ids, 6 forbidden actions를 기록한다.
5. approval packet 생성은 SQL Server, SQL Agent, DTSX 실행, FTP, SMB, HTTP, API, production endpoint에 접속하지 않는다.
6. focused tests, 실제 runner, G1 focused suite, 전체 테스트가 통과한다.

### Phase 41: G1 Import Approval Guard
**Goal:** operator-supplied G1 evidence fragment import가 승인 decision 없이 G1 통과 근거로 쓰이지 않도록 import guard를 추가한다.
**Mode:** mvp

**Requirements:** INV-03, VAL-04, OPS-04

**Success Criteria:**
1. `G1ApprovalDecision` model이 approval packet id, request id, decision status, approver, approvedAt, allowed query ids, acknowledged forbidden actions를 기록한다.
2. import guard가 켜져 있으면 approval packet과 approval decision이 없을 때 pack write 전 실패한다.
3. approval decision은 `APPROVED_READ_ONLY_EXPORT`, matching packet/request ids, all read-only query ids allowed, all forbidden actions acknowledged 조건을 만족해야 한다.
4. import report가 approval packet id/request id/decision status를 기록한다.
5. committed approval decision template은 `PENDING` 상태라 guard에서 승인으로 인정되지 않는다.
6. focused tests, G1 focused suite, 전체 테스트가 통과한다.

### Phase 42: G1 Import Approval Readiness Gate
**Goal:** migration readiness가 G1 validation report뿐 아니라 승인된 G1 import report까지 요구하게 만들어 승인 guard 우회를 차단한다.
**Mode:** mvp

**Requirements:** VAL-04, OPS-04

**Success Criteria:**
1. readiness gate 목록에 `G1_IMPORT_APPROVAL`이 추가된다.
2. G1 validation이 `PASSED`여도 G1 import report가 없으면 readiness는 `BLOCKED`로 남는다.
3. G1 import report가 `APPROVED_READ_ONLY_EXPORT` decision 없이 생성됐으면 readiness는 `BLOCKED`로 남는다.
4. `PACK_WRITTEN_VALIDATION_PASSED` + `G1EvidenceConclusion.PASSED` + approved decision metadata가 있을 때만 G1 import approval gate가 통과한다.
5. command runner가 `--partner.integration.readiness.g1-import-report` 입력을 받는다.
6. sample readiness report는 9 gates, 4 passed, 5 blocked를 기록한다.
7. focused tests, actual readiness runner, full tests가 통과한다.

## Decision Gates

| Gate | Decision | Needed Before |
|------|----------|---------------|
| G1 | SQL Agent `msdb`, 운영 DTSX, SP definition, golden output read-only 확인 승인 | Phase 1 completion |
| G2 | `partner-integration-batch` repo 생성 방식, JobRepository/manifest/artifact 저장소 결정 | Phase 2 completion |
| G3 | full/today job split vs mode parameter 결정 | Phase 4 completion |
| G4 | row 15 exact scope 결정 | row 15 design/implementation |
| G5 | feed별 production cutover 승인 | Phase 6 execution |

## Next Phase

Phase 50 G1 operator preflight readiness gate는 b2b commit `e904cb9`까지 로컬 완료됐다. 현재 로컬 증거는 skeleton job, contract-format validation을 포함한 one-command smoke matrix, DTSX structural inventory, Spring Batch mapping 후보, 46개 SQL 후보/34개 stored procedure 후보/12개 미해석 SQL 후보를 기록하는 legacy SQL call adapter plan, 해당 legacy SQL plan readiness gate, 17개 manual-review step이 있는 DTSX spec coverage, copy/transcode/cleanup/partition/generation work item으로 분해한 manual-review worklist, 17개 manual-review 범주를 처리하는 local service, Spring Batch Tasklet adapter, 17/17 work item 통과 manual implementation coverage report, manual implementation readiness gate, 16개 실행 가능 work item과 1개 G1 차단 `NAVER_RANKING` work item을 기록하는 manual operation job/step/adapter plan, manual step plan readiness gate, manual implementation coverage와 manual step plan이 모두 `PASSED`일 때만 DTSX manual-review coverage blocker를 해소하는 readiness bridge, 7/7 local repo package의 `LOCAL_REPO_CANDIDATE` DTSX checksum fragment 생성, build-only G1 approval decision 생성, approval guard는 통과하지만 `BLOCKED_LOCAL_CANDIDATE`로 남는 local candidate import, G1 operator source-root preflight, G1 operator preflight readiness gate, file-compatible but non-file-only exchange contract catalog, exchange catalog readiness gate, contract-format validation, golden comparison, final equivalence decision gate, offline G1 evidence-pack 검증, G1 request bundle 생성, G1 approval packet 생성, G1 import approval guard, G1 import approval readiness gate, local publish/readback smoke, fill-in G1 evidence pack 생성, directory-fragment import, operator용 fragment template directory 생성, 동일 feed/businessDate run lock, rebuild/retransfer parameter 분리, artifact 재생성 없는 manifest-based retransfer까지 포함한다. 단일 readiness report는 SQL Agent active package, SP definition, golden output, 실제 operator preflight 통과, 실제 G1 import approval, shadow-run equivalence가 확보될 때까지 11개 gate 기준 `BLOCKED`로 남는다. DB/SP/SQL Agent/prod write, partner-facing publish, schedule 변경, delivery modernization, YouTrack/KB update, push, PR은 수행하지 않았다. Git repo는 사용자 명시 지시로 `main`에 초기화됐고 b2b 로컬 커밋은 작은 단위로 유지 중이다. 다음 단계는 실제 operator `READ_ONLY_EXPORT` fragment source-root를 받아 preflight 통과 후 SQL Agent/SP/golden/publish/runtime evidence를 import하는 것이다.

### Phase 43: Legacy SQL call adapter plan

**Goal:** DTSX SQL/SP 후보를 신규 Spring Batch core 밖의 `LegacyDbAdapter` 호출 계획으로 고정하고, 미해석 SQL 후보가 readiness를 우회하지 못하게 로컬 report를 생성한다.
**Mode:** mvp

**Requirements:** SPEC-03, VAL-04, OPS-04
**Depends on:** Phase 42

**Success Criteria:**
1. `docs/dtsx-spec/priority-13-17-migration-spec.json`에서 SQL 후보가 있는 step을 모두 수집한다.
2. `exec`/`execute` stored procedure 후보는 procedure name과 argument text를 추출한다.
3. 각 SQL 후보는 `LegacyDbAdapter` boundary plan으로 기록되고 core 직접 JDBC 호출로 간주되지 않는다.
4. `select`/미해석 SQL 후보는 `requiresManualAdapterReview=true`로 남겨 readiness 우회를 막는다.
5. command runner가 `--partner.integration.legacy-sql-plan.*` 입력/출력 옵션으로 deterministic JSON report를 생성한다.
6. sample report는 SQL 후보 count, procedure call count, unresolved SQL count, package별 breakdown을 기록한다.
7. focused tests, actual runner, full tests가 통과한다.

**Plans:** 1 plan

Plans:
- [x] 43-1 Legacy SQL call adapter plan generator and runner

### Phase 44: Legacy SQL adapter plan readiness gate

**Goal:** migration readiness가 legacy SQL adapter plan report를 필수 gate로 요구하게 만들어 unresolved SQL 후보가 readiness를 우회하지 못하게 한다.
**Mode:** mvp

**Requirements:** SPEC-03, VAL-04, OPS-04
**Depends on:** Phase 43

**Success Criteria:**
1. readiness gate 목록에 `LEGACY_SQL_ADAPTER_PLAN`이 추가된다.
2. legacy SQL plan report가 누락되면 readiness는 `BLOCKED`로 남는다.
3. `BLOCKED_UNRESOLVED_SQL` plan은 readiness `BLOCKED`로 남고 unresolved/procedure count를 메시지로 기록한다.
4. `LegacySqlCallPlanConclusion.PASSED` plan만 readiness 통과 gate로 인정된다.
5. command runner가 `--partner.integration.readiness.legacy-sql-plan-report` 입력을 받는다.
6. sample readiness report는 10 gates, 4 passed, 6 blocked를 기록한다.
7. focused tests, actual readiness runner, approval packet regeneration, full tests가 통과한다.

**Plans:** 1 plan

Plans:
- [x] 44-1 Legacy SQL adapter plan readiness gate

### Phase 45: Legacy SQL statement risk classification

**Goal:** legacy SQL adapter plan의 unresolved SQL을 SELECT, mutation, unknown risk kind로 분류해 G1/SP 검토와 adapter 설계 우선순위를 명확히 한다.
**Mode:** mvp

**Requirements:** SPEC-03, VAL-04, OPS-04
**Depends on:** Phase 44

**Success Criteria:**
1. `LegacySqlStatementKind`가 stored procedure, select query, data mutation, unknown을 표현한다.
2. 각 SQL call plan item이 `statementKind`를 기록한다.
3. report와 package summary가 SELECT/mutation/unknown count를 기록한다.
4. mutation SQL은 side-effect/idempotency review 메시지를 남긴다.
5. SELECT SQL은 adapter mapping 전 review 메시지를 남긴다.
6. sample report는 46 SQL candidates, 34 SP, 12 unresolved, 3 SELECT, 9 mutation, 0 unknown을 기록한다.
7. focused legacy tests, actual runner, full tests가 통과한다.

**Plans:** 1 plan

Plans:
- [x] 45-1 Legacy SQL statement risk classification

### Phase 46: DTSX manual review resolution readiness bridge

**Goal:** DTSX spec coverage의 manual-review blocker가 manual implementation coverage와 manual operation step plan으로 해소됐을 때 readiness에서 영구 차단되지 않도록 연결한다.
**Mode:** mvp

**Requirements:** INV-03, BATCH-01, BATCH-02, VAL-04
**Depends on:** Phase 45

**Success Criteria:**
1. `DTSX_SPEC_COVERAGE` report 누락, empty spec, warning blocker는 계속 readiness를 차단한다.
2. `BLOCKED_MANUAL_REVIEW` coverage는 manual implementation report와 manual step plan report가 모두 `PASSED`일 때만 readiness 통과 gate로 인정된다.
3. manual implementation 또는 manual step plan이 누락/blocked/failed이면 `DTSX_SPEC_COVERAGE`는 clear message와 함께 `BLOCKED`로 남는다.
4. 현재 sample readiness는 manual step plan이 `BLOCKED_G1`이므로 계속 `BLOCKED`로 남는다.
5. focused readiness tests, actual readiness runner, approval packet regeneration, full tests가 통과한다.

**Plans:** 1 plan

Plans:
- [x] 46-1 DTSX manual review resolution readiness bridge

### Phase 47: G1 local DTSX candidate evidence collector

**Goal:** 승인된 G1 수집 전에 로컬 repo DTSX 후보의 checksum fragment를 자동 생성해 운영 read-only export와 비교할 기준선을 만든다.
**Mode:** mvp

**Requirements:** INV-03, INV-04, VAL-04, OPS-04
**Depends on:** Phase 46

**Success Criteria:**
1. 로컬 repo 후보 DTSX evidence는 운영 `READ_ONLY_EXPORT`가 아니라 `LOCAL_REPO_CANDIDATE` source type으로 분리된다.
2. validator는 `LOCAL_REPO_CANDIDATE` pack을 G1 통과 증거로 인정하지 않고 명확히 차단한다.
3. command runner가 로컬 `/Users/jm/Documents/workspace/ssis` 기준 DTSX 후보 checksum fragment directory를 생성한다.
4. 생성 report는 후보 수, 발견 수, 누락 수, package path, SHA-256을 기록한다.
5. 현재 sample readiness는 계속 `BLOCKED`로 남는다.
6. focused G1 tests, actual local DTSX candidate runner, full tests가 통과한다.

**Plans:** 1 plan

Plans:
- [x] 47-1 G1 local DTSX candidate evidence collector

### Phase 48: G1 approval decision artifact runner

**Goal:** 사용자 승인 내용을 build-only G1 approval decision artifact로 생성해 approval guard import를 수동 JSON 편집 없이 실행 가능하게 한다.
**Mode:** mvp

**Requirements:** INV-04, VAL-04, OPS-04
**Depends on:** Phase 47

**Success Criteria:**
1. approval packet을 읽어 packet id/request id/read-only query id/forbidden action을 그대로 반영한 decision JSON을 생성한다.
2. `APPROVED_READ_ONLY_EXPORT` decision은 명시 옵션으로만 생성된다.
3. committed template은 계속 `PENDING`으로 유지한다.
4. 생성된 build-only decision으로 G1 import approval guard가 통과한다.
5. local DTSX candidate fragment import는 approval guard를 통과하되 validation은 `BLOCKED_LOCAL_CANDIDATE`로 남는다.
6. focused G1 tests, actual decision runner, guarded import runner, full tests가 통과한다.

**Plans:** 1 plan

Plans:
- [x] 48-1 G1 approval decision artifact runner

### Phase 49: G1 operator export source preflight

**Goal:** operator가 제공한 G1 source-root를 import하기 전에 template/local 후보/누락 fragment를 자동 판정해 잘못된 증거가 G1 import로 들어오는 것을 막는다.
**Mode:** mvp

**Requirements:** INV-04, VAL-04, OPS-04
**Depends on:** Phase 48

**Success Criteria:**
1. complete `READ_ONLY_EXPORT` fragment directory는 `PASSED_READY_TO_IMPORT`로 통과한다.
2. `TODO_` placeholder가 남은 fragment template은 `BLOCKED_TEMPLATE_PLACEHOLDER`로 차단한다.
3. `LOCAL_REPO_CANDIDATE` source type은 `BLOCKED_LOCAL_REPO_CANDIDATE`로 차단한다.
4. 필수 fragment 누락은 `FAILED_MISSING_FRAGMENT`로 실패한다.
5. command runner가 `--partner.integration.g1-operator-preflight.*` 옵션으로 JSON report를 생성한다.
6. 실제 로컬 template/local candidate source-root에 preflight를 실행해 각각 차단 report를 남긴다.
7. focused preflight tests, G1 focused suite, full tests가 통과한다.

**Plans:** 1 plan

Plans:
- [x] 49-1 G1 operator export source preflight

### Phase 50: G1 operator preflight readiness gate

**Goal:** migration readiness가 G1 evidence/import approval뿐 아니라 operator source-root preflight 통과도 필수 gate로 요구하게 만든다.
**Mode:** mvp

**Requirements:** VAL-04, OPS-04
**Depends on:** Phase 49

**Success Criteria:**
1. readiness gate 목록에 `G1_OPERATOR_PREFLIGHT`가 추가된다.
2. preflight report가 없으면 readiness는 `MISSING`/`BLOCKED`로 남는다.
3. preflight conclusion이 `PASSED_READY_TO_IMPORT`가 아니면 readiness는 `BLOCKED`로 남는다.
4. `PASSED_READY_TO_IMPORT` preflight만 readiness 통과 gate로 인정된다.
5. command runner가 `--partner.integration.readiness.g1-operator-preflight-report` 입력을 받는다.
6. sample readiness report는 11 gates, 4 passed, 7 blocked를 기록한다.
7. focused readiness tests, actual readiness runner, approval packet regeneration, full tests가 통과한다.

**Plans:** 1 plan

Plans:
- [x] 50-1 G1 operator preflight readiness gate

### Phase 50: G1 operator preflight readiness gate

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 49
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 50 to break down)

### Phase 51: Legacy SQL comment-prefixed mutation classification

**목표:** 주석 접두어와 변경 SQL 키워드가 같은 DTSX preview 줄에 들어온 경우에도 기존 SQL 계획에서 `DATA_MUTATION`으로 보수 분류한다.
**모드:** mvp

**요구사항:** VAL-04, OPS-04
**의존성:** Phase 50
**성공 기준:**
1. `--- ... Delete ...` 형태의 preview가 `DATA_MUTATION`으로 분류된다.
2. SELECT 분류는 정규화된 SQL에 대해서만 유지되어 주석 문구로 오인되지 않는다.
3. `docs/legacy-sql/sample-report.json`은 `mutationSqlCount=9`, `unknownSqlCount=0`을 기록한다.
4. `docs/readiness/sample-report.json`과 `docs/g1-evidence/approval-packet.json`은 최신 legacy SQL report 기준으로 재생성된다.
5. README와 migration ledger의 기존 SQL 카운트가 최신 보고서와 일치한다.
6. focused legacy tests, actual runner, readiness runner, approval packet runner, full tests가 통과한다.

**계획:** 1개

계획:
- [x] 51-1 기존 SQL 주석 접두어 변경문 분류

### Phase 52: 기존 SQL 보고서 메시지 한글화

**목표:** 기존 SQL plan report의 사용자 노출 메시지를 한글로 바꿔 개발 산출물 언어 기준을 맞춘다.
**모드:** mvp

**요구사항:** VAL-04, OPS-04
**의존성:** Phase 51
**성공 기준:**
1. 저장 프로시저, SELECT SQL, 변경 SQL, 알 수 없는 SQL 메시지가 한글로 생성된다.
2. enum/status/CLI option/adapter boundary 같은 실행 계약은 유지된다.
3. `docs/legacy-sql/sample-report.json`에 기존 영문 메시지가 남지 않는다.
4. legacy SQL 카운트는 SQL 46, SP 34, 미해결 12, SELECT 3, 변경 9, 알 수 없음 0을 유지한다.
5. RED/GREEN focused legacy test, actual legacy runner, full tests가 통과한다.

**계획:** 1개

계획:
- [x] 52-1 기존 SQL 보고서 메시지 한글화

### Phase 53: 준비도와 승인 패킷 메시지 한글화

**목표:** readiness report와 G1 approval packet의 사용자 노출 gate 메시지를 한글 중심으로 바꾼다.
**모드:** mvp

**요구사항:** VAL-04, OPS-04
**의존성:** Phase 52
**성공 기준:**
1. readiness gate 메시지가 한글 중심으로 생성된다.
2. approval packet blocking gate 메시지가 readiness의 한글 메시지를 반영한다.
3. enum/status/CLI option/report key/gate id는 유지된다.
4. readiness sample은 11 gates, passed 4, blocked 7, failed 0을 유지한다.
5. approval packet은 `APPROVAL_REQUIRED`, blocking gates 7을 유지한다.
6. RED/GREEN focused readiness test, actual readiness runner, approval packet runner, full tests가 통과한다.

**계획:** 1개

계획:
- [x] 53-1 준비도와 승인 패킷 메시지 한글화
