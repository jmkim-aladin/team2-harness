---
description: GitHub PR 코드 리뷰 (팀 하네스 기준)
model: sonnet
---

# GitHub PR 코드 리뷰

팀 하네스 기준에 따라 GitHub PR을 리뷰하고 pending review로 코멘트를 게시합니다.

## 검증 순서

[policies/hypothesis-verification-order.md](../../../policies/hypothesis-verification-order.md) 적용 — "이거 맞나요?"류 질문 코멘트 달기 전에 콜그래프/grep + dev DB 읽기 쿼리로 답이 나오는지 먼저 확인. 잔여 의문만 작성자에게 질의 코멘트로 남긴다. dev DB 읽기는 사전 동의 ([local-credentials-policy.md](../../../policies/local-credentials-policy.md)).

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

### 실행 모드

이 스킬은 다수의 `gh` 호출과 마지막 리뷰 게시까지 포함하므로, **세션 시작 시 `--dangerously-skip-permissions` 로 진입하는 것을 권장**한다.

```bash
claude --dangerously-skip-permissions
```

- 권한 프롬프트가 모두 우회되므로, 게시 직전 단계에서 스킬이 보여주는 **미리보기를 사용자가 검토**하는 것이 유일한 게이트가 된다.
- 미리보기 단계에서 사용자가 "이대로 게시"라고 답해야만 `gh api ... POST` 를 실행한다 — 이 규칙은 권한 모드와 무관하게 지킨다.
- 일반 모드로 실행했다면 `.claude/settings.local.json` 의 `Bash(gh pr view:*)` / `Bash(rtk gh pr view:*)` 계열 화이트리스트로 읽기 명령은 통과하고, 게시 명령은 사용자 확인을 거친다.

### 도구 점검

```bash
# gh CLI 설치 확인
gh --version

# 인증 확인
gh auth status
```

gh CLI가 없으면 설치 안내: https://cli.github.com/ (`brew install gh`)
인증이 안 되어 있으면: `gh auth login`

## 실행 지침

### 0. 입력 파싱 — 항상 `--repo` 명시

하네스 워킹디렉터리(`team2`)는 대상 레포가 아니므로, gh 호출에는 **반드시 `--repo {owner}/{name}`을 붙인다.** 추론 실패 시 사용자에게 묻고 진행한다.

| 입력 형태 | 처리 |
|----------|------|
| `https://github.com/{owner}/{repo}/pull/{N}` | URL에서 `{owner}/{repo}`와 `{N}` 추출 → `--repo {owner}/{repo}` 사용 |
| 숫자만 (`1308`) | `catalog/*.yaml`의 `repos:` 매핑에서 후보를 모은 뒤 `AskUserQuestion`으로 어느 레포인지 확인 |
| `{owner}/{repo}#{N}` 또는 `{repo}#{N}` | 같은 방식으로 owner/repo 해석 |

레포 해석 결과는 **수집 단계 첫 출력**으로 사용자에게 한 줄 노출한다. PR 정보 조회(1단계) 후 머지 방향(`headRefName` → `baseRefName`)과 **PR 작성자(`author.login`/`author.name`)**를 함께 표기해 어느 브랜치가 어느 브랜치로 머지되는지, 누구 요청인지 드러낸다 (예: `대상: AladinCommunication/max-front #1308 (feature/DEV2-1234 → develop) · 작성자: 안혜련(00HyeRyun00)`). 잘못 매핑되거나 머지 대상 브랜치가 예상과 다르면 조기 중단 가능하도록.

### 1. PR 정보 수집

```bash
# PR 기본 정보 + 최신 커밋 SHA (한 번에 조회)
gh pr view {N} --repo {owner}/{repo} --json title,body,author,baseRefName,headRefName,commits,files,additions,deletions

# 변경 파일 목록 (이름만)
gh pr diff {N} --repo {owner}/{repo} --name-only

# 전체 diff (코드 리뷰용)
gh pr diff {N} --repo {owner}/{repo}
```

> `--repo` 누락 시 현재 디렉터리(하네스)의 remote를 따라가 엉뚱한 레포 조회나 실패가 발생한다. 항상 명시한다.

### 2. 팀 하네스 기준 리뷰

PR을 아래 기준으로 리뷰합니다. `policies/code-review-policy.md` 참조.

#### 리뷰 제외 항목 (지적 금지)
- **티켓 ID 불일치**: PR/브랜치의 feature ID와 커밋의 task ID가 다른 것은 정상. 팀 관행에 따른 것이므로 지적하지 않는다.
- **PR 본문 형식**: PR 템플릿(`templates/pr-template.md`)은 아직 확정되지 않은 초안. 형식 준수 여부를 차단 이슈로 다루지 말 것.

#### 기본 체크
- [ ] 요구사항(티켓)과 일치하는가
- [ ] 테스트가 포함되어 있는가
- [ ] 기존 컨벤션을 따르는가

#### 운영 영향 체크
- [ ] DB/SP 변경이 있는가 → 별도 승인 필요 (단, 프론트엔드 전용 서비스 PR은 체크 대상에서 제외)
- [ ] 외부 시스템 연동 변경이 있는가
- [ ] 레거시 경계를 넘는 변경이 있는가 → LEGACY_BOUNDARY.md 확인
- [ ] 롤백 방법이 명시되어 있는가

#### 현대화 체크
- [ ] 신규 코드에서 레거시 DB/SP 직접 접근이 없는가 (백엔드/API/배치/DB 레포만 해당)
- [ ] adapter를 통해 접근하는가
- [ ] 서비스 하네스 갱신이 필요한 변경인가

#### 서비스별 DB/SP 체크 적용
- 프론트엔드 전용 서비스 PR은 DB/SP 변경 여부와 SP 직접 접근 여부를 리뷰 체크포인트에서 제외한다.
- 백엔드/API/배치/DB 스크립트 레포 또는 프론트 PR에 DB 스크립트·SP 호출 계약 변경이 함께 포함된 경우에는 DB/SP 체크를 적용한다.

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

#### 로컬 하네스 정보 노출 금지

GitHub에 게시하는 코멘트/리뷰 본문에는 로컬 하네스 내부 정보를 노출하지 않는다.

- ❌ `policies/*.md`, `catalog/*.yaml`, `templates/*.md` 같은 내부 경로 직접 언급
- ❌ 하네스 파일명·디렉터리 구조·내부 정책 문서명 그대로 인용
- ✅ 근거는 일반화된 표현으로 전달 (예: "팀 코드리뷰 정책", "서비스 카탈로그", "외부 연동 의존성 문서")
- ✅ 개선 제안은 "하네스 갱신 필요" 정도로 표기하고, 구체적인 파일/경로는 미리보기(로컬)에만 표시

미리보기(사용자 확인용)에는 로컬 경로를 표시해도 되지만, 실제 게시 본문에서는 위 규칙을 따른다.

발견한 이슈를 정리하여 사용자에게 **미리보기** 표시:

```
## PR #{번호} 리뷰 결과
머지: {headRefName} → {baseRefName}
작성자: {author.name}({author.login})

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

**중요: `gh api -f 'comments[][...]'` 반복 브래킷 폼 인코딩은 금지.**
GitHub API가 `side` 필드를 인식 못 하거나 배열 인덱스를 잘못 매핑해 422 에러가 난다.
**반드시 JSON 페이로드를 stdin/파일로 전달한다.**

#### 5-A. 인라인 코멘트 **없을 때** (단순 APPROVE/COMMENT/REQUEST_CHANGES)

`gh pr review` 명령 한 줄로 끝.

```bash
# APPROVE
gh pr review {N} --repo {owner}/{repo} --approve --body "{전체 메시지}"

# REQUEST_CHANGES
gh pr review {N} --repo {owner}/{repo} --request-changes --body "{전체 메시지}"

# COMMENT
gh pr review {N} --repo {owner}/{repo} --comment --body "{전체 메시지}"
```

#### 5-B. 인라인 코멘트 **포함**할 때

JSON 페이로드를 작성 후 한 번에 review를 POST한다 (event를 같이 보내면 별도 submit 단계 불필요).

```bash
# 1. JSON 페이로드 작성 (임시 파일)
cat > /tmp/review-{N}.json <<'EOF'
{
  "commit_id": "{SHA}",
  "event": "APPROVE",
  "body": "{전체 메시지}",
  "comments": [
    {"path": "src/foo.ts", "line": 42, "side": "RIGHT", "body": "{코멘트 1}"},
    {"path": "src/bar.ts", "line": 10, "side": "RIGHT", "body": "{코멘트 2}"}
  ]
}
EOF

# 2. 게시
gh api repos/{owner}/{repo}/pulls/{N}/reviews \
  -X POST \
  --input /tmp/review-{N}.json \
  --jq '{id, state}'

# 3. 임시 파일 정리
rm /tmp/review-{N}.json
```

**페이로드 작성 규칙:**
- `event` 값은 `APPROVE` / `REQUEST_CHANGES` / `COMMENT` 중 하나 (event를 함께 보내면 즉시 submit 됨)
- 각 comment 객체는 `path`, `line`, `body` 필수. `side`는 `RIGHT`(추가/수정된 줄) 또는 `LEFT`(삭제된 줄). 기본 `RIGHT`.
- 멀티라인 코멘트는 `start_line` 추가 (`line`은 끝줄).
- `body`가 빈 문자열인 코멘트는 페이로드에서 제외 (서버가 422 반환).
- JSON 문자열 안의 따옴표·줄바꿈은 반드시 이스케이프. 백틱·달러 기호는 heredoc `<<'EOF'`(단일 따옴표) 사용으로 셸 확장 차단.

#### 5-C. 게시 직후 확인

```bash
gh api repos/{owner}/{repo}/pulls/{N}/reviews --jq '.[-1] | {id, state, user: .user.login}'
```
`state`가 `APPROVED` / `CHANGES_REQUESTED` / `COMMENTED`로 나오면 성공.

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
