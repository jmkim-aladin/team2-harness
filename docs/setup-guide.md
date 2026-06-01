# 팀 하네스 셋업 가이드

## 구조 이해

```
~/.claude/commands/ad/  →  team2/.claude/commands/ad/ (심볼릭 링크)
~/.codex/AGENTS.md      →  team2/AGENTS.md (심볼릭 링크)
~/.codex/skills/*       →  team2/.codex/skills/* (심볼릭 링크)

어떤 서비스 레포에서든 Claude Code 실행 시:
├── 팀 스킬 (/ad:ticket 등)   ← 글로벌 ~/.claude/commands/ad/ 에서 로드
├── 서비스 CLAUDE.md           ← 현재 레포에서 로드
└── 서비스 코드                 ← 작업 대상

Codex 실행 시:
├── 팀 하네스 진입점            ← 글로벌 ~/.codex/AGENTS.md 에서 로드
├── Codex Skill                 ← 글로벌 ~/.codex/skills/* 에서 로드
└── 서비스 AGENTS.md            ← 현재 레포에서 로드
```

- **team2 레포에서 실행할 필요 없음** — 팀 스킬은 심볼릭 링크로 어디서든 사용 가능
- **각 서비스 레포에서 평소처럼 Claude Code/Codex 실행** — 코드 작업 + 팀 스킬 모두 사용
- **team2 레포**는 스킬/정책의 source of truth — 스킬 수정은 여기서 PR로 관리

---

## 셋업 (1회)

### 자동 셋업

```bash
git clone https://github.com/AladinCommunication/team2.git
cd team2
./scripts/setup.sh
```

스크립트가 자동으로:
1. `TEAM2_HARNESS_PATH`, `YOUTRACK_BASE_URL` 등록
2. Claude Code `/ad` command 심볼릭 링크 생성
3. Codex `AGENTS.md`와 Skill 심볼릭 링크 생성
4. YouTrack 토큰 설정 확인
5. gh CLI 설치/인증 확인

### 수동 셋업

#### 1. 레포 클론
```bash
git clone https://github.com/AladinCommunication/team2.git
```

#### 2. 팀 스킬 심볼릭 링크
```bash
# 기존 ad/ 디렉토리가 있으면 백업
mv ~/.claude/commands/ad ~/.claude/commands/ad.bak 2>/dev/null

# 심볼릭 링크 생성
ln -s /path/to/team2/.claude/commands/ad ~/.claude/commands/ad
```

#### 3. Codex 하네스 링크
```bash
mkdir -p ~/.codex/skills
mv ~/.codex/AGENTS.md ~/.codex/AGENTS.md.bak 2>/dev/null
ln -s /path/to/team2/AGENTS.md ~/.codex/AGENTS.md

for skill in /path/to/team2/.codex/skills/*; do
  name="$(basename "$skill")"
  mv "$HOME/.codex/skills/$name" "$HOME/.codex/skills/$name.bak" 2>/dev/null
  ln -s "$skill" "$HOME/.codex/skills/$name"
done
```

#### 4. YouTrack 토큰 등록
`~/.claude/settings.json`의 `env`에 추가:
```json
{
  "env": {
    "YOUTRACK_TOKEN": "perm-XXXX"
  }
}
```
토큰 발급: https://aladincommunication.youtrack.cloud > Profile > Account Security > New Token

> 팀 스킬은 YouTrack을 REST API(`curl` + `$YOUTRACK_TOKEN`)로만 호출한다. MCP 서버는 사용하지 않는다.

#### 5. gh CLI
```bash
brew install gh
gh auth login
```

---

## 서비스 레포 연결

각 서비스 레포의 CLAUDE.md에 팀 하네스 참조가 필요합니다.

### 이미 연결된 서비스
- naru (`NaruServer/CLAUDE.md`)
- max (`max-doc/CLAUDE.md`)
- bazaar (`BazaarServer/CLAUDE.md`)
- tobe (`tobe-project/CLAUDE.md`)
- aasm (`s3manager/CLAUDE.md`)

### 새 서비스 연결

CLAUDE.md 상단에 팀 하네스 섹션을 추가합니다:

```markdown
## 팀 하네스

> 이 서비스는 개발 2팀 하네스를 따릅니다.

| 정책 | 파일 |
|------|------|
| 엔지니어링 총칙 | `$TEAM2_HARNESS_PATH/policies/engineering-policy.md` |
| 브랜치/커밋 규칙 | `$TEAM2_HARNESS_PATH/policies/branching-strategy.md` |
| 코드 리뷰 기준 | `$TEAM2_HARNESS_PATH/policies/code-review-policy.md` |
| 배포/릴리즈 | `$TEAM2_HARNESS_PATH/policies/release-policy.md` |
| AI 사용 원칙 | `$TEAM2_HARNESS_PATH/policies/ai-usage-policy.md` |
| 보안 | `$TEAM2_HARNESS_PATH/policies/security-policy.md` |
| 서비스 프로파일 | `$TEAM2_HARNESS_PATH/catalog/{서비스ID}.yaml` |
| 팀원 | `$TEAM2_HARNESS_PATH/policies/team-members.md` |
```

레거시 서비스는 추가로:
```markdown
| 현대화 정책 | `$TEAM2_HARNESS_PATH/policies/legacy-modernization-policy.md` |
```

상세: [service-harness-setup.md](./service-harness-setup.md)

---

## 사용법

### 어떤 서비스 레포에서든

```bash
cd ~/workspace/max-api     # 또는 NaruServer, BazaarServer 등
claude                      # Claude Code 실행

# 팀 스킬 사용 가능
/ad:ticket                  # 티켓 생성
/ad:code-review 123         # PR 리뷰
/ad:team2-kb-read REF-A-625 # KB 문서 조회
```

### team2 레포에서

```bash
cd ~/workspace/team2
claude

# 팀 스킬 + 하네스 정책/카탈로그 직접 접근
/ad:team2-kb-list           # KB 문서 목록
/ad:team2-kb-sync           # KB → 하네스 동기화
```

### 언제 어디서 실행?

| 작업 | 실행 위치 | 이유 |
|------|-----------|------|
| 코드 개발/수정 | 서비스 레포 | 코드 컨텍스트 필요 |
| PR 리뷰 | 서비스 레포 | 코드 diff 필요 |
| 티켓 생성 | 아무 레포 | 팀 스킬로 어디서든 가능 |
| KB 조회 | 아무 레포 | 팀 스킬로 어디서든 가능 |
| 하네스 정책 수정 | team2 레포 | 정책 파일이 여기에 있음 |
| 스킬 수정 | team2 레포 | 스킬 마스터가 여기에 있음 |
| 서비스 카탈로그 갱신 | team2 레포 | 카탈로그가 여기에 있음 |

---

## 스킬 업데이트

team2 레포에서 스킬이 업데이트되면:
```bash
cd ~/workspace/team2
git pull    # 최신 스킬 가져오기
```
심볼릭 링크이므로 **즉시 반영** — 별도 작업 불필요.

---

## 설정 파일 요약

| 파일 | 위치 | 공유 | 내용 |
|------|------|------|------|
| `.claude/commands/ad/*.md` | team2 레포 | 팀 (git → symlink) | 팀 스킬 정의 |
| `~/.claude/settings.json` | 개인 홈 | 개인 | `YOUTRACK_TOKEN`, `YOUTRACK_BASE_URL`, `TEAM2_HARNESS_PATH` |
| `~/.claude/commands/ad` | 개인 홈 | symlink → team2 | 팀 스킬 자동 연결 |
| `~/.codex/AGENTS.md` | 개인 홈 | symlink → team2 | Codex용 팀 하네스 진입점 |
| `~/.codex/skills/dev2-team-harness-ko` | 개인 홈 | symlink → team2 | Codex용 개발2팀 하네스 Skill |
| `~/.codex/skills/dev2-ad-commands-ko` | 개인 홈 | symlink → team2 | Codex용 `/ad:*` 호환 Skill |
| `~/.codex/skills/youtrack-ticket-5w1h-ko` | 개인 홈 | symlink → team2 | Codex용 DEV2 티켓 Skill |

## Codex 사용

Codex는 Claude Code의 `.claude/commands/ad/*.md`를 자동 명령으로 로드하지 않는다.
Codex에서는 `~/.codex/skills/*`에 연결된 얇은 Skill이 team2의 command 파일을 읽어서 같은 하네스 기준을 적용한다.

| 요청 | Codex Skill |
|------|-------------|
| 개발2팀 정책, 카탈로그, KB, OKR, 주간업무, 코드리뷰 | `$dev2-team-harness-ko` |
| `/ad:ticket`, DEV2 티켓 생성/초안 | `$youtrack-ticket-5w1h-ko` |
| Claude Code `/ad:*` 명령 전체 | `$dev2-ad-commands-ko` |

Codex Skill도 YouTrack은 REST API(`$YOUTRACK_TOKEN`)로만 호출한다.

---

## 스킬별 필요 설정

| 스킬 | YouTrack 토큰 | gh CLI |
|------|:---:|:---:|
| `/ad:ticket` | O | - |
| `/ad:code-review` | - | O |
| `/ad:team2-kb-read` | O | - |
| `/ad:team2-kb-list` | O | - |
| `/ad:team2-kb-sync` | O | - |

---

## 문제 해결

| 증상 | 원인 | 해결 |
|------|------|------|
| `/ad:ticket`이 안 보임 | Claude Code 심볼릭 링크 없음 | `./scripts/setup.sh` 실행 |
| Codex에서 `/ad:*`가 하네스를 안 따름 | `~/.codex/skills/*` 링크 없음 또는 세션 재시작 필요 | `./scripts/setup.sh` 실행 후 Codex 재시작 |
| KB 조회 시 인증 오류 | `YOUTRACK_TOKEN` 미설정 | `~/.claude/settings.json` env 확인 |
| 티켓 생성 시 401/403 | `YOUTRACK_TOKEN` 만료/오타 | YouTrack에서 토큰 재발급 후 settings.json 갱신 |
| PR 리뷰 시 gh 오류 | gh CLI 미설치/미인증 | `brew install gh` → `gh auth login` |
| 환경변수 적용 안 됨 | Claude Code 재시작 필요 | `/exit` 후 `claude` 다시 실행 |
| 스킬 업데이트 안 됨 | team2 pull 필요 | `cd team2 && git pull` |
