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
- 가이드·정책 문서는 절 단위로 소비한다 — 목차(`grep -n '^## '`)로 절을 고른 뒤 그 절만 읽는다
- 넓은 조사는 서브에이전트로 보내고 결론만 회수한다

근거: 2026-08-08 30일 실측 — 호출당 평균 컨텍스트 470k (zone의 3배).

## 서브에이전트 위임 프롬프트

> SoT: [memory/claude-base.md](./memory/claude-base.md) §위임 프롬프트 계약 — Codex 로드 경로 부재로 아래 블록을 **생성**한다. 직접 고치지 말고 SoT를 고친 뒤 `python3 tools/lint_harness_rules.py --sync-generated`. 모델 선택표는 SoT를 본다.

<!-- generated:delegation-contract source=memory/claude-base.md -->
절차를 쪼개 순서대로 시키지 말고 **일을 통째로** 준다. 다섯 요소를 모두 채우면 자족적이다.

| 요소 | 내용 |
|---|---|
| **목표** | 끝난 상태를 한 문장. 경로·순서는 지정하지 않는다 |
| **의도(왜)** | 누구를 위해, 무엇이 가능해지는가. 미리 못 정한 결정을 서브에이전트가 이 맥락으로 판단한다 |
| **불변조건** | 각 항에 이유를 붙인 긍정형. 앵커 문서 경로(티켓 노트·정책·카탈로그)와 repo 관례를 여기 건다 |
| **완료 기준** | 기계 판정 가능한 신호 — 통과할 명령(lint·build·test), 존재할 파일, 만족할 수치 |
| **출력 형식** | 회수할 산출물의 모양과 길이. 안 적으면 장황해진다 |

- 커밋·푸시·티켓 상태 변경은 서브에이전트가 하지 않는다 — 게이트는 메인 (근거: 사용자 확인 게이트는 invariant)
- 부정형 나열("~하지 마라")로 가드레일을 채우지 않는다. 대체 행동이 비면 모델이 그 자리를 임의로 채운다 — `policies/instruction-precedence-policy.md` §표기 규약
- "다시 검증하라", "단계별로 생각하라" 같은 사고 과정 지시는 넣지 않는다. 신모델 내장 행동이라 중복 단계와 토큰만 늘린다. 산출물에 남길 증거(출처·파일:행·통과 명령)를 요구하는 것은 이와 다르며 유지한다

근거: 2026-09-16 Anthropic Claude 5 세대 가이드 — 완전한 작업 명세(목표·가드레일·종료 조건)를 주고 끝까지 돌리는 쪽이 단계 지시보다 낫다.
<!-- /generated:delegation-contract -->

## 지시문 준수 검사

팀 지시문(정책·스킬·템플릿)은 [instruction-precedence-policy.md](./policies/instruction-precedence-policy.md) §표기 규약을 따르고, 준수 여부는 검사로 지킨다.

```bash
python3 tools/lint_harness_rules.py            # 전체 위반 목록
python3 tools/lint_harness_rules.py --check    # 베이스라인 대비 증가만 차단 (ratchet)
```

하네스 문서를 고쳤으면 `--check`를 통과시킨 뒤 커밋한다. 상세는 [tools/README.md](./tools/README.md).

## 외부 시스템

- **YouTrack**: `https://aladincommunication.youtrack.cloud` — REST API(`$YOUTRACK_TOKEN`)만 사용. MCP 미사용 — 토큰과 쓰기 권한을 `curl` 한 경로로 통제하기 위해
- **GitHub**: `gh` CLI로 PR·이슈 조회. Org는 `AladinCommunication`, 개인 계정은 `jmkim-aladin`
- **DB**: DB 관련 MCP 도구는 사용하지 않는다. dev RDS `sqlcmd`는 read-only 조회만 허용 — 훅이 차단한다. 에이전트에 DB 쓰기 경로를 주지 않는다
- **공통 서비스 영향**: 로그인·결제·정산·구독 등이 걸리면 [policies/common-service-policy.md](./policies/common-service-policy.md) + [catalog/common-services/registry.yaml](./catalog/common-services/registry.yaml) 확인
- **검색 서비스 명칭**: 공식 표기는 `ALICE(알리스)`. 검색 API·색인·OpenSearch 경계는 [catalog/common-services/alice.yaml](./catalog/common-services/alice.yaml) 확인

## GBrain 공유 brain

설정·검색 가이드: [docs/gbrain-config.md](./docs/gbrain-config.md)

## 커밋 메시지

[policies/ai-usage-policy.md](./policies/ai-usage-policy.md) §메시지 작성 품질을 따른다.
