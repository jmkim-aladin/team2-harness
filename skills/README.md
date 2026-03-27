# 팀 스킬 목록

## 네임스페이스

| 네임스페이스 | 용도 | 위치 |
|-------------|------|------|
| `ad:` | 개발 2팀 공통 스킬 | `.claude/commands/ad/` (이 레포) |
| `ad:team2` | 팀 운영 스킬 (하네스, KB 연동 등) | `.claude/commands/ad/` (이 레포) |

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
| `ad:code-review` | GitHub PR 코드 리뷰 (팀 체크리스트 기반) | gh CLI | 구현됨 |
| `ad:ticket-split` | 2일 초과 이슈 자식 분할 | YouTrack | 미구현 |
| `ad:time-log` | 소요시간 기록 | YouTrack | 미구현 |
| `ad:status-update` | 티켓 상태 전환 + 검증 | YouTrack | 미구현 |
| `ad:daily-report` | 일일 작업 요약 | YouTrack | 미구현 |
| `ad:sprint-plan` | 스프린트 계획 보조 | YouTrack | 미구현 |

### ad:team2 (팀 운영 — 하네스/KB/관리)

| 스킬 | 설명 | 인증 | 상태 |
|------|------|------|------|
| `ad:team2-kb-read` | YouTrack KB 문서 조회/검색 | YouTrack | 구현됨 |
| `ad:team2-kb-list` | YouTrack KB 문서 트리 조회 | YouTrack | 구현됨 |
| `ad:team2-kb-sync` | KB 변경 시 하네스 정책 동기화 | YouTrack | 구현됨 |
| `ad:team2-onboard` | 신규 서비스 하네스 생성 (템플릿 적용) | - | 미구현 |
| `ad:team2-catalog` | 서비스 카탈로그 조회/갱신 | - | 미구현 |
| `ad:team2-harness-check` | 서비스 하네스 완성도 점검 | - | 미구현 |
| `ad:team2-members` | 팀원/담당 서비스 조회 | - | 미구현 |

### 서비스별 스킬 (서비스 하네스에서 추가)

| 스킬 | 설명 |
|------|------|
| `ad:deploy` | 서비스별 배포 절차 |
| `ad:migration` | DB 마이그레이션 가이드 |
| `ad:api-check` | API 스펙 정합성 검증 |
| `ad:env-setup` | 로컬 환경 셋업 가이드 |
