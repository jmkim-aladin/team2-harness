# 팀 스킬 목록

## 네임스페이스

| 네임스페이스 | 용도 | 위치 |
|-------------|------|------|
| `ad:` | 개발 2팀 공통 스킬 | `.claude/commands/ad/` (이 레포) |
| `ad:team2` | 팀 운영 스킬 (하네스, KB 연동 등) | `.claude/commands/ad/` (이 레포) |
| Codex Skill | Codex용 team2 하네스 진입점 | `.codex/skills/` (이 레포, repo-local) |
| 재피치 스킬 | 명시 호출 전용 설명 스킬 | `.codex/skills/` (이 레포, Claude·Codex 양쪽 링크) |

## 필요 인증

| 인증 | 설정 방법 | 용도 |
|------|-----------|------|
| `YOUTRACK_TOKEN` | 개인 `~/.claude/settings.json` env에 추가 | YouTrack KB 조회, 티켓 생성 |
| `YOUTRACK_BASE_URL` | 프로젝트 `.claude/settings.json` (설정됨) | YouTrack API 베이스 URL |
| GitHub (gh CLI) | `brew install gh` → `gh auth login` | PR 리뷰, GitHub 연동 |

## 스킬 목록

### ad: (공통 — 일상 업무)

| 스킬 | 설명 | 인증 | 상태 |
|------|------|------|------|
| `ad:ticket` | YouTrack 티켓 생성 (5W1H) | YouTrack | 구현됨 |
| `ad:plan` | grill 결과를 vault 다세션 계획·진행 원장으로 합성 | - | 구현됨 |
| `ad:plan-run` | vault 계획의 internal milestone 하나를 실행하고 진행·근거 기록 | - | 구현됨 |
| `ad:work-prep` | 티켓번호/자유글 → 로컬 위키 노트 + daily 아젠다 + 브랜치 제안 | YouTrack | 구현됨 |
| `ad:code-review` | GitHub PR 코드 리뷰 (이해 패스 → 팀 체크리스트 판정 → 교차 모델 검증 → 승인 조건 게이트) | gh CLI, 교차 모델 CLI (codex 또는 claude) | 구현됨 |
| `ad:tldr` | 저장소·프로젝트 한 페이지 아키텍처 개요(TL;DR) 작성 | - | 구현됨 |
| `ad:explain` | 코드 변경·분석 결과 설명서 (배경→직관→본체→퀴즈, md + HTML) | - | 구현됨 |
| `ad:ticket-split` | 2일 초과 이슈 자식 분할 | YouTrack | 미구현 |
| `ad:time-log` | 소요시간 기록 | YouTrack | 미구현 |
| `ad:status-update` | 티켓 상태 전환 + 검증 | YouTrack | 미구현 |
| `ad:daily-report` | 일일 작업 요약 | YouTrack | 미구현 |
| `ad:sprint-plan` | 스프린트 계획 보조 | YouTrack | 미구현 |

### ad:team2 (팀 운영 — 하네스/KB/관리)

| 스킬 | 설명 | 인증 | 상태 |
|------|------|------|------|
| `ad:team2-kb-read` | YouTrack KB 문서 조회/검색 | YouTrack | 구현됨 |
| `ad:team2-onboard` | 신규 서비스 하네스 생성 (템플릿 적용) | - | 미구현 |
| `ad:team2-catalog` | 서비스 카탈로그 조회/갱신 | - | 미구현 |
| `ad:team2-harness-check` | 서비스 하네스 완성도 점검 | - | 미구현 |
| `ad:team2-members` | 팀원/담당 서비스 조회 | - | 미구현 |

### 재피치 스킬 (사용자 호출 전용)

| 스킬 | 설명 | 인증 | 상태 |
|------|------|------|------|
| `eli5` | 주제·확정된 결론을 무지 독자 눈높이로 터미널 재피치 (구체 사례 + ASCII 그림) | - | 구현됨 |
| `eli5-html` | 같은 설명을 공유용 자족 HTML 한 장으로 (인라인 SVG, 400단어 이하) | - | 구현됨 |
| `eli5-onboard` | 낯선 저장소를 도메인 지식 0에서 심화까지 밟는 단계별 온보딩 커리큘럼으로 | - | 구현됨 |

원안은 [claude-plugins-community `eli5`](https://github.com/anthropics/claude-plugins-community/blob/main/eli5/skills/eli5/SKILL.md) 한 종. 즉답(파일 없음)과 공유물(파일 남음)은 출력 매체가 다르므로 둘로 갈랐다.

셋 다 `disable-model-invocation: true` — `/eli5`, `/eli5-html`, `/eli5-onboard`(Codex는 `$` 접두)로 사람이 부를 때만 돈다. 다른 스킬 절차에서 이 규율이 필요하면 이름으로 부르지 말고 `.codex/skills/eli5/SKILL.md`를 읽어 수행한다.

`eli5-onboard`는 대상이 주제가 아니라 **저장소 하나**다. 갈림: 독자가 도메인을 이미 알면 `/ad:tldr`(현황 한 장), 처음 투입이면 이쪽(학습 경로).

### 서비스별 스킬 (서비스 하네스에서 추가)

| 스킬 | 설명 |
|------|------|
| `ad:deploy` | 서비스별 배포 절차 |
| `ad:migration` | DB 마이그레이션 가이드 |
| `ad:api-check` | API 스펙 정합성 검증 |
| `ad:env-setup` | 로컬 환경 셋업 가이드 |

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
