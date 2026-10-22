# Paperclip 파일럿 구성 — 쇼핑 데이터 추출

로컬 단독 Paperclip에서 쇼핑 데이터 추출 요청의 SQL 작성을 에이전트에 맡길 때의 구성값이다. 진행 원장은 vault `wiki/projects/paperclip-pilot/plan.md`, 경계는 [ai-usage-policy.md §Paperclip 에이전트 실행 예외](../../policies/ai-usage-policy.md)이고, 기계 강제는 `tools/agent_run_guard.py`가 한다.

## 인스턴스

| 항목 | 값 | 이유 |
|---|---|---|
| 설치 | `npx paperclipai@2026.1012.0 onboard`. 서비스 등록 없이 포그라운드로 띄운다 | 버전을 고정하고, 종료와 `~/.paperclip` 삭제만으로 제거되게 한다 |
| env | `PAPERCLIP_TELEMETRY_DISABLED=1`, `DO_NOT_TRACK=1`. `YOUTRACK_TOKEN`·AWS 자격증명은 없는 셸에서 띄운다 | 텔레메트리가 기본으로 켜져 있다. 에이전트는 서버 프로세스 env를 상속한다 |
| 배포 모드 | `local_trusted` + loopback | 팀 공유 서버가 아니다 |
| 쓰지 않는 것 | 관리형 AI 연결, Paperclip MCP connection, routine | 관리형 연결을 쓰면 `~/.claude` 계층(팀 스킬·게이트 훅)이 빠진다. connection을 추가하면 `--strict-mcp-config`로 내 MCP가 꺼진다 |

## 프로젝트·이슈

- 프로젝트 workspace는 `data-requests-dev2`, 실행 모드는 이슈별 git worktree 격리로 둔다
- 이슈 제목은 `DEV2-#### {요청 제목}`, 본문은 YouTrack 링크와 요청 요약이다. import는 YouTrack → Paperclip 단방향이다
- executionPolicy는 리뷰 단계(리뷰 에이전트) → 승인 단계(board 사용자) 순서다

## 에이전트 (claude_local)

| | 작성 | 리뷰 |
|---|---|---|
| `instructionsFilePath` | `{team2}/templates/paperclip/data-request-writer.md` | `{team2}/templates/paperclip/sql-reviewer.md` |
| `promptTemplate` | `/ad:data-request 할당된 Paperclip 이슈(PAPERCLIP_TASK_ID)의 DEV2 티켓 — 이슈 제목·본문에서 티켓 ID와 요청부서를 읽는다` | `/code-review 현재 작업 디렉토리의 feature/DEV2-* 브랜치를 origin/sprint/YYYY-MM 대비 리뷰` |
| 깨움 | 주기·할당 깨움 끔, 수동 실행만, 동시 실행 1 | 같음 |

- 템플릿 변수에 이슈 ID가 없다(`{{agentId}}`·`{{runId}}` 등만). 그래서 티켓은 `PAPERCLIP_TASK_ID`로 이슈를 조회해 정한다
- `-p`에서는 프롬프트 첫머리 스킬 하나만 실행된다. 사람 전용 스킬도 실행되지만, 스킬에서 다른 사람 전용 스킬로 이어 부를 수는 없다
- `dangerouslySkipPermissions`는 기본값(true)으로 둔다. 경계는 사용자 레벨 훅이 지킨다 — 훅 deny는 우회 모드에서도 강제된다
- Codex 교차 검증은 2주차에 붙인다. codex_local 어댑터는 쓰지 않는다 — 샌드박스 우회가 기본이고, 격리 CODEX_HOME에 팀 스킬이 없다
