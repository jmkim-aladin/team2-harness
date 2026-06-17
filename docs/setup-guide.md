# 팀 하네스 셋업 가이드

## 구조 이해

```
~/.claude/commands/ad/  →  team2/.claude/commands/ad/ (심볼릭 링크)

어떤 서비스 레포에서든 Claude Code 실행 시:
├── 팀 스킬 (/ad:ticket 등)   ← 글로벌 ~/.claude/commands/ad/ 에서 로드
├── 서비스 CLAUDE.md           ← 현재 레포에서 로드
└── 서비스 코드                 ← 작업 대상

team2 레포에서 Codex 실행 시:
├── 팀 하네스 진입점            ← repo-local AGENTS.md 에서 로드
├── Codex Skill                 ← ~/.codex/skills/* → team2/.codex/skills/* symlink
└── 팀 하네스 파일              ← 현재 레포에서 로드

어떤 터미널에서든 Claude Code 실행 시:
├── 팀 스킬 (/ad:ticket 등)     ← 글로벌 ~/.claude/commands/ad/ symlink
└── Claude Code Skill           ← ~/.claude/skills/* → team2/.codex/skills/* symlink
```

- **Claude Code는 team2 레포에서 실행할 필요 없음** — `/ad` command는 심볼릭 링크로 어디서든 사용 가능
- **Codex는 repo-local 진입점 + 전역 Skill symlink 기준** — team2 전용 Skill은 team2 레포의 `.codex/skills/*`가 source of truth
- **team2 레포**는 스킬/정책의 source of truth — 스킬 수정은 여기서 PR로 관리
- **Skill은 전역 홈에 복제하지 않음** — `~/.codex/skills/*`, `~/.claude/skills/*`에는 team2 원본을 가리키는 symlink만 둔다

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
3. `~/.codex/skills/*`, `~/.claude/skills/*`에 team2 Skill 심볼릭 링크 생성
4. YouTrack 토큰 설정 확인
5. gh CLI 설치/인증 확인

터미널 control pane에서 `team2-agent`를 짧게 쓰려면 shell profile에 team2 `bin/`을 추가한다.

```bash
export PATH="/Users/jm/Documents/workspace/team2/bin:$PATH"
```

확인:

```bash
team2-agent board
team2-agent cockpit
team2-agent cycle
```

herdr를 로컬 작업실로 쓸 때는 hook을 한 번 설치하고 `team2-orchestration` space를 연다.

```bash
team2-agent herdr doctor
team2-agent herdr install-hooks
team2-agent herdr open
team2-agent herdr tickets --service max --concurrency 4 DEV2-6509 DEV2-6510
```

`open` 후에는 `team2-orchestration` space의 `global-orchestrator` pane에 자연어로 지시한다. herdr 계층은 `space=오케스트레이션/서비스 경계`, `tab=티켓/작업 단위`, `pane=임시 role agent`로 쓴다. 여러 티켓을 병렬 분석할 때는 orchestrator가 서비스 판정에 필요한 최소 정보만 확인해 서비스 space에 티켓별 tab을 만들고, 티켓 상세 정리와 상태 판단은 각 tab의 `ticket-lead`가 맡는다. `ticket-lead`는 업무 유형에 따라 analyst/developer/reviewer/QA/designer/data/architect role agent를 필요한 만큼만 띄운다. Hermes board와 desktop cockpit은 상시 패널이 아니라 orchestrator가 필요할 때 조회하는 내부 상태 도구다. `team2-agent brief ...` 같은 내부 명령은 사용자가 직접 치기보다 orchestrator가 필요할 때 실행한다.

```text
지금 내가 결정해야 할 것만 순서대로 보여줘.
DEV2-6509는 자동결제인지 재가입인지 판단해서 선택지만 줘.
이건 A안으로 결정하고 나머지는 진행해.
```

이미 herdr 안에서 실행 중이거나 화면 attach 없이 workspace만 준비하려면 `team2-agent herdr open --no-attach`를 사용한다.

동시에 맡길 비서비스 작업이 더 많으면 orchestrator가 아래 형식으로 작업 단위 worker를 동적으로 띄운다. instruction이 있는 worker는 결과를 읽은 뒤 자동으로 pane을 닫는다.

```bash
team2-agent herdr worker orch-worker-3 "분석 범위와 산출물 기준을 정리해줘"
```

ticket-lead가 cell 안의 협업자를 직접 띄워야 할 때는 아래 형식을 사용한다.

```bash
team2-agent herdr role --service max DEV2-6509 analyst "요구사항과 코드 진입점 분석"
```

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

#### 3. Codex / Claude Code Skill 심볼릭 링크
```bash
for skill in /path/to/team2/.codex/skills/*; do
  name="$(basename "$skill")"
  ln -sfn "$skill" "$HOME/.codex/skills/$name"
  ln -sfn "$skill" "$HOME/.claude/skills/$name"
done

if [ -L "$HOME/.codex/AGENTS.md" ] &&
   [ "$(readlink "$HOME/.codex/AGENTS.md")" = "/path/to/team2/AGENTS.md" ]; then
  rm "$HOME/.codex/AGENTS.md"
fi
```

team2 스킬 원본은 team2 레포의 `.codex/skills/*`다. 전역 홈에는 복제하지 않고 symlink만 둔다.

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
Claude Code `/ad` command와 Codex/Claude Code Skill은 심볼릭 링크이므로 즉시 반영된다. 새 터미널 또는 새 세션에서 목록이 갱신된다.

---

## 설정 파일 요약

| 파일 | 위치 | 공유 | 내용 |
|------|------|------|------|
| `.claude/commands/ad/*.md` | team2 레포 | 팀 (git → symlink) | 팀 스킬 정의 |
| `~/.claude/settings.json` | 개인 홈 | 개인 | `YOUTRACK_TOKEN`, `YOUTRACK_BASE_URL`, `TEAM2_HARNESS_PATH` |
| `~/.claude/commands/ad` | 개인 홈 | symlink → team2 | 팀 스킬 자동 연결 |
| `~/.claude/skills/ad-*` | 개인 홈 | symlink → team2 | Claude Code Skill 자동 연결 |
| `~/.codex/skills/ad-*` | 개인 홈 | symlink → team2 | Codex Skill 자동 연결 |
| `AGENTS.md` | team2 레포 | 팀 (git) | Codex용 팀 하네스 진입점 |
| `.codex/skills/dev2-team-harness-ko` | team2 레포 | 팀 (git) | Codex용 개발2팀 하네스 Skill |
| `.codex/skills/dev2-ad-commands-ko` | team2 레포 | 팀 (git) | Codex용 `/ad:*` 호환 Skill |
| `.codex/skills/youtrack-ticket-5w1h-ko` | team2 레포 | 팀 (git) | Codex용 DEV2 티켓 Skill |

## Codex 사용

Codex는 Claude Code의 `.claude/commands/ad/*.md`를 자동 명령으로 로드하지 않는다.
Codex에서는 team2 레포의 `.codex/skills/*`에 있는 얇은 Skill이 team2의 command 파일을 읽어서 같은 하네스 기준을 적용한다.

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
| Codex에서 `ad-*` Skill이 안 보임 | `~/.codex/skills/ad-*` symlink 없음 또는 세션 재시작 필요 | `./scripts/setup.sh` 실행 후 Codex 재시작 |
| Claude Code에서 `ad-*` Skill이 안 보임 | `~/.claude/skills/ad-*` symlink 없음 또는 세션 재시작 필요 | `./scripts/setup.sh` 실행 후 Claude Code 재시작 |
| Codex에서 `/ad:*`가 하네스를 안 따름 | AGENTS 로드 안 됨 또는 세션 재시작 필요 | `TEAM2_HARNESS_PATH` 확인 후 Codex 재시작 |
| KB 조회 시 인증 오류 | `YOUTRACK_TOKEN` 미설정 | `~/.claude/settings.json` env 확인 |
| 티켓 생성 시 401/403 | `YOUTRACK_TOKEN` 만료/오타 | YouTrack에서 토큰 재발급 후 settings.json 갱신 |
| PR 리뷰 시 gh 오류 | gh CLI 미설치/미인증 | `brew install gh` → `gh auth login` |
| 환경변수 적용 안 됨 | Claude Code 재시작 필요 | `/exit` 후 `claude` 다시 실행 |
| 스킬 업데이트 안 됨 | team2 pull 필요 | `cd team2 && git pull` |
