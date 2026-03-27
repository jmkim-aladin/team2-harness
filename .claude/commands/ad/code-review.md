# GitHub PR 코드 리뷰

팀 하네스 기준에 따라 GitHub PR을 리뷰하고 pending review로 코멘트를 게시합니다.

## 사용법

```
/ad:code-review {PR번호 또는 URL}
/ad:code-review 123
/ad:code-review https://github.com/AladinCommunication/max-api/pull/123
```

## 환경변수

| 변수 | 용도 | 설정 위치 |
|------|------|-----------|
| `GITHUB_TOKEN` | GitHub API 인증 (gh CLI) | `gh auth login`으로 설정 |
| `$YOUTRACK_TOKEN` | YouTrack KB/티켓 참조 | 개인 `~/.claude/settings.json` |
| `$YOUTRACK_BASE_URL` | YouTrack 베이스 URL | 프로젝트 `.claude/settings.json` |

## 사전 확인

리뷰 시작 전 반드시:
```bash
# gh CLI 설치 확인
gh --version

# 인증 확인
gh auth status
```

gh CLI가 없으면 설치 안내: https://cli.github.com/ (`brew install gh`)
인증이 안 되어 있으면: `gh auth login`

## 실행 지침

### 1. PR 정보 수집

```bash
# PR 기본 정보 + 최신 커밋 SHA (한 번에 조회)
gh pr view {PR번호} --json title,body,author,baseRefName,headRefName,commits,files,additions,deletions

# 변경 파일 목록 (이름만)
gh pr diff {PR번호} --name-only

# 전체 diff (코드 리뷰용)
gh pr diff {PR번호}
```

### 2. 팀 하네스 기준 리뷰

PR을 아래 기준으로 리뷰합니다. `policies/code-review-policy.md` 참조.

#### 기본 체크
- [ ] 요구사항(티켓)과 일치하는가
- [ ] 테스트가 포함되어 있는가
- [ ] 기존 컨벤션을 따르는가

#### 운영 영향 체크
- [ ] DB/SP 변경이 있는가 → 별도 승인 필요
- [ ] 외부 시스템 연동 변경이 있는가
- [ ] 레거시 경계를 넘는 변경이 있는가 → LEGACY_BOUNDARY.md 확인
- [ ] 롤백 방법이 명시되어 있는가

#### 현대화 체크
- [ ] 신규 코드에서 레거시 DB/SP 직접 접근이 없는가
- [ ] adapter를 통해 접근하는가
- [ ] 서비스 하네스 갱신이 필요한 변경인가

#### PR 체크리스트 확인 (`templates/pr-template.md`)
- [ ] 사용자 영향 명시
- [ ] DB/SP 영향 명시
- [ ] 외부 연동 영향 명시
- [ ] 레거시 경계 영향 명시
- [ ] 롤백 방법 명시
- [ ] 배포 후 확인 포인트 명시
- [ ] 하네스 갱신 필요 여부 확인

#### DB/SP 변경이 있는 경우 추가 확인
- [ ] 영향 테이블 목록
- [ ] 입력/출력 계약 변경 사항
- [ ] 롤백 스크립트
- [ ] 최소 재현 데이터셋
- [ ] smoke test 시나리오

### 3. 서비스 컨텍스트 참조

대상 레포가 어떤 서비스인지 `catalog/*.yaml`에서 확인하고:
- 해당 서비스의 기술 스택, 아키텍처 패턴에 맞는 리뷰
- LEGACY_BOUNDARY.md 위반 여부 확인 (레거시 서비스인 경우)
- 현대화 트랙(Observe/Wrap/Extract)에 맞는 방향인지 확인

### 4. 리뷰 코멘트 작성

발견한 이슈를 정리하여 사용자에게 **미리보기** 표시:

```
## PR #{번호} 리뷰 결과

### 하네스 체크리스트
✅ 기본: 티켓 일치, 테스트 포함, 컨벤션 준수
⚠️ 운영: DB/SP 변경 있음 — 롤백 스크립트 누락
❌ 현대화: 신규 코드에서 SP 직접 호출 발견

### 코드 코멘트 ({N}개)
1. {파일}:{줄} — {이슈 설명} [suggestion 포함]
2. ...

### 이벤트: {APPROVE / REQUEST_CHANGES / COMMENT}
### 전체 메시지: "{요약}"

→ 이대로 게시할까요?
```

### 5. 사용자 승인 후 게시

반드시 사용자 확인 후에만 게시합니다.

```bash
# Pending review 생성 (코멘트 포함)
gh api repos/{owner}/{repo}/pulls/{PR번호}/reviews \
  -X POST \
  -f commit_id="{SHA}" \
  -f 'comments[][path]={파일}' \
  -F 'comments[][line]={줄}' \
  -f 'comments[][side]=RIGHT' \
  -f 'comments[][body]={코멘트}' \
  --jq '{id, state}'

# Review 제출
gh api repos/{owner}/{repo}/pulls/{PR번호}/reviews/{REVIEW_ID}/events \
  -X POST \
  -f event="{APPROVE|REQUEST_CHANGES|COMMENT}" \
  -f body="{전체 메시지}"
```

## 이벤트 타입 선택 기준

| 이벤트 | 기준 |
|--------|------|
| `APPROVE` | 이슈 없거나 비차단 제안만 (스타일, 선택적 개선) |
| `REQUEST_CHANGES` | 차단 이슈 (보안, 버그, 레거시 경계 위반, DB/SP 롤백 누락) |
| `COMMENT` | 중립 피드백, 질문, 확인 요청 |

## 참조

- 코드 리뷰 정책: `policies/code-review-policy.md`
- PR 체크리스트: `templates/pr-template.md`
- DoD: `templates/dod-checklist.md`
- 서비스 카탈로그: `catalog/`
- 팀원 정보: `policies/team-members.md`
