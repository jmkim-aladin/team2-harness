# 팀 스킬 목록

셋업용 안내다 — 스킬을 쓰기 전에 갖출 위치·인증만 적는다. 분류와 "언제 무엇을"은 [harness-guide.md](../docs/harness-guide.md) §작업 플로우의 4그룹(구상·개발·주기·상시) 하나뿐이고, 이 파일은 따로 분류하지 않는다 — 분류 체계가 둘이면 한쪽이 낡는다.

- 존재 여부: 디렉토리가 SoT — `ls .claude/commands/ad/`, Codex alias는 `ls .codex/skills/`
- 한 줄 설명: command 파일 frontmatter `description`. 맨 앞 `[그룹·단계]` 태그가 지도의 주 소속이라 `/ad:` 메뉴에서 바로 보인다
- 미구현 후보: harness-guide §스킬 목록

## 위치

| 종류 | 위치 |
|------|------|
| `/ad:*` 팀 스킬 (절차 SoT) | `.claude/commands/ad/` |
| Codex `$ad-*` alias | `.codex/skills/ad-*/` (repo-local, SoT를 읽는 얇은 alias) |
| 재피치 스킬 `eli5`·`eli5-html`·`eli5-onboard` | `.codex/skills/` (Claude·Codex 양쪽 링크) |
| 서비스 전용 스킬 (배포·마이그레이션 절차 등) | 각 서비스 하네스 repo |

## 필요 인증

| 인증 | 설정 방법 | 쓰는 스킬 |
|------|-----------|-----------|
| `YOUTRACK_TOKEN` | 개인 `~/.claude/settings.json` env에 추가 | YouTrack 티켓·KB·보고를 읽거나 쓰는 스킬 전부 |
| `YOUTRACK_BASE_URL` | 프로젝트 `.claude/settings.json` (설정됨) | 위와 같음 — API 베이스 URL |
| GitHub (gh CLI) | `brew install gh` → `gh auth login` | `/ad:code-review`·`/ad:code-review-self` |
| 교차 모델 CLI (codex 또는 claude, 선택) | 각 CLI 설치·로그인 | `/ad:code-review` 교차 모델 리뷰, `/ad:eng-review` 교차 모델 의견 |

인증 없이 로컬 위키·저장소만 읽는 스킬도 있다 — `/ad:plan`·`/ad:plan-run`·`/ad:explain`(`--tldr` 포함) 등.

## 재피치 스킬 (사용자 호출 전용)

원안은 [claude-plugins-community `eli5`](https://github.com/anthropics/claude-plugins-community/blob/main/eli5/skills/eli5/SKILL.md) 한 종. 즉답(파일 없음)과 공유물(파일 남음)은 출력 매체가 다르므로 둘로 갈랐다. 쓰는 상황은 지도 §4 상시 `이해` 행.

셋 다 `disable-model-invocation: true` — `/eli5`, `/eli5-html`, `/eli5-onboard`(Codex는 `$` 접두)로 사람이 부를 때만 돈다. 다른 스킬 절차에서 이 규율이 필요하면 이름으로 부르지 말고 `.codex/skills/eli5/SKILL.md`를 읽어 수행한다.

`eli5-onboard`는 대상이 주제가 아니라 **저장소 하나**다. 갈림: 독자가 도메인을 이미 알면 `/ad:explain --tldr`(현황 한 장), 처음 투입이면 이쪽(학습 경로).

## Codex 호환

Codex는 `.claude/commands/ad/*.md`를 slash command로 직접 로드하지 않는다.
Codex Skill은 team2 레포의 `.codex/skills/*`에 repo-local로 두고, 같은 command 파일을 읽어서 절차를 수행한다.
전역 `~/.codex/skills/*`에는 team2 전용 스킬을 복제하거나 symlink하지 않는다.

| Codex Skill | 역할 |
|-------------|------|
| `dev2-team-harness-ko` | 정책/카탈로그/KB/스프린트 등 team2 컨텍스트 로드 |
| `dev2-ad-commands-ko` | `/ad:*` 전체를 `.claude/commands/ad/{name}.md`에 위임 |
| `youtrack-ticket-5w1h-ko` | `/ad:ticket` 티켓 작성 진입점 |
| `eli5` / `eli5-html` | 엔진 스킬 — Codex·Claude 양쪽에 같은 SKILL.md가 링크된다 |
