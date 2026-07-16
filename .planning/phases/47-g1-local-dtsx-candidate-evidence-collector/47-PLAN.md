# Phase 47 Plan - G1 로컬 DTSX 후보 증거 수집기

## 목표

로컬 DTSX 후보 파일의 SHA-256 기준선을 G1 fragment 형태로 생성하되, 이 산출물이 운영 read-only evidence가 아님을 스키마와 validator에서 명확히 구분한다.

## 작업

1. `LOCAL_REPO_CANDIDATE` source type이 G1 pass로 인정되지 않는 failing test를 추가한다.
2. 로컬 DTSX 후보 수집기 테스트를 추가한다.
3. `G1EvidenceSourceType.LOCAL_REPO_CANDIDATE`와 validator 차단 규칙을 추가한다.
4. 로컬 후보 DTSX 경로/패키지명/checksum을 수집해 fragment directory와 report를 쓰는 runner를 구현한다.
5. README, migration ledger, GSD ledger를 한글로 갱신한다.
6. 실제 `/Users/jm/Documents/workspace/ssis` 기준 runner를 실행해 build-only evidence를 생성한다.
7. focused G1 tests와 full test suite를 실행한다.

## 검증

- `./gradlew test --tests 'kr.co.aladin.partner.integration.batch.g1.*'`
- actual local DTSX candidate runner
- G1 import runner against generated candidate fragment directory
- `./gradlew test --rerun-tasks`
- `git diff --check`
