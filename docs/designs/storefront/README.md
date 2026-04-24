# 스토어 프론트 설계 문서

B2B 스토어프론트(SF) 프로젝트 설계 문서 모음. 속성별로 6개 폴더로 분리.

---

## 📁 폴더 구조

### 1. [`scope/`](./scope/) — 비전·스코프 정의

프로젝트 컨셉, 플랫폼 방향성, MVP 스코프 문서.

| 문서 | 설명 |
|------|------|
| [b2b-saas-platform-concept.md](./scope/b2b-saas-platform-concept.md) | B2B SaaS 플랫폼 최초 컨셉 (4/1) |
| [multi-storefront-platform-direction.md](./scope/multi-storefront-platform-direction.md) | 멀티 스토어프론트 플랫폼 방향성 (4/15) |
| [b2b-store-scope-definition-0415.md](./scope/b2b-store-scope-definition-0415.md) | 스코프 정의 1차 (4/15) — V1.1(4/21)까지 반영 |
| [storefront-as-demand-orchestrator.md](./scope/storefront-as-demand-orchestrator.md) | **SF Charter (4/22)** — SF = 수요 오케스트레이터 정체성, 바자르(공급) 대칭 구조, mermaid 다이어그램 포함 |

### 2. [`meetings/`](./meetings/) — 회의 준비·회의록

날짜별 회의 자료. 준비(prep)·가이드(guide)·회의록(minutes) 3종.

| 문서 | 설명 |
|------|------|
| [b2b-store-meeting-prep-0410.md](./meetings/b2b-store-meeting-prep-0410.md) | 4/10 회의 준비 |
| [b2b-store-meeting-guide-0410.md](./meetings/b2b-store-meeting-guide-0410.md) | 4/10 회의 가이드 |
| [b2b-store-meeting-minutes-0415.md](./meetings/b2b-store-meeting-minutes-0415.md) | 4/15 스코프 1차 회의록 |
| [b2b-store-meeting-prep-0417.md](./meetings/b2b-store-meeting-prep-0417.md) | 4/17 주문 여정 상세 회의 준비 |
| [b2b-store-meeting-minutes-0417.md](./meetings/b2b-store-meeting-minutes-0417.md) | 4/17 도메인 분류 회의록 (13영역 공식화) |
| [b2b-store-meeting-prep-0420.md](./meetings/b2b-store-meeting-prep-0420.md) | 4/20 이벤트 스토밍 사전 배포 |
| [b2b-store-mvp-agreement-0422.md](./meetings/b2b-store-mvp-agreement-0422.md) | **4/22 MVP 합의 (기획자 공용)** — 첫 고객·Must 8·Should 5·Could 4·Won't, 시간 차원 질문법, 확인 5가지 |

### 3. [`architecture/`](./architecture/) — 설계·DDD·아키텍처

시스템 아키텍처, 데이터 모델, DDD 분류, MSA 진화 경로.

| 문서 | 설명 |
|------|------|
| [b2b-store-tenant-model.md](./architecture/b2b-store-tenant-model.md) | Schema per Tenant 멀티테넌시 전략 |
| [b2b-store-naru-oidc-integration.md](./architecture/b2b-store-naru-oidc-integration.md) | Naru OIDC 인증 설계 |
| [b2b-store-ddd-classification.md](./architecture/b2b-store-ddd-classification.md) | 서브도메인·BC·Context Map·MSA 진화·다중 공급원 확장 (10개 섹션) |
| [b2b-store-bazaar-coordination.md](./architecture/b2b-store-bazaar-coordination.md) | **SF ↔ 바자르 연동 설계 (4/22)** — 실 코드 분석 기반. `Vendor.B2B_STOREFRONT` 신규 등록 권장, API 4개 Port, Outbox 이벤트, 김규태 협의 체크리스트, 미결 11개 |

### 4. [`event-storming/`](./event-storming/) — 이벤트 스토밍

워크숍 진행서, 기술 세션 가이드, 결과 시뮬레이션.

| 문서 | 설명 |
|------|------|
| [b2b-store-event-storming-planning.md](./event-storming/b2b-store-event-storming-planning.md) | 기획 워크숍 진행 방식 (90분, 3색) |
| [b2b-store-event-storming-guide.md](./event-storming/b2b-store-event-storming-guide.md) | 기술 세션 가이드 (2~3시간, 7색, BC 경계) |
| [b2b-store-event-storming-simulation.md](./event-storming/b2b-store-event-storming-simulation.md) | 워크숍 결과 사전 시뮬레이션 (4개 여정) |

### 5. [`domain/`](./domain/) — 도메인 결정 마스터

미결 결정 단일 출처, V1.1 반영 기록.

| 문서 | 설명 |
|------|------|
| [b2b-store-domain-decisions.md](./domain/b2b-store-domain-decisions.md) | D-01~D-19 결정 + A-01~A-05 액션 마스터 레지스트리 |
| [b2b-store-domain-v11-reflection.md](./domain/b2b-store-domain-v11-reflection.md) | 도메인 V1.1 반영 기록 (4/21 기획 스코프 확장) + 이벤트 스토밍 중간점검(4/22) |
| [b2b-store-mvp-definition-0422.md](./domain/b2b-store-mvp-definition-0422.md) | **MVP 정의 (4/22 기획자 협의용)** — 첫 고객 = 일반 몰 임직원 기준 Walking Skeleton + MoSCoW 분류 + BC 10개 축소 + Phase 로드맵 |

### 6. [`reviews/`](./reviews/) — 리뷰

CEO 리뷰, 기타 리뷰 기록.

| 문서 | 설명 |
|------|------|
| [b2b-store-ceo-review.md](./reviews/b2b-store-ceo-review.md) | 4/8 최초 CEO 리뷰 (Phase 0~4 티켓 매핑) |

---

## 🧭 읽는 순서 가이드

### 신규 합류자 (외주 BE/FE 포함)

1. `scope/b2b-saas-platform-concept.md` → 프로젝트 최초 컨셉
2. `scope/multi-storefront-platform-direction.md` → 플랫폼 방향
3. `scope/storefront-as-demand-orchestrator.md` → **SF 정체성(수요 오케스트레이터)**
4. `meetings/b2b-store-meeting-minutes-0415.md`, `meetings/b2b-store-meeting-minutes-0417.md` → 주요 회의 결과
5. `architecture/b2b-store-tenant-model.md` → 테넌트 모델
6. `architecture/b2b-store-naru-oidc-integration.md` → 인증 설계
7. `architecture/b2b-store-ddd-classification.md` → DDD·BC·MSA 진화 전체
8. `architecture/b2b-store-bazaar-coordination.md` → SF↔바자르 연동
9. `domain/b2b-store-domain-v11-reflection.md` → 최신 도메인 V1.1 기준

### 이벤트 스토밍 참석자

1. `meetings/b2b-store-meeting-prep-0420.md` → 사전 배포 체크리스트
2. `event-storming/b2b-store-event-storming-planning.md` → 워크숍 진행
3. `event-storming/b2b-store-event-storming-simulation.md` → 예상 산출물
4. `domain/b2b-store-domain-decisions.md` → D-01~D-19 핫스팟

### 아키텍처 결정 리뷰

1. `domain/b2b-store-domain-decisions.md` → 미결 마스터
2. `architecture/b2b-store-ddd-classification.md` → BC·MSA
3. `domain/b2b-store-domain-v11-reflection.md` → 최신 결정 이력

---

## 🔗 외부 참조

- 상위 티켓: DEV2-5283
- YouTrack KB: DEV2-A-1050 (4/15 기획), DEV2-A-1064 (4/17 도메인 분류)
- 티켓 업데이트 기록: `docs/DEV2-5283-subtask-updates-0420.md` (상위 `docs/`)

---

## 📝 명명 규칙

- `b2b-store-` 접두어: B2B 스토어프론트 전용 문서 (대부분)
- `multi-storefront-` 접두어: 플랫폼 차원 문서 (스토어프론트 일반)
- `b2b-saas-` 접두어: B2B SaaS 최초 컨셉
- 날짜 접미사 `-0415`: 해당 일자 회의·산출물 (YYMMDD 또는 MMDD)

새 문서 작성 시 속성에 맞는 폴더에 배치. 분류 애매하면 `domain/`에.
