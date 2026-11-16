# 회원·알림 MSA KB 탐색 인덱스

확인일: 2026-11-11 · 작업: TASK-20261111-3a77f7dab91e

KB는 YouTrack 원문을 참조한다. 하네스에는 저장소·자료 탐색과 영향 확인 경계를 두고, 상세 요약과 시점별 차이는 위키에 둔다. owner 확인과 배포 검증은 수행하지 않았으므로 세 공통 서비스의 등록 상태는 `candidate`를 유지한다.

## 시작 경로

| 대상 | 하네스 프로파일 | 위키 진입점 | KB 첫 문서 |
|---|---|---|---|
| 회원 | [회원 MSA](member-msa.yaml) | [회원 자료 모음](/Users/jm/Library/Mobile%20Documents/iCloud~md~obsidian/Documents/team2/wiki/services/member-msa/member-msa.md) | [REF-A-4113](https://aladincommunication.youtrack.cloud/articles/REF-A-4113) → [제공 기능](https://aladincommunication.youtrack.cloud/articles/REF-A-4368) |
| 알림 | [알림 MSA](notification-msa.yaml) | [알림 자료 모음](/Users/jm/Library/Mobile%20Documents/iCloud~md~obsidian/Documents/team2/wiki/services/notification-msa/notification-msa.md) | [REF-A-4110](https://aladincommunication.youtrack.cloud/articles/REF-A-4110) → [저장소별 설명](https://aladincommunication.youtrack.cloud/articles/REF-A-4461) |
| 공통 인증·BFF | [알라딘 인증](aladin-auth.yaml) | [인증 자료 모음](/Users/jm/Library/Mobile%20Documents/iCloud~md~obsidian/Documents/team2/wiki/services/aladin-auth/aladin-auth.md) | [REF-A-4366](https://aladincommunication.youtrack.cloud/articles/REF-A-4366) → [제공 기능](https://aladincommunication.youtrack.cloud/articles/REF-A-4369) |

위키 링크는 개인 로컬 vault 경로다. 다른 장비에서는 동일한 vault 내부 경로로 찾는다.

## 수집 범위

YouTrack REST API로 회원·알림·Member·Notification·Auth·MSA를 검색한 뒤 관련 루트의 실제 `childArticles`를 재귀 조회했다. 본문 조회에 성공한 고유 문서는 **323건**이다. 모든 본문을 동일 깊이로 검토한 것은 아니며, 요약은 주요 설계·연동·운영 문서와 일부 소스 대조에 한정한다.

| 분류 | 실제 트리 | 추가 관련 문서 | 위키 자료 목록 |
|---|---:|---:|---|
| 회원 | REF-A-4113 아래 57 | 3 | 회원 분석 노트 |
| 알림 | REF-A-4110 아래 98 | 4 | 알림 분석 노트 |
| 인증 | REF-A-4366 아래 156 | 5 | 인증 분석 노트 |
| 합계 | 311 | 12 | 323개 고유 KB ID |

전체 목록은 각 위키 분석 노트에 KB 링크·부모 ID·최종 수정일(KST)로 보존한다. KB 원문, 환경 설정값, 개인정보 예시, 코드·SQL 원문은 복제하지 않는다. KB의 ERD·인프라 이미지는 원문 링크에서 확인한다.

알림 루트·책임 문서에 남은 이전 참조 `REF-A-4372`, `REF-A-4373`, `REF-A-4374`, `REF-A-4398`은 같은 날 API 조회에서 404 오류가 보고되어 수집 건수에서 제외했다. 삭제·이동·권한 중 원인은 확인하지 못했다. 발송 흐름은 조회 가능한 `REF-A-4487`, `REF-A-4450`, `REF-A-4472`, `REF-A-5093`을 우선 참조한다.

## 업무별 읽기 순서

| 업무 | 순서 |
|---|---|
| 회원 가입·조회·탈퇴·파기 | REF-A-4368 → 해당 하위 API 문서 → REF-A-4750 → MemberDomain 라우트·핸들러 |
| 회원군 라우팅·M2M | REF-A-4369 → REF-A-4924 → REF-A-5264/5265 → MemberApi·Auth 계약 |
| 회원↔알림 연동 | REF-A-4399 → REF-A-4449 → REF-A-5265 → 회원 아웃박스와 알림 Lifecycle 라우트 |
| 발송 책임·상태 전이 | REF-A-5093 → REF-A-4470 → REF-A-4451/4459 → 해당 서비스 구현 |
| 예약·배치·장애 복구 | REF-A-4395 → REF-A-4557 → REF-A-4533/4544 → 현재 배포 설정 |
| 수신동의·개인정보 | REF-A-4501 → REF-A-4485 → REF-A-4449 → 서비스 코드와 운영 정책 |
| 알림 콘솔 로그인 | REF-A-4469 → REF-A-4536 → REF-A-4369 → CommonBff·Auth·api-noti 계약 |

## 재확인 원칙

KB 제목의 `구현 완료`, 과거 테스트 성공 수치, 인프라 요청의 주소를 현재 운영 사실로 옮기지 않는다. 최신 수정일은 내용 전체의 최신성을 보장하지 않는다. 문서끼리 또는 소스와 다른 설명은 위키의 차이 표에서 출발해 owner와 현재 배포 계약을 확인한다.

관련 정책: [공통 서비스 정책](../../policies/common-service-policy.md), [지식 분리 정책](../../policies/knowledge-base-policy.md).
