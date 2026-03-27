# 개발 2팀 팀원 정보

## 팀 구성

### 정규직

| 역할 | 이름 | 이메일 (YouTrack ID) | 담당 서비스 |
|------|------|---------------------|-------------|
| 팀장 | 김규태 | ktkim@aladin.co.kr | 전체 |
| 디자이너 | 김정실 | jungsiri@aladin.co.kr | |
| 디자이너 | 이유림 | design72@aladin.co.kr | |
| 기획자 | 조윤주 | yj@aladin.co.kr | |
| 백엔드 개발자 | 김정민 | jmkim@aladin.co.kr | max, tobe, naru, aasm (메인) |
| 백엔드 개발자 | 안혜련 | hyeryun@aladin.co.kr | b2b |
| 백엔드 개발자 | 이현민 | bbooya@aladin.co.kr | b2b |
| 프론트엔드 개발자 | 조은흠 | heum2@aladin.co.kr | max, tobe (서브) |

### 프리랜서

| 역할 | 이름 | 이메일 (YouTrack ID) | 담당 서비스 |
|------|------|---------------------|-------------|
| 백엔드 개발자 | 강인용 | iyk@aladin.co.kr | bazaar (메인) |
| 백엔드 개발자 | 박희수 | heesoo@aladin.co.kr | max, tobe |
| 백엔드 개발자 | 조주영 | jjy@aladin.co.kr | bazaar (서브) |

## 서비스별 담당

| 서비스 | Owner (메인) | 서브/백업 | 비고 |
|--------|-------------|-----------|------|
| max (만권당) | 김정민 (jmkim) | 조은흠 (heum2), 박희수 (heesoo) | |
| tobe (투비컨티뉴드) | 김정민 (jmkim) | 조은흠 (heum2), 박희수 (heesoo) | |
| naru | 김정민 (jmkim) | | |
| bazaar | 강인용 (iyk) | 조주영 (jjy) | 프리랜서 |
| aasm | 김정민 (jmkim) | | |
| b2b | 안혜련 (hyeryun) | 이현민 (bbooya) | 서비스 미등록 — 레포 확정 후 카탈로그 추가 |

## 역할 정의

| 역할 | 하네스 내 권한 |
|------|---------------|
| 팀장 | 도메인 경계 승인, 예외 기술 승인, 모든 상태 전환 |
| 기획자 | 티켓 생성, 요구사항 정의, 레거시 유지/대체/폐기 우선순위 결정 |
| 디자이너 | UI/UX 설계, BFF/API contract 기준 UI 변경면 최소화 |
| 백엔드 개발자 | 신규 개발, 레거시 adapter, 추출 후보 선정, 코드 변경/배포 |
| 프론트엔드 개발자 | 프론트엔드 개발, API 연동, UI 구현 |

## 승인 권한

| 항목 | 승인자 |
|------|--------|
| 일반 PR | 서비스 담당자 중 본인 외 1명 |
| DB/SP 변경 | 서비스 owner + 팀장 |
| 프로덕션 배포 | 서비스 owner |
| 신규 서비스 생성 | 팀장 |
| 현대화 트랙 변경 | 팀장 |
