# gstack 팀 오버라이드 정책

gstack 스킬 사용 시 팀 정책이 gstack 기본값보다 우선한다.
아래 항목은 gstack 스킬의 기본 동작을 팀 컨벤션으로 대체한다.

## Git 컨벤션 오버라이드

### 브랜치 네이밍
- gstack 기본: 제한 없음
- **팀 규칙**: `feature/{이슈ID}` (예: `feature/T2-123`)
- `/ship` 실행 시 현재 브랜치가 `feature/` 접두사인지 확인

### 커밋 메시지 형식
- gstack 기본: `<type>: <summary>` (conventional commits)
- **팀 규칙**: `[{이슈ID}] 작업 내용` (예: `[T2-123] 로그인 API 구현`)
- `/ship`의 bisected commit에도 이 형식 적용
- VERSION/CHANGELOG 커밋도 동일: `[{이슈ID}] 버전 범프 및 변경 로그 갱신`

### Co-Authored-By 삽입 금지
- gstack 기본: 최종 커밋에 `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` 삽입
- **팀 규칙**: Co-Authored-By 관련 문구 일체 삽입 금지
- `/ship`, `/land-and-deploy` 등 모든 커밋에서 제거

### PR 타이틀 형식
- gstack 기본: `<type>: <summary>`
- **팀 규칙**: `[{이슈ID}] 작업 요약`

## 배포 오버라이드

### 프로덕션 배포 사람 승인 필수
- gstack `/land-and-deploy`의 자동 배포 기능 사용 금지
- staging 배포 → staging 검증 → 프로덕션 요청 → 승인 → 프로덕션 배포 절차 준수
- `/land-and-deploy` 사용 시 merge까지만 수행, 프로덕션 배포는 사람에게 위임

### DB/SP 변경 별도 승인
- `/ship` PR에 DB/SP 변경이 포함된 경우 PR 본문에 명시
- 영향 테이블, 입출력 계약, 롤백 스크립트, 스모크 테스트 시나리오 포함

## 코드 리뷰 오버라이드

### 리뷰어 승인 필수
- gstack `/review`는 자동 수정 적용 가능하나, PR merge는 최소 1명 리뷰어 승인 필요
- 셀프 리뷰 불가

### 레거시 경계 확인
- `/review`, `/cso` 실행 시 서비스 하네스의 `LEGACY_BOUNDARY.md` 참조
- SP 직접 호출 금지 정책 준수 여부 점검

## 보안 오버라이드

### AWS Secrets 컨벤션
- `/cso` 실행 시 `sm-{service}-{module}-{environment}-{resource}` 네이밍 준수 확인
- 시크릿 값 로깅 금지, 민감 필드 마스킹 확인

## Retro 오버라이드

### 커밋 분류
- gstack 기본: conventional commits (feat/fix/refactor 등) 기준 분류
- **팀 규칙**: 커밋 메시지가 `[이슈ID]` 형식이므로, YouTrack 이슈 타입 기준으로 분류
- 이슈 ID에서 프로젝트 코드 추출하여 서비스별 분석 지원

## 적용 범위

이 정책은 gstack의 모든 스킬에 적용된다:
- `/ship`, `/land-and-deploy`: Git 컨벤션, 배포 오버라이드
- `/review`, `/cso`: 코드 리뷰, 보안 오버라이드
- `/retro`: Retro 오버라이드
- `/qa`, `/qa-only`: 레거시 경계 확인
- 기타 스킬: 팀 정책 우선 원칙 적용
