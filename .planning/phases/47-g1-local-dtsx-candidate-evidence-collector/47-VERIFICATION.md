# Phase 47 Verification - G1 로컬 DTSX 후보 증거 수집기

## 명령

- `./gradlew test --tests 'kr.co.aladin.partner.integration.batch.g1.*'`
- actual local DTSX candidate runner
- G1 import runner against `build/g1-evidence/local-dtsx-candidates`
- `./gradlew test --rerun-tasks`
- `git diff --check`

## 결과

- RED check: enum/class 미구현 상태에서 focused G1 test compile failure 확인.
- Focused G1 tests: 통과.
- Actual local DTSX candidate runner: 통과, 7/7 후보 발견.
- G1 import runner: 통과, validation conclusion `BLOCKED_LOCAL_CANDIDATE`.
- Full test suite: 통과.
- Whitespace check: 통과.
