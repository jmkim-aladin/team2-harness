# 공통 서비스 정책

## 목적

개발 2팀 업무는 팀 소유 서비스만으로 끝나지 않는다. 알라딘 인증, 뉴빌링처럼 여러 팀·서비스가 함께 쓰는 공통 서비스가 티켓의 실제 영향 범위를 결정한다. 이 정책은 팀 서비스 카탈로그와 별도로 공통 서비스를 정의하고, 티켓 준비·설계·리뷰에서 공통 서비스 영향 확인을 빠뜨리지 않기 위한 기준이다.

## 정의

| 구분 | 의미 | 등록 위치 |
|---|---|---|
| 팀 서비스 | 개발 2팀이 직접 소유하거나 주도적으로 변경·운영하는 서비스 | `catalog/{service_id}.yaml` |
| 공통 서비스 | 여러 팀/서비스가 소비하며 소유권, 배포, 변경 승인 경계가 팀 밖에도 걸친 서비스 | `catalog/common-services/registry.yaml` |
| 외부 의존 | 벤더, 타 부서, 사내 공용 DB/API 등 직접 변경 권한이 없는 시스템 | 공통 서비스 registry 또는 각 팀 서비스 dependency |

공통 서비스 registry는 운영 사실의 최종 원장이 아니다. 팀 업무에서 반복 확인해야 할 영향 경계와 조사 진입점을 기록하는 하네스다. 실제 confirmed 지식은 코드, 운영 문서, YouTrack KB, 회의/결정 기록, owner 확인으로 검증한다.

## 공통 서비스 영향 확인

아래 조건 중 하나라도 해당하면 티켓 준비, 설계, 코드 리뷰, QA 계획에 공통 서비스 영향 확인을 포함한다.

- 로그인, SSO, 세션, 권한, 회원 식별, partner user mapping을 건드린다.
- 결제, 청구, 환불, 정산, 구독, 포인트/적립금, 세금계산서 흐름을 건드린다.
- 신규 빌링, 결제, 청구, 환불, 정산, 구독, 빌링키 기능을 만든다.
- 주문/배송/클레임 상태가 다른 서비스에 이벤트나 API로 전파된다.
- 공유 DB, 공유 SP, 공통 batch, 공통 메시지/이벤트/outbox를 읽거나 쓴다.
- storefront, bazaar, max, tobe, shopping, blog, naru, aasm 등이 같은 기능에서 함께 언급된다.
- 운영 장애/데이터 추출 요청에서 원인 서비스와 영향 서비스가 다를 수 있다.

## 필수 절차

1. 대상 팀 서비스를 먼저 식별한다.
2. `catalog/{service_id}.yaml`의 `dependencies`를 확인한다.
3. `catalog/common-services/registry.yaml`에서 관련 공통 서비스를 찾는다.
4. 공통 서비스가 있으면 티켓/분석 노트에 `공통 서비스 영향` 섹션을 만든다.
5. 확인 수준을 명시한다.
   - `candidate`: 이름/회의/티켓에 언급됨
   - `evidence`: 코드 경로, API, DB, SP, runbook, KB 중 하나로 확인됨
   - `owner-confirmed`: 공통 서비스 owner 또는 운영 책임자가 확인함
6. owner-confirmed 전에는 확정 지식으로 승격하지 않는다.

## 자동화 경계

Hermes, Codex, Claude Code, GBrain은 공통 서비스 후보를 찾고 위키 draft를 보강할 수 있다. 하지만 아래는 사용자 승인 없이 하지 않는다.

- 공통 서비스 owner에게 요청 발송
- YouTrack 티켓/Task 생성 또는 상태 변경
- YouTrack KB 생성/수정/삭제
- DB/SP/schema 변경
- 운영 설정, 인증, 결제, 정산 상태 변경
- vault 문서의 `confirmed`, `canonical`, `done` 승격

## 초기 공통 서비스

초기 registry에는 다음 서비스를 등록한다.

| service_id | 표시명 | 우선 확인 영역 |
|---|---|---|
| `aladin-auth` | 알라딘 인증 | 로그인, SSO, 세션, 권한, 회원 식별 |
| `new-billing` | 뉴빌링 | 결제, 청구, 환불, 정산, 구독 |

뉴빌링은 `billing-backend`, `billing-frontend` 소스가 확인된 개발 중 공통 서비스다. 현재 팀 서비스와의 active 연동은 확인되지 않았으므로 production dependency로 쓰지 않는다. 다만 새로 만들어지는 빌링, 결제, 정산, 구독, 빌링키 기능은 먼저 `catalog/common-services/new-billing.yaml`의 뉴빌링 API 경계를 확인하고, 경유하지 않는다면 사유를 티켓/설계 노트에 남긴다.

새 공통 서비스가 반복 등장하면 `catalog/common-services/registry.yaml`에 먼저 후보로 추가한다. owner, API, repo, KB, 운영 runbook이 확인되기 전에는 `status: candidate`로 둔다.

## 문서 위치

- 공통 서비스 정책과 registry: team2 repo
- 공통 서비스별 분석, 장애 영향, 회의/결정, 티켓 산출물: Obsidian vault
- 전사 공통 원천 가이드: YouTrack KB
- 공통 서비스 코드와 강결합된 runbook: 해당 서비스 repo
