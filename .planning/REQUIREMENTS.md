# Requirements: IDC DB 이관 B2B SSIS 13-17 Spring Batch 전환

**Defined:** 2026-06-19
**Core Value:** 기존 SSIS가 생성하던 파트너 연동 산출물을 검증 가능한 Spring Batch 실행 단위로 재현하고, 이관 중에는 기존 파일/HTTP/FTP/API 제공 계약을 깨지 않는다.

## v1 Requirements

### Inventory

- [ ] **INV-01**: Excel 13-17번을 실제 DTSX package 후보와 연결한 inventory report를 만든다.
- [ ] **INV-02**: 각 DTSX에서 Control Flow, Data Flow, variable, parameter, connection manager, precedence constraint를 추출한다.
- [ ] **INV-03**: 각 DTSX의 SQL/SP 호출, table mutation, Script Task, file I/O, cleanup, publish endpoint를 operation type으로 분류한다.
- [ ] **INV-04**: SQL Agent `msdb` read-only 근거로 active job/step/package/schedule을 확정한다.

### Architecture

- [ ] **ARCH-01**: 신규 별도 repo의 독립 Kotlin + Spring Boot + Spring Batch app 구조를 정의한다.
- [ ] **ARCH-02**: `LegacyDbAdapter`, `IntegrationArtifactGenerator`, `IntegrationPublisher`, `IntegrationManifestRepository`, `IntegrationValidator` 경계를 정의한다.
- [ ] **ARCH-03**: 기존 SP/SQL은 `LegacyDbAdapter` 내부 typed method로만 노출한다.
- [ ] **ARCH-04**: v1 delivery는 file/HTTP/FTP/API current contract compatibility bridge로 유지하고 post-migration 변경으로 분리한다.

### Batch Model

- [ ] **BATCH-01**: SSIS Package를 Spring Batch `Job`, Control Flow를 Step/flow/decider, Execute SQL Task를 Tasklet, Data Flow를 chunk Step으로 매핑한다.
- [ ] **BATCH-02**: integration별 JobParameters는 `integrationId`, `mode`, `businessDate`, `contractVersion`, `shadowRun`, `forceRebuild`, `retransferArtifactId`를 지원한다.
- [ ] **BATCH-03**: rebuild와 retransfer를 분리한다.
- [ ] **BATCH-04**: full feed는 paging/range/partition/streaming writer로 처리하고 JVM full-list 적재를 금지한다.

### Feed Contracts

- [ ] **FEED-01**: Naver book feed는 full/today JSONL 또는 JSONL.js 계약을 명세화한다.
- [ ] **FEED-02**: Naver shopping feed는 product/sales/today TXT 계약을 명세화한다.
- [ ] **FEED-03**: Naver ranking row 15는 active SQL Agent 확인 후 exact scope를 명세화한다.
- [ ] **FEED-04**: Google feed는 TSV split 기준과 group/page 기준을 명세화한다.
- [ ] **FEED-05**: Kakao/Daum feed는 six XML output 계약과 retention 동작을 명세화한다.

### Validation

- [ ] **VAL-01**: 기존 SSIS output golden files를 확보하고 byte-level 비교 기준을 정의한다.
- [ ] **VAL-02**: shadow run은 같은 `businessDate` 기준으로 row count, byte count, checksum, aggregate total, reject count, duration을 비교한다.
- [ ] **VAL-03**: publish 전 schema, encoding, newline, delimiter, null handling, sort order를 검증한다.
- [ ] **VAL-04**: publish 후 readback smoke와 manifest status를 기록한다.

### Operations

- [ ] **OPS-01**: Spring Batch metadata와 별도로 feed-domain manifest schema를 정의한다.
- [ ] **OPS-02**: 동일 feed/businessDate 동시 실행 방지 lock을 정의한다.
- [ ] **OPS-03**: 실패 시 restart, manual rerun, retransfer, rollback runbook을 정의한다.
- [ ] **OPS-04**: runtime account, secret source, private network allowlist, alert route를 승인 항목으로 분리한다.

## v2 Requirements

### Delivery Modernization

- **DELIV-01**: 이관 후 `ftp.aladin.co.kr`, `www2.aladin.co.kr`, SMB/UNC/API 제공 방식을 private web endpoint, SFTP/FTPS, private object storage/private distribution, API/payload delivery 계열 중 하나로 재설계한다.
- **DELIV-02**: manifest-driven lifecycle 기반 retention으로 기존 delete/cleanup task를 대체한다.
- **DELIV-03**: partner-facing URL/protocol/path/auth 변경이 필요하면 별도 승인과 partner communication plan을 작성한다.

## Out of Scope

| Feature | Reason |
|---------|--------|
| DTSX 1:1 production code generation | 배치 명세 추출과 skeleton 생성까지만 현실적이며 운영 동등성을 보장할 수 없다. |
| 기존 B2B batch repo를 기본 베이스로 확장 | 참고 구현으로는 활용하되 SSIS 이관 전용 책임과 기존 B2B batch 책임을 섞지 않는다. |
| v1 delivery redesign | 파일 제공 방식은 이관 후 변경하기로 결정했다. |
| 승인 없는 DB/SP/prod 변경 | team2 정책상 별도 승인 필요. |
| row 15 구현 착수 | active SQL Agent 확인 전까지 scope가 불명확하다. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INV-01 | Phase 1, Phase 10 | Implemented local Excel/DTSX candidate ledger and DTSX inventory JSON; canonical active mapping still requires G1 |
| INV-02 | Phase 1, Phase 10, Phase 11 | Partial: extractor captures package, connection manager, variable, executable/task, precedence constraint, and SQL candidates; Script Task internals still need follow-up if cutover-critical |
| INV-03 | Phase 1, Phase 10, Phase 11 | Partial: SQL/SP candidates, file/path variables, precedence edges, and operation categories classified locally; publish/readback and cleanup final classification still requires G1 |
| INV-04 | Phase 1, Phase 16, Phase 18, Phase 19, Phase 20 | Blocked: read-only SQL Agent approval required; offline G1 evidence-pack acceptance validator, fill-in template generator, directory-fragment importer, and fragment template directory generator implemented |
| ARCH-01 | Phase 2, Phase 8 | Implemented local repo skeleton: `/Users/jm/Documents/workspace/b2b/partner-integration-batch` |
| ARCH-02 | Phase 2, Phase 8 | Implemented initial ports: manifest, artifact, validation, publisher, legacy adapter |
| ARCH-03 | Phase 2, Phase 8 | Implemented `LegacyDbAdapter` boundary with no-op adapter; real SP mapping blocked by G1 |
| ARCH-04 | Phase 2, Phase 17 | Partial: local publish/readback compatibility bridge harness implemented; real file/HTTP/FTP/API target proof still requires G1/runtime approval |
| BATCH-01 | Phase 2, Phase 8, Phase 9, Phase 12 | Implemented local Spring Batch tasklet flow for Naver book, Naver shopping, Google, Kakao/Daum; generated DTSX-to-Spring-Batch mapping spec; Naver ranking blocked |
| BATCH-02 | Phase 2, Phase 8, Phase 22 | Implemented `integrationId`, `mode`, `businessDate`, `contractVersion`, `runPurpose`, `targetAlias`, `forceRebuild`, and `retransferArtifactId` parsing |
| BATCH-03 | Phase 2, Phase 22, Phase 23 | Implemented local rebuild/retransfer separation and manifest-based retransfer without artifact regeneration; production publish approval remains gated |
| BATCH-04 | Phase 2 | Planned: paging/range/partition reader and streaming writer rule |
| FEED-01 | Phase 4, Phase 9 | Implemented local Naver book FULL/TODAY skeleton outputs; SSIS-equivalent content blocked by G1 |
| FEED-02 | Phase 4, Phase 9 | Implemented local Naver shopping FULL/TODAY skeleton outputs; SSIS-equivalent content blocked by G1 |
| FEED-03 | Phase 4, Phase 9 | Blocked by G1: `naverRankingFeedJob` exists but fails before execution until row 15/ranking scope is confirmed |
| FEED-04 | Phase 4, Phase 9 | Implemented local Google FULL/TODAY skeleton outputs; SSIS-equivalent content blocked by G1 |
| FEED-05 | Phase 4, Phase 8, Phase 9 | Implemented local Kakao/Daum six XML dated outputs; SSIS-equivalent content blocked by G1 |
| VAL-01 | Phase 3, Phase 13, Phase 14, Phase 16, Phase 18, Phase 19, Phase 20 | Specified and implemented local comparator plus final equivalence/G1 evidence gates, template, import path, and fragment directory generation; actual golden file acquisition Blocked by G1 |
| VAL-02 | Phase 3, Phase 13, Phase 14, Phase 16, Phase 18, Phase 19, Phase 20 | Specified and implemented byte/line/SHA comparison plus equivalence/G1 evidence report/template/import path; real shadow comparison blocked by G1 |
| VAL-03 | Phase 3, Phase 13, Phase 14, Phase 15 | Specified: pre-publish schema/format/byte validation; implemented basic contract-format validator, byte/hash comparator, and final pass/block/fail gate; partner-specific field schemas still require G1 follow-up |
| VAL-04 | Phase 5, Phase 8, Phase 9, Phase 17 | Implemented local shadow publish/readback ledger status and local filesystem publish/readback report with byte/SHA readback; actual partner-facing readback proof blocked by G1/runtime access |
| OPS-01 | Phase 2, Phase 8, Phase 17, Phase 21, Phase 23 | Implemented file-backed `IntegrationManifest` ledger skeleton plus local publish/readback JSON evidence report, lock acquisition event, artifact lookup, and validation lookup |
| OPS-02 | Phase 2, Phase 21 | Implemented local domain lock key and file-backed atomic lock; production store/takeover rule still depends on G2 storage decision |
| OPS-03 | Phase 5, Phase 6, Phase 22, Phase 23 | Specified: restart, manual rebuild, retransfer, rollback runbook; cutover rollback gates specified; rebuild/retransfer preflight separation and local manifest-based retransfer implemented |
| OPS-04 | Phase 2, Phase 6, Phase 16, Phase 18, Phase 19, Phase 20 | Specified runtime account/private network/secret approval matrix and implemented offline G1 evidence-pack validator/template/importer plus fragment template directory for runtime evidence |
| DELIV-01 | Phase 7 | Specified: private web endpoint, SFTP/FTPS, private object storage/private distribution, API/payload delivery options |
| DELIV-02 | Phase 7 | Specified: manifest-driven `LifecyclePolicy` retention model |
| DELIV-03 | Phase 7 | Specified: partner communication, compatibility period, approval gates, rollback |

**Coverage:**
- v1 requirements: 24 total
- v2 requirements: 3 total
- Mapped to phases: 27
- Unmapped: 0

---
*Requirements defined: 2026-06-19*
*Last updated: 2026-06-19 after Phase 23 manifest based retransfer*
