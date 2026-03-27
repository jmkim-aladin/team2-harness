# 레거시 현대화 정책

## 현대화 4트랙

모든 서비스는 분석 후 반드시 아래 4가지 중 하나로 분류한다.

| 트랙 | 설명 | 대상 기준 |
|------|------|-----------|
| **Observe** | 문서화와 하네스만 생성 | 변경 적고 안정적, 당장 건드릴 필요 없음 |
| **Wrap** | adapter/facade로 감싸기 | SP-heavy, 직접 의존 끊어야 할 때 |
| **Extract** | 신규 서비스로 도메인 추출 | 변경 빈도 높고 사업 중요도 높은 영역 |
| **Freeze/Retire** | 종료 계획만 관리 | 사실상 사용되지 않는 서비스 |

## 분류 기준

**기술 기준이 아니라 사업 기준으로 분류한다.**

> .NET Framework라서 먼저 옮기는 게 아니라, **자주 바뀌고 다른 서비스가 많이 붙어 있는 곳**부터 뺀다.

분류 매트릭스: `변경 빈도 × 장애 영향도 × 데이터 결합도`

## 실행 원칙

### SP 관련
- 신규 코드에서 SP 직접 호출 금지
- SP 호출은 legacy adapter repo/service에서만 허용
- SP 변경 시 필수 첨부: 영향 테이블, 입출력 계약, 롤백 스크립트, 최소 재현 데이터셋, smoke test
- SP를 없애는 프로젝트가 아니라 **SP가 퍼지는 걸 멈추는 프로젝트**부터 시작

### 추출 순서
1. read path 먼저 분리 (조회 분리는 상대적으로 안전)
2. write path는 나중에 (트랜잭션/정합성 이슈가 큼)
3. 테이블/스키마의 write owner는 1개만 유지
4. 신규 서비스가 레거시 DB/SP를 직접 때리지 않게 adapter 뒤에 숨김

### .NET 레거시
- 자동 변환보다 점진적 라우팅이 안전
- side-by-side incremental: 새 프로젝트를 옆에 두고 일부 엔드포인트만 새 앱으로 라우팅
- 한 번에 업그레이드가 아니라 우회/대체/분리 라우팅

## 신규 서비스 원칙

신규 서비스는 분석이 아니라 **골든 패스 템플릿**으로 시작한다.

4가지 archetype:
- sync API service (REST API)
- async worker/batch
- legacy adapter service
- admin/backoffice service

각 템플릿에 기본 하네스(AGENTS.md, 공통 에러 포맷, observability, GitHub workflow, PR 템플릿, smoke test, 보안 규칙, rollback 문서)가 포함되어야 한다.

> **레거시는 discovery-based, 신규는 template-based**
