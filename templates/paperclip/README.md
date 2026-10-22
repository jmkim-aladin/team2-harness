# Paperclip 파일럿 구성 — 쇼핑 데이터 추출

로컬 단독 Paperclip에서 쇼핑 데이터 추출 요청의 SQL 작성을 에이전트에 맡길 때의 구성값이다. 진행 원장은 vault `wiki/projects/paperclip-pilot/plan.md`, 경계는 [ai-usage-policy.md §Paperclip 에이전트 실행 예외](../../policies/ai-usage-policy.md)이고, 기계 강제는 `tools/agent_run_guard.py`가 한다.

## 인스턴스

| 항목 | 값 | 이유 |
|---|---|---|
| 설치 | `npx paperclipai@2026.1012.0 onboard`. 서비스 등록 없이 포그라운드로 띄운다 | 버전을 고정하고, 종료와 `~/.paperclip` 삭제만으로 제거되게 한다 |
| env | `PAPERCLIP_TELEMETRY_DISABLED=1`, `DO_NOT_TRACK=1`. `YOUTRACK_TOKEN`·AWS 자격증명은 없는 셸에서 띄운다 | 텔레메트리가 기본으로 켜져 있다. 에이전트는 서버 프로세스 env를 상속한다 |
| 배포 모드 | `local_trusted` + loopback | 팀 공유 서버가 아니다 |
| 실험 플래그 | `enableIsolatedWorkspaces: true` (`PATCH /api/instance/settings/experimental`) | 기본이 꺼져 있어서, 프로젝트에 격리 정책을 걸어도 무시되고 사람용 체크아웃에서 돈다 (2026-10-22 ALA-1) |
| 쓰지 않는 것 | 관리형 AI 연결, Paperclip MCP connection, routine | 관리형 연결을 쓰면 `~/.claude` 계층(팀 스킬·게이트 훅)이 빠진다. connection을 추가하면 `--strict-mcp-config`로 내 MCP가 꺼진다 |

## 프로젝트·이슈

- 프로젝트 workspace는 `data-requests-dev2`, 실행 모드는 이슈별 git worktree 격리로 둔다. 이슈에도 `executionWorkspaceSettings.mode: isolated_workspace`를 명시한다
- worktree 위치는 `workspaceStrategy.worktreeParentDir`로 repo 밖에 둔다. 기본값은 repo 안의 `.paperclip/worktrees/`라서 사람 쪽 `git status`에 섞인다. 이미 repo 안에 만들었다면 `.git/info/exclude`에 `.paperclip/`를 넣는다
- 이슈 제목은 `DEV2-#### {요청 제목}`, 본문은 YouTrack 링크와 요청 요약이다. import는 YouTrack → Paperclip 단방향이다
- executionPolicy는 리뷰 단계(리뷰 에이전트) → 승인 단계(board 사용자) 순서다
- 등록은 `/ad:paperclip-dispatch DEV2-####`(또는 `--inbox`)다. Board 담당·backlog로 들어가 Inbox "Mine"에 모이고, `pilot.json` 규칙에 맞으면 프로젝트·격리·정책이 붙는다. 라벨 `요청자:`·`태그:`와 Artifacts 탭의 원본 티켓 링크(work product)도 함께 붙는다. 맡길 이슈는 `--project "쇼핑 데이터 추출" DEV2-####`로 분류한다 — 화면에서 프로젝트만 바꾸면 격리·정책이 붙지 않는다
- 실행 시작은 사람이 담당을 SQL Writer로 바꾸고 상태를 todo로 올리는 순간이다. backlog 이슈는 할당해도 깨우지 않는다(`issue-assignment-wakeup.ts:46`)
- 자동화: cron·routine이 `python3 tools/paperclip_import_ticket.py --inbox`(또는 `--query "<YouTrack 검색식>"`)를 부른다. 멱등이라 반복 실행해도 중복이 없다. 해결된 티켓의 Paperclip 반영(`--sync-resolved`)은 후속이다

## 에이전트 (claude_local)

| | 작성 | 리뷰 |
|---|---|---|
| 지시문 번들 | `mode: external`, `rootPath: {team2}/templates/paperclip`, `entryFile: data-request-writer.md` | 같음, `entryFile: sql-reviewer.md` |
| 진입 스킬 | 지시문에서 `/ad:data-request` 호출 | 지시문에서 내장 `/code-review` 호출 |
| model | `claude-opus-5-5` | `claude-sonnet-5-5` |
| engine | `cli` | `cli` |
| heartbeat | `enabled: false`(주기 끔), `wakeOnDemand: true`, `maxConcurrentRuns: 1` | 같음 |

- 새 에이전트는 `promptTemplate`을 받지 않는다(지시문 번들만, `2026.1012.0`). 번들은 external 모드로 repo 파일을 직접 가리키게 한다 — 복사본은 repo와 어긋난다
- engine은 `cli`로 둔다. 기본값(ACP)은 내장 Claude Code 2.1.257로 돌아 Opus 5.5에서 400 오류가 난다(2.1.280 이상 필요). 또 SDK 경로라 `~/.claude` 훅 로드가 검증되지 않았다. `cli`는 설치된 `claude --print`를 써서 가드 훅 로드가 headless로 확인된 경로다
- 진입 스킬은 모델이 호출할 수 있어야 한다. 사람 전용 스킬(`disable-model-invocation`)은 지시문으로 부를 수 없다
- `wakeOnDemand` 하나가 할당·수동·자동 깨움을 함께 켜고 끈다(`heartbeat/queue.ts:2699`). 끄면 수동 실행도 막힌다. 그래서 작성 에이전트는 사람이 이슈를 할당하는 순간이 실행이고, 리뷰 에이전트는 리뷰 단계 전이 때 자동으로 돈다 — 판정만 하고 가드가 걸려 있어 위험이 낮다
- `dangerouslySkipPermissions`는 기본값(true)으로 둔다. 경계는 사용자 레벨 훅이 지킨다 — 훅 deny는 우회 모드에서도 강제된다
- 승인·반려 결정은 코멘트와 상태 변경이 **같은 요청**이어야 한다(`PATCH /api/issues/{id}` `{status, comment}`). 화면은 둘을 따로 보내서 결정이 거부된다(2026-10-22 ALA-2). 결정은 API로 보낸다
- 에이전트가 자기 실행 안에서 이슈를 다음 단계로 넘기면, 다음 담당 에이전트의 깨움이 누락될 수 있다(ALA-2 리뷰 단계). 담당 에이전트가 `idle`인 채 실행이 없으면 `POST /api/agents/{id}/wakeup` `{source:"assignment", payload:{issueId}}`로 깨운다
- ACP 엔진으로 돈 적이 있으면 대상 repo에 `.claude/settings.local.json`(`curl:*`·`env` 허용 규칙)이 남는다. 지운다
- Codex 교차 검증은 2주차에 붙인다. codex_local 어댑터는 쓰지 않는다 — 샌드박스 우회가 기본이고, 격리 CODEX_HOME에 팀 스킬이 없다
