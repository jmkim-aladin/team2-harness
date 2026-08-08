# Codex 진입점 — 개발 2팀 하네스

Codex에서 `CLAUDE.md`와 같은 역할을 한다. 작업은 항상 **개발 2팀 하네스**(team2)를 source of truth로 한다.

**팀 규칙·구조·서비스 카탈로그·문서 규칙은 [CLAUDE.md](./CLAUDE.md)가 SoT다.** 이 파일은 Codex에만 해당하는 것만 담는다.

## 경로

```
$TEAM2_HARNESS_PATH = /Users/jm/Documents/workspace/team2
$LOCAL_WIKI_PATH    = /Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2
```

- 가이드·정책·스킬·서비스 카탈로그·스프린트 산출물: 팀 하네스 (`$TEAM2_HARNESS_PATH`)
- 도메인 분석, Graphify 산출물, Querybook, daily/meetings/tickets 노트: 로컬 Obsidian vault (`$LOCAL_WIKI_PATH`)
- `YOUTRACK_TOKEN`이 환경에 없으면 `~/.claude/settings.json`의 `env.YOUTRACK_TOKEN`을 읽되 값은 출력하지 않는다

## 스킬 호출

스킬은 **사용자가 호출할 때만** 실행한다. 어떤 스킬을 언제 부르는지는 [docs/harness-guide.md](./docs/harness-guide.md)의 **작업 플로우** 절이 인덱스다.

근거: 2026-08-08 실사용 실측 — 판정은 [docs/skill-stack-and-workflow-plan.md](./docs/skill-stack-and-workflow-plan.md) §3.

절차의 SoT는 `.claude/commands/ad/{name}.md` 하나다. `.codex/skills/ad-{name}/`은 SoT를 런타임에 읽는 얇은 alias이므로 `$ad-*` 호출 시 해당 command 문서를 먼저 읽고 같은 절차로 수행한다.

### `$ad-*` ↔ `/ad:*` alias

`architecture-analysis` `capacity-plan` `code-review` `data-request` `explain` `granola-sync` `harness-optimize` `new-note` `okr` `orchestration` `service-activity` `sprint-close-check` `team2-kb-read` `ticket` `tldr` `weekly-planned` `weekly-report` `work-board` `work-close` `work-prep`

20종 전부 `$ad-{name}` = `/ad:{name}`. 컨텍스트 스킬 3종: `$dev2-team-harness-ko`(정책·카탈로그·KB·주간업무 컨텍스트), `$youtrack-ticket-5w1h-ko`(DEV2 티켓 작성), `$dev2-ad-commands-ko`(`/ad:*` 호환 실행).

## 도구 대응

gstack 본문은 Claude Code 도구명을 사용하므로 Codex에서는 이렇게 읽는다: `Bash`→`exec_command`, `Read`→`sed`/`rg`/`cat`, `Write`·`Edit`→`apply_patch`, `Grep`·`Glob`→`rg`/`find`, `Agent`→가능하면 multi-agent, `AskUserQuestion`→짧은 직접 질문.

gstack 스킬 사용 시 [policies/gstack-override-policy.md](./policies/gstack-override-policy.md)를 참조한다 — 팀 Git 컨벤션·배포 정책이 gstack 기본값보다 우선한다.

## 세션 컨텍스트 규율

세션 컨텍스트는 **smart zone**(약 150k 토큰) 안에 둔다.

- 단계 경계에서 비운다. 각 구현 앞에서 컨텍스트를 새로 시작한다
- 파일은 읽기 도구로 읽고 `cat`·`sed`로 전문을 출력하지 않는다
- 셸 cwd는 호출마다 초기화되므로 절대 경로로 명령한다
- 한 번 읽은 파일은 다시 읽지 않는다
- 넓은 조사는 서브에이전트로 보내고 결론만 회수한다

근거: 2026-08-08 30일 실측 — 호출당 평균 컨텍스트 470k (zone의 3배).

## 외부 시스템

- **YouTrack**: `https://aladincommunication.youtrack.cloud` — REST API(`$YOUTRACK_TOKEN`)만 사용. MCP 미사용
- **GitHub**: `gh` CLI로 PR·이슈 조회. Org는 `AladinCommunication`, 개인 계정은 `jmkim-aladin`
- **DB**: DB 관련 MCP 도구는 사용하지 않는다. dev RDS `sqlcmd`는 read-only 조회만 허용

## GBrain 공유 brain

- DEV2 공유 brain은 Hermes Docker의 `gbrain-team2` 서비스가 제공하는 HTTP MCP다
- 로컬 에이전트 MCP URL `http://127.0.0.1:3131/mcp`, Hermes 컨테이너 내부 URL `http://gbrain-team2:3131/mcp`
- Codex·Claude Code·Hermes가 같은 MCP를 쓴다. Mac의 직접 `gbrain` CLI는 개인 로컬 PGLite일 수 있으므로 공유 brain 운영 명령은 `docker exec gbrain-team2 ...`로 실행한다
- Docker runtime은 `GBRAIN_SOURCE=team2-vault`로 실행해 vault를 기본 검색 범위로 둔다. 하네스 검색이 필요하면 source를 명시한다
- 상시 지식 강화 주체는 Hermes다. cron이 `tools/run_team2_knowledge_cycle.py`로 vault projection·board·outbox·status를 갱신하고, `tools/run_granola_sync_cycle.py`를 10분마다 실행해 Granola 회의록을 동기화한다
- PGLite maintenance는 host LaunchAgent `com.team2.gbrain-maintenance`가 01:40 KST에 수행한다. 상태 조회는 `/Users/jm/.hermes-team2/scripts/gbrain-maintenance.sh --status`이며 maintenance를 실행하지 않는다
- gbrain 검색 결과는 **후보 근거**다. 확정 지식·승인·done/canonical 상태는 vault/YouTrack/코드/사용자 확인으로 검증한다
- gbrain bearer token과 API key는 문서나 커밋에 기록하지 않는다

## 커밋 메시지

- AI co-author footer나 도구 자기참조 footer를 추가하지 않는다
- 본문은 의사결정·영향 범위 중심으로 짧게. 코드 수준 구현 디테일 bullet 나열은 피한다
