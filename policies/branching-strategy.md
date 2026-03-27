# 브랜치 전략

> 전사 Git Flow 상세: [REF-A-625](https://aladincommunication.youtrack.cloud/articles/REF-A-625) (YouTrack KB)
> 필요 시 `/ad:team2-kb-read REF-A-625`로 조회 가능

[nvie Git Flow](https://nvie.com/posts/a-successful-git-branching-model/) 브랜칭 모델을 따릅니다.

## 브랜치 구조

```
master                        ← 항상 배포 가능한 상태
├── develop                   ← 현재 스프린트 통합 개발 브랜치
│   └── feature/{이슈ID}      ← 단위 기능 개발
├── release/{YYYY.M.N}        ← QA 및 안정화 (릴리즈 준비)
└── hotfix/{YYYY.M.N}         ← 긴급 수정 (릴리즈 단위)
```

## 브랜치 명명 규칙

브랜치명은 YouTrack **이슈 ID**로 생성합니다.
Feature 티켓이 있으면 Feature ID, 없으면 Task ID를 사용합니다.

| 브랜치 | 형식 | 예시 |
|--------|------|------|
| 기능 | `feature/{이슈ID}` | `feature/DEV2-1234` |
| 릴리즈 | `release/{YYYY.M.N}` | `release/2026.4.0` |
| 핫픽스 (릴리즈) | `hotfix/{YYYY.M.N}` | `hotfix/2026.4.1` |
| 핫픽스 (개별) | `hotfix/{이슈ID}` | `hotfix/DEV2-456` |
| 릴리즈 내 수정 | `release/{이슈ID}` | `release/DEV2-789` |
| Git Worktree | `feature/{이슈ID}` | 브랜치와 동일 |

### YouTrack VCS 통합

```
+:refs/heads/feature/*
+:refs/heads/release/*
+:refs/heads/hotfix/*
```

| 팀 | 프리픽스 | 예시 |
|----|----------|------|
| 개발2팀 | DEV2 | `feature/DEV2-123`, `release/DEV2-123`, `hotfix/DEV2-123` |

## 태그

릴리즈 버전을 태그로 관리하며, YouTrack의 수정 버전과 동일하게 유지합니다.

| 태그 | 의미 |
|------|------|
| `2026.4.0` | 2026년 4월 첫 번째 릴리즈 |
| `2026.4.1` | 2026년 4월 두 번째 릴리즈 (핫픽스) |

## 브랜치별 규칙

### master
- 항상 배포 가능한 상태 유지
- `release/*` 또는 `hotfix/*` 브랜치만 머지 가능
- 직접 푸시 금지

### develop
- 현재 스프린트의 통합 개발 브랜치
- `feature/*` → `develop`으로 PR
- 매일 새벽 Fortify 자동 수행, 결과는 release PR 전에 수정
- PR 전에 squash로 커밋 정리

### feature/*
- 단위 기능 개발 브랜치
- YouTrack 이슈 ID로 생성: `feature/DEV2-123`
- `feature/*` → `develop`으로 PR

### release/*
- QA 및 안정화 단계 — 모든 QA는 release 브랜치에서 수행
- 최대한 단일 브랜치로 운영
- 안정화 기간에 버그 수정 가능, 스펙 추가 불가
- `develop` → `release/YYYY.M.N`으로 PR
- 완료 후 `release/*` → `master`로 PR

### hotfix/*
- 긴급 수정용 릴리즈 단위 브랜치
- QA 생략 가능, 바로 master 반영 가능
- `hotfix/DEV2-123` → `hotfix/YYYY.M.N`으로 PR
- 완료 후 `hotfix/*` → `master`로 PR

## CI (PR 생성 시)

모든 브랜치에서 PR 생성 시 자동 수행:

1. Lint
2. Fortify
3. Unit Test
4. Sanity Test 및 통합 Test
5. 통과 시 머지 가능

## CD (머지 시)

### master 머지 시
1. 태그 등록 (`release/2026.4.0` → `2026.4.0`)
2. AWS 실서버 배포 (stage가 있으면 stage 우선)
3. YouTrack 버전별 시간 보고서 생성
4. YouTrack 지식베이스 릴리즈 노트 수정
5. GitHub Release 노트 작성

### release/hotfix 머지 시
1. AWS 테스트 서버 배포
2. 앱 테스트 배포

## 보호 규칙

- `master`, `release/*`는 protected branch
- PR 승인 + 필수 status check 통과 후에만 머지 가능
- staging/prod 배포는 GitHub Environments로 분리
- self-hosted runner 사용 시 PR 워크플로가 prod 배포 runner에 닿지 않게 격리

## 커밋 메시지

커밋 메시지는 YouTrack **Task 티켓 ID**를 포함합니다.

### 형식
```
[{Task 티켓ID}] {Task 티켓명 또는 작업 내용}
```

### 예시

```
[DEV2-1235] 프로필 조회 API 엔드포인트 추가
[DEV2-1236] 프로필 수정 API 및 유효성 검증
[DEV2-1237] 프로필 API 단위 테스트 추가
```

### 브랜치와 커밋의 관계

**Feature 하위에 Task가 있는 경우:**
```
Feature: DEV2-1234 "프로필 조회 및 수정 API 구현"
  ├── Task: DEV2-1235 "프로필 조회 API 추가"
  ├── Task: DEV2-1236 "프로필 수정 API"
  └── Task: DEV2-1237 "단위 테스트 추가"

브랜치: feature/DEV2-1234              ← Feature ID
커밋 1: [DEV2-1235] 프로필 조회 API      ← Task ID
커밋 2: [DEV2-1236] 프로필 수정 API      ← Task ID
커밋 3: [DEV2-1237] 단위 테스트 추가     ← Task ID
```

**Feature 없이 단독 Task인 경우:**
```
Task: DEV2-5678 "로그인 오류 수정"

브랜치: feature/DEV2-5678              ← Task ID
커밋:   [DEV2-5678] 로그인 오류 수정     ← Task ID
```

> 브랜치 = Feature ID (없으면 Task ID), 커밋 = 항상 작업 이슈 ID

### Squash Merge

develop PR 시 squash merge로 정리할 수 있습니다:
```bash
git checkout develop
git merge --squash feature/DEV2-1234
git commit -m "[DEV2-1234] 프로필 조회 및 수정 API 구현"
```

squash 시 커밋 메시지는 Feature 티켓 ID를 사용합니다.

## Git Worktree

병렬 작업이 필요할 때 worktree를 사용합니다. 브랜치 규칙과 동일하게 이슈 ID로 생성합니다.

```bash
# worktree 생성 (브랜치명과 동일)
git worktree add ../worktree-DEV2-1234 -b feature/DEV2-1234

# 작업 완료 후 정리
git worktree remove ../worktree-DEV2-1234
```

## 복수 릴리즈 시나리오

`release/2026.4.0`이 안정화 중이고 `release/2026.5.0`이 준비된 상태에서 `release/2026.4.0`에 수정이 필요하면:

1. `release/DEV2-123` → `release/2026.4.0`으로 PR
2. `release/2026.4.0` → `master` 머지 후
3. master 변경 사항을 release / develop / feature 브랜치에 모두 전파
