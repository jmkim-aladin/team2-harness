# Phase 47 Summary - G1 로컬 DTSX 후보 증거 수집기

## 결과

`partner-integration-batch`가 로컬 repo DTSX 후보 7개의 checksum fragment directory를 생성할 수 있게 됐다. 로컬 커밋: `4f48883`.

추가로 사용자 지시에 따라 `README.md`를 한국어 산출물로 정리했다. 로컬 커밋: `0dbce21`.

## 변경

- `G1EvidenceSourceType.LOCAL_REPO_CANDIDATE` 추가.
- validator가 로컬 repo 후보 pack을 `BLOCKED_LOCAL_CANDIDATE`로 차단하도록 추가.
- 로컬 DTSX 후보 7개 경로, package name, SHA-256을 수집하는 `G1LocalDtsxCandidateCollector` 추가.
- command runner `--partner.integration.g1-local-dtsx-candidates.*` 추가.
- `docs/g1-evidence/import-fragments.md`를 한글 운영 가이드로 정리.
- README와 `docs/migration-ledger.md`에 한글 설명 추가.
- `README.md` 전체 설명 문장을 한국어로 재작성하고, 명령/옵션/스키마명만 기존 형식을 유지.

## 실제 로컬 실행 결과

- Source root: `/Users/jm/Documents/workspace/ssis`
- DTSX 후보: 7
- 발견: 7
- 누락: 0
- Import validation conclusion: `BLOCKED_LOCAL_CANDIDATE`

## 남은 차단

로컬 repo 후보 checksum은 운영 G1 증거가 아니다. 실제 완료에는 운영 SQL Agent active job/step/schedule, 운영 배포 DTSX checksum, SP definition checksum, same-businessDate golden output checksum, publish/readback target, runtime/private-network evidence가 필요하다.
