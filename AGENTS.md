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
- 용어: "위키"는 로컬 Obsidian vault만 뜻한다. YouTrack Articles는 "지식베이스(KB)" 또는 "기술자료"라고 부르며, "위키에 저장"은 로컬 위키 저장으로 해석한다
- 토큰 조달: [youtrack/api-guide.md](./youtrack/api-guide.md) §환경변수·§셋업(cred.py 체인)을 따른다

## 스킬 호출

요청이 스킬에 맞으면 다른 도구보다 먼저 호출한다. 판단 근거는 각 스킬의 `description`이며, 이 파일에 라우팅 목록을 따로 두지 않는다 — 같은 일을 두 곳에서 하면 한쪽이 반드시 낡는다.

**사용자 호출 전용 6종**(사이드이펙트): `$ad-code-review`, `$ad-work-board`, `$ad-tldr`, `$ad-explain`, `$ad-implement`, `$ad-plan-run`.

어떤 스킬을 언제 부르는지의 지도는 [docs/harness-guide.md](./docs/harness-guide.md) §작업 플로우.

절차의 SoT는 `.claude/commands/ad/{name}.md` 하나다. `.codex/skills/ad-{name}/`은 SoT를 런타임에 읽는 얇은 alias이므로 `$ad-*` 호출 시 해당 command 문서를 먼저 읽고 같은 절차로 수행한다.

### `$ad-*` ↔ `/ad:*` alias

`.codex/skills/` 디렉토리가 SoT — `ad-{name}` = `/ad:{name}`.

컨텍스트 스킬 3종: `$dev2-team-harness-ko`(정책·카탈로그·KB·주간업무 컨텍스트), `$youtrack-ticket-5w1h-ko`(DEV2 티켓 작성), `$dev2-ad-commands-ko`(`/ad:*` 호환 실행).

## 도구 대응

gstack 본문은 Claude Code 도구명을 사용하므로 Codex에서는 이렇게 읽는다: `Bash`→`exec_command`, `Read`→`sed`/`rg`/`cat`, `Write`·`Edit`→`apply_patch`, `Grep`·`Glob`→`rg`/`find`, `Agent`→가능하면 multi-agent, `AskUserQuestion`→짧은 직접 질문.

gstack 스킬 사용 시 [policies/gstack-override-policy.md](./policies/gstack-override-policy.md)를 참조한다 — 팀 Git 컨벤션·배포 정책이 gstack 기본값보다 우선한다.

## 세션 컨텍스트 규율

> SoT: [memory/claude-base.md](./memory/claude-base.md) §세션 컨텍스트 규율 — Codex 로드 경로 부재로 여기 복제.

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
- **공통 서비스 영향**: 로그인·결제·정산·구독 등이 걸리면 [policies/common-service-policy.md](./policies/common-service-policy.md) + [catalog/common-services/registry.yaml](./catalog/common-services/registry.yaml) 확인

## GBrain 공유 brain

설정·검색 가이드: [docs/gbrain-config.md](./docs/gbrain-config.md)

## 커밋 메시지

[policies/ai-usage-policy.md](./policies/ai-usage-policy.md) §메시지 작성 품질을 따른다.
