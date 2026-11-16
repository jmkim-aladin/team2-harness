# 교정 규칙 강제 대장

사용자 교정에서 생긴 규칙과 그 규칙을 지키게 하는 수단을 짝지어 둔다. 같은 교정이 다시 필요 없게 하려는 장부다. 원칙: [북극성 §개선 사이클 5](../policies/harness-north-star.md#개선-사이클). 형식은 pstack `correct`(MIT, Lauren Tan)를 번안했다.

## 쓰는 법

- 교정이 들어오면 가장 높은 층에서 막는다: **아키텍처·타입 > 권한·훅·lint > 테스트·CI > 문서**. 문서는 판단이 필요한 규칙에만 쓴다
- 기계화했으면 규칙 원문은 강제 수단을 가리키는 한 줄로 줄인다. 대장에는 행을 남긴다
- 팀 훅(`correction-guard`)에는 팀 규칙만 넣는다. 설치기가 팀 전원의 `~/.claude`에 깔기 때문이다. 개인 규칙은 개인 설정에서 강제하거나 팀 규칙으로 올린 뒤 넣는다
- `correction-guard` 규칙 id는 `tools/correction_guard.py`의 `REASONS`와 맞춘다. 테스트가 대장 누락을 잡는다

## 대장

상태: **강제**(기계가 막음) · **문서**(판단이 필요해 문서로 둠) · **후보**(기계화 가능, 미착수) · **보류**(전제 미확인)

| 규칙 | 출처 | 층 | 강제 수단 | 상태 |
|---|---|---|---|---|
| 커밋·PR에 AI 도구 푸터 금지 | [ai-usage-policy](../policies/ai-usage-policy.md) §메시지 작성 품질, 2026-11-12 PR 푸터 수동 제거 | 훅 | `correction-guard:ai-footer` | 강제 |
| 단순 조사·웹 읽기·1차 리뷰 subagent는 model 명시 | [claude-base](../memory/claude-base.md) §서브에이전트 위임, 2026-11-02 | 훅 | `correction-guard:delegate-model` | 강제 |
| 비밀 파일 읽기·강제 push·미커밋 변경 폐기 금지 | [북극성](../policies/harness-north-star.md) 원칙 5 | 권한 | `install_claude_gates.py` `DENY_RULES` | 강제 |
| DB 계열 MCP 금지 | 2026-05-18 사용자 범위 지정 | 훅 | `block-db-mcp` | 강제 |
| 운영 DB·sqlcmd 읽기 경로 | [운영 DB 접근 정책](../policies/production-db-access-policy.md) | 훅 | `sqlcmd-readonly`, `agent-run-guard` | 강제 |
| 스킬은 Claude·Codex 양쪽에 같이 | 2026-07-16 "대전제" | 테스트 | `tests/test_codex_skills.py` alias 패리티 | 강제 |
| 작업마다 공통 task_id | [task-tracing-policy](../policies/task-tracing-policy.md) | 훅 | UserPromptSubmit `task_tracing` 주입 | 강제 |
| Feature SP는 0 | 2026-07 Velocity 중복 집계 | 문서 | [/ad:ticket](../.claude/commands/ad/ticket.md) | 후보 — 티켓 생성이 curl 문자열이라 훅 판정이 불안정. 생성 도구로 모으면 검사 가능 |
| 서브에이전트는 커밋·푸시·티켓 상태 변경 안 함 | [claude-base](../memory/claude-base.md) §위임 프롬프트 계약 | 훅 | — | 보류 — PreToolUse 입력에서 subagent 호출을 구분하는 필드를 확인하지 못함 |
| DB 스크립트·SP PR 리뷰는 분기·계산·경계값만, 배포 산출물 제외 | 2026-10-12 PR #7 리뷰 | 문서 | [code-review personas](code-review/personas.md) | 문서 — 지적 범위 판단 |
| 서비스 하네스 없는 서비스는 레거시 경계를 `해당없음` | 2026-08-06 Tobe PR #153 | 문서 | [/ad:code-review](../.claude/commands/ad/code-review.md) §통과 근거 | 문서 — 판정 표기 |
| 남의 티켓·PR은 리뷰·승인·머지까지 | 2026-08-06 Tobe PR #152 | 문서 | 개인 auto-memory | 문서 — 작성자 판별·문맥 판단 |
| 새 문서 위치 결정 트리 즉시 적용 | [knowledge-base-policy](../policies/knowledge-base-policy.md) | 문서 | vault `lint_vault`(frontmatter `type`)가 일부 | 문서 — 분류 판단 |
| 기본 브라우저는 ego lite | [claude-base](../memory/claude-base.md) §브라우저 | 문서 | — | 문서 — 보조 수단 허용이라 금지 규칙 아님 |

### 개인 규칙 (`~/.claude/CLAUDE.md`)

팀 훅에 넣지 않는다. 기록만 하고 강제 여부는 본인이 정한다.

| 규칙 | 층 | 판정 |
|---|---|---|
| PR 머지는 검토한 HEAD를 `--match-head-commit`으로 고정 | 훅 | 후보 — 팀 규칙으로 올리면 `correction-guard`에 추가 가능 |
| 아티팩트 게시 시 vault 노트 동시 저장 | 훅 | 후보 — 게시 직후 PostToolUse로 vault 경로를 상기시키는 방식 |
| 리뷰 본문 `--body-file`·명령 단독 호출 | 문서 | 권한 프롬프트 회피용 작성 요령 |
| vault autogit — 커밋 여부 묻지 않음 | 문서 | 행동 규칙 |
| team2는 PR 없이 `--no-ff` 머지 | 문서 | [branching-strategy](../policies/branching-strategy.md) 하네스 예외와 같음 |
| 파일 참조는 `file://` 링크 | 문서 | 출력 형식 — 기계 판정 불안정 |
