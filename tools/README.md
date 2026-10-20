# harness tools

팀 하네스 보조 도구 모음. 일회성 또는 정기 실행용 스크립트.

## 하네스 행동·실행 검증

- `evaluate_harness_behavior.py`: 두 실행의 원본 산출물을 사전 assertion으로 비교한다. [입력 계약·실행법·판정 한계](../docs/harness-behavior-evaluation.md).
- `verify_harness_links.py`: 실제 링크 동기화 CLI의 dry-run·apply·반복·재개·증거 보존을 격리 fixture에서 확인한다. [실행 검증 계약](../docs/verification/harness-links.md).

두 도구 모두 종료 코드는 PASS 0 / FAIL 1 / INCONCLUSIVE 또는 입력 오류 2다. 로그의 성공 문구만으로 동작을 판정하지 않는다.

## team2-agent.py / bin/team2-agent — 터미널 조작면

컴퓨터 앞에서 쓰는 짧은 control pane 명령. 내부적으로는 아래 Python 도구들을 호출하지만, 사용자는 긴 `python3 tools/...` 명령을 직접 치지 않는다.

### 사용법

```bash
export PATH="/Users/jm/Documents/workspace/team2/bin:$PATH"

team2-agent board
team2-agent cockpit
team2-agent cycle
team2-agent brief t_36a47508
team2-agent delegate t_36a47508 planner "추천안과 리스크 정리"
team2-agent decide t_36a47508 "A안으로 결정. 원본 위키에 기록"
team2-agent herdr doctor
team2-agent herdr install-hooks
team2-agent herdr open
team2-agent herdr open --engine claude
team2-agent herdr open --no-attach
team2-agent herdr tickets --engine claude --service max --concurrency 4 DEV2-6509 DEV2-6510
team2-agent herdr worker --engine claude orch-worker-3 "추가 분석 작업"
team2-agent herdr role --engine claude --service max DEV2-6509 analyst "요구사항과 코드 진입점 분석"
team2-agent herdr close --service max DEV2-6509
team2-agent herdr reset
team2-agent herdr sync
```

herdr 작업실이 열린 뒤 사용자는 `team2-orchestration` space의 `global-orchestrator` pane에 자연어로 지시한다. 기본 작업실은 `global-orchestrator`만 확보하고, `--engine {codex|claude}`로 새 agent engine을 선택한다. 티켓 묶음은 서비스 space 안의 티켓별 tab으로 나눈다. 각 tab의 ticket-lead는 analyst/developer/reviewer/QA/designer/data/architect role agent pane을 필요한 만큼만 띄운다. 종료 시에는 `herdr close`로 tab 안의 lead/role pane을 같이 닫는다. Hermes board와 desktop cockpit은 orchestrator가 필요할 때 조회하는 내부 상태 도구로 둔다. CLI action 명령은 사람용 주 인터페이스가 아니라 orchestrator/worker/ticket-lead가 쓰는 내부 도구다.

### 역할

- `board`: Hermes `team2` 보드 상태 확인
- `cockpit`: desktop decision cockpit 갱신
- `cycle`: 전체 지식 사이클 실행
- `brief`, `ask`, `delegate`, `decide`, `approve`, `revise`, `split`, `snooze`, `done`: action queue 기록 + Hermes task 댓글 기록
- `herdr doctor`: herdr server, integration, workspace 상태 확인
- `herdr install-hooks`: Codex/Claude Code herdr hook 설치
- `herdr open`: `team2-orchestration` space를 focus하고 `global-orchestrator`만 보정하거나, 없으면 새 작업실을 만든 뒤 herdr session attach
- `herdr open --no-attach`: herdr session attach 없이 workspace focus/준비만 수행
- `herdr worker`: `team2-orchestration` space에 작업 단위 worker 시작
- `herdr tickets`: 서비스 space에 티켓별 tab을 만들고 ticket-lead를 concurrency 한도만큼 시작
- `herdr role`: 특정 서비스 space의 티켓 tab 안에 role agent 시작
- `herdr close`: 특정 서비스 space의 티켓/work tab을 닫음. 기본은 working/blocked pane이 있으면 거부하고, `--force`일 때만 강제 종료
- `herdr reset`: team2가 만든 모든 작업실(`team2-orchestration`, `team2-triage`, 카탈로그 서비스 space)을 전부 정리해 초기화. 비-team2 작업실은 보존. 기본은 working/blocked pane이 있으면 거부하고, `--force`일 때만 강제 종료
- `herdr sync`: 전체 cycle과 cockpit 갱신 후 herdr 알림 표시
- `herdr notify`: herdr 알림 직접 표시

## run_team2_knowledge_cycle.py — Hermes 지식 사이클 runner

Hermes cron에서 주기 실행하는 deterministic runner. harness link, vault relation/index, Hermes board, Discord dispatch batch/outbox, Hermes Kanban, board action queue, desktop decision cockpit, GBrain health, cycle status note를 한 번에 갱신한다.

### 사용법

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
REPO="/Users/jm/Documents/workspace/team2"

# dry-run
python3 tools/run_team2_knowledge_cycle.py --harness "$REPO" --vault "$VAULT"

# 실 실행
python3 tools/run_team2_knowledge_cycle.py --harness "$REPO" --vault "$VAULT" --apply
```

### Hermes Docker

```bash
python3 /workspace/team2/tools/run_team2_knowledge_cycle.py \
  --harness /workspace/team2 \
  --vault /workspace/team2-vault \
  --gbrain-health-url http://gbrain-team2:3131/health \
  --apply
```

### 경계

- YouTrack, YouTrack KB, DB, 배포, git commit/push를 호출하지 않는다.
- vault draft/projection 파일만 갱신한다.
- Hermes Kanban은 projection view로만 동기화한다. active decision/review task는 `blocked`로 유지하고, source card가 사라진 task는 `done`으로 이동한다.
- Hermes task 본문은 `Source of truth: wiki note`, `Projection: Hermes task`, `Vault path`를 포함한다. 기존 task에는 `TEAM2-SOURCE-LINK` 댓글을 한 번 남겨 같은 연결을 보강한다. task만 직접 완료하지 말고 wiki note 상태를 먼저 정리한다.
- Hermes Board 댓글 지시는 action queue로 수집한다. queue는 실행 요청 이벤트이지 원장이 아니다. queue item은 `source_of_truth`, `vault_path`, `work_id`, `ticket_id`, `service`, `column`을 보존한다.
- canonical 승격은 하지 않는다.

## sync_hermes_kanban.py — Hermes Kanban projection sync

`wiki/projects/agentic-os/hermes-decision-board.json`을 읽어 Hermes Kanban `team2` 보드에 task를 생성/동기화한다. 매핑 state는 vault의 `wiki/projects/agentic-os/hermes-kanban-sync-state.json`에 저장한다.
state item은 Hermes task id와 wiki 원장 경로를 연결하는 projection map이며, 최소 `task_id`, `card_id`, `vault_path`, `work_id`, `ticket_id`, `service`, `column`, `source_of_truth`를 보존한다.

### 사용법

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"

# dry-run
python3 tools/sync_hermes_kanban.py --vault "$VAULT"

# 실 실행
python3 tools/sync_hermes_kanban.py --vault "$VAULT" --apply
```

### 상태 이동

- board에 새 card가 있으면 Hermes task를 만든다.
- active card는 사람 결정/검토 대기이므로 `blocked` 상태로 유지한다.
- 이전 sync state에는 있지만 현재 board에 없는 card는 Hermes task를 `done`으로 이동한다.
- Hermes task를 수동으로 `done` 처리하지 않는다. 먼저 source wiki note의 상태 필드를 정리하고 다음 sync가 task를 이동하게 둔다.

## import_hermes_board_actions.py — Hermes Board comment import

Hermes Kanban task 댓글에서 operator 지시를 읽어 vault action queue로 가져온다.

지원하는 댓글 형식:

```text
/brief 결정 브리프 만들어줘
/delegate planner에게 맡겨서 진행해줘
/decide A안으로 결정. 위키에 기록해줘
```

### 사용법

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"

python3 tools/import_hermes_board_actions.py --vault "$VAULT"
python3 tools/import_hermes_board_actions.py --vault "$VAULT" --apply
```

## queue_agent_board_action.py — action queue writer

터미널이나 cockpit에서 특정 Hermes task/card에 대한 지시를 queue에 기록한다. `--comment-hermes`를 붙이면 같은 지시를 Hermes task 댓글에도 남긴다.

```bash
python3 tools/queue_agent_board_action.py \
  --vault "$VAULT" \
  --task-id t_36a47508 \
  --action brief \
  --instruction "결정 브리프 만들어줘" \
  --apply --comment-hermes
```

## generate_decision_cockpit.py — desktop decision cockpit

컴퓨터 앞에서 보는 통합 decision cockpit projection을 생성한다.

출력:

- `wiki/projects/agentic-os/desktop-decision-cockpit.md`
- `wiki/projects/agentic-os/desktop-decision-cockpit.json`

```bash
python3 tools/generate_decision_cockpit.py --vault "$VAULT" --apply
```

## audit_vault.py — vault 분류 매트릭스 생성

vault 내 모든 md를 새 택소노미에 대응시킨 분류표 생성.

### 사용법

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"

python3 tools/audit_vault.py \
  --vault "$VAULT" \
  --catalog catalog/ \
  --output-md  "$VAULT/wiki/guides/_audit/migration-plan.md" \
  --output-json "$VAULT/wiki/guides/_audit/migration-plan.json"
```

### 출력

- `migration-plan.md` — 사람 검토용 (서비스별 섹션 + 정렬 + 요약)
- `migration-plan.json` — Sub 3 입력용

### 분류 룰

설계 근거는 git 이력의 `docs/superpowers/specs/2026-05-27-vault-audit-migration-plan-design.md` 참조 (2026-08 하네스 정리 시 제거).

요약:
- service prefix(`tobe-`, `web-aladin-`, `max-`, `aasm-`, `shopping-`, `caravan-`, `naru-`, `bazaar-`, `storefront-`, `b2b-store-`, `blog-`, `bookple-`) → 해당 서비스 dir
- 디렉터리(`daily/`, `meetings/`, `okr/`, `incidents/`, `capacity/`) → `processes/{name}/`
- `domains/`, `proposals/`, `decisions/`, `inventory/` → `services/{svc}/{...}`
- `indexes/` → DELETE (Sub 4 재생성)
- `briefs/`, `execution/`, `archive/`, `exports/`, `patterns/`, `imports/`, `templates/`, `tasks/`, `usecases/`, `projects/`, `processes/`, `contracts/`, `services/` (기존) → 사람 판정 (`action=review`)
- guides/ 메타 잔류, guides/ 서비스 prefix 사람 판정

### 검토 절차

1. 도구 실행 (위)
2. `migration-plan.md` 열어 `action=review` row 확정 — `제안 경로` 셀 채우고 `action` 변경
3. 검토 끝나면 도구 재실행하지 말고 json을 수동 갱신 또는 Sub 3 입력으로 직접 사용

### 의존성

Python 3.10+ stdlib만 사용. 외부 패키지 불필요.

## migrate_vault.py — vault 일괄 이관

audit_vault.py 산출(`migration-plan.json`)을 입력으로 받아 파일 이관 + wikilink 재작성.

### 사용법

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"

# 1) dry-run으로 영향 확인 (기본)
python3 tools/migrate_vault.py \
  --vault "$VAULT" \
  --plan  "$VAULT/wiki/guides/_audit/migration-plan.json"

# 2) 단계별 실 실행
python3 tools/migrate_vault.py --vault "$VAULT" --plan "...migration-plan.json" --phase 1 --apply
python3 tools/migrate_vault.py --vault "$VAULT" --plan "...migration-plan.json" --phase 2 --apply
python3 tools/migrate_vault.py --vault "$VAULT" --plan "...migration-plan.json" --phase 3
```

### Phase

- 1: 파일 이관 (action: move/merge/delete)
- 2: wikilink 재작성 (옛 이름 → 새 이름)
- 3: 잔존 끊긴 wikilink 검증 + surface

### 옵션

- `--dry-run` (기본) — 실 변경 없음, 영향만 출력
- `--apply` — 실 실행 (`git mv`/`git rm`/append/sed)
- `--phase 1|2|3|all` — 기본 all
- `--action move,merge,delete` — 처리 대상 action 필터
- `--log-out <path>` — 로그 출력 경로 (기본 vault/wiki/guides/_audit/migration-log.md)

### 안전장치

- 기본 dry-run, `--apply` 명시해야 실 실행
- merge에서 dst 존재 시 자동 append + surface (사람 후속 검토)
- git mv 실패(untracked) 시 mv + git add fallback
- wikilink 충돌(동명 다른 새 이름) 시 변경 안 함 + surface

## generate_vault_indexes.py — vault 인덱스와 서비스 관계 projection 자동 생성

vault `services/{svc}/`, `processes/{type}/`, hub 인덱스를 generated block 기반으로 생성·갱신한다.
서비스 노트에는 `related_services`를 역방향 조회한 `generated:related-notes` block도 함께 생성한다.

### 사용법

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"

# dry-run (기본)
python3 tools/generate_vault_indexes.py --vault "$VAULT"

# 실 실행
python3 tools/generate_vault_indexes.py --vault "$VAULT" --apply

# 부분 target
python3 tools/generate_vault_indexes.py --vault "$VAULT" --target services --apply
```

### 동작

- `<!-- generated:vault-index ... -->` 블록만 자동 갱신
- 서비스 노트의 `<!-- generated:related-notes ... -->` 블록은 관계 필드 기반으로 자동 갱신
- 기존 _index.md에 generated block 없으면 skip + surface (사람 본문 보존)
- 없는 _index.md는 신규 생성 (frontmatter + block + harness-link placeholder)
- `--apply` 시 변경 파일만 git add

### 산출

- services/{svc}/{svc}.md
- processes/{type}/_index.md
- wiki/services/_index.md, wiki/processes/_index.md (hub)

### 의존성

Python 3.10+ stdlib만.

## sync_harness_links.py — harness ↔ vault sync

harness `catalog/*.yaml`, `policies/team-members.md`, `policies/*.md`를 vault 안 generated 블록에 반영.

### 사용법

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
REPO="/Users/jm/Documents/workspace/team2"

# dry-run
python3 tools/sync_harness_links.py --vault "$VAULT" --harness "$REPO"

# 실 실행
python3 tools/sync_harness_links.py --vault "$VAULT" --harness "$REPO" --apply

# target 한정
python3 tools/sync_harness_links.py --vault "$VAULT" --harness "$REPO" --target services --apply
```

### 갱신 대상 블록

- `services/{svc}/_index.md` 의 `<!-- generated:harness-link -->`
- `processes/team/_index.md` 의 `<!-- generated:team-members -->` (없으면 파일 신규 생성)
- `wiki/_index.md` 의 `<!-- generated:policy-index -->` (없으면 본문 끝에 추가)

### 동작

- catalog yaml은 정규식 shallow 파싱 (service_id, name, type, status, owners.{primary,backup,additional,stakeholders})
- team-members.md 정규직 표 파싱 + 이메일 → '한글이름 (id)' 매핑
- policies/*.md 파일 listing + H1 다음 첫 행 = 1행 요약
- 기존 _index.md에 해당 블록 없으면 skip + surface (services 케이스)

### 의존성

Python 3.10+ stdlib.

## lint_vault.py — vault 5룰 lint (Sub A)

vault 안 md를 5 룰로 검사. 노트 작성 직후(`/ad:new-note`) + 정기 sweep 호출 진입점. vault 커밋 게이트(pre-commit)로는 쓰지 않는다 — Tolaria autogit 커밋이 위반 1건에 조용히 막혀 노트가 쌓인다(2026-10-20).

룰:
1. frontmatter `type` 필수 + type별 필수 필드
2. 파일 위치 = type 기반 결정 트리 일치
3. 파일명 = kebab-case, 서비스 prefix 금지
4. file size warn (≥500 line)
5. `_index.md` 안 `<!-- llm-hint -->` 블록 의무

```bash
# 전체
python3 tools/lint_vault.py --vault "$VAULT" --all

# 지정 파일 (노트 작성 직후)
python3 tools/lint_vault.py --vault "$VAULT" --files wiki/foo.md
```

exit 0 = 통과, 1 = 위반.

## sync_granola_meetings.py — Granola 회의록 → vault 동기화

Granola 공식 REST API에서 회의록을 읽어 Tolaría 호환 `type: meeting` 노트로 저장한다.

### 저장 위치

```text
wiki/processes/meetings/YYYY-MM-DD-{topic}.md
```

생성된 노트는 다음 frontmatter를 포함한다.

- `type: meeting`
- `canonical_id: meeting:{date}-{topic}`
- `date`
- `participants`
- `related_tickets`, `related_services`
- `source: granola`
- `granola_id`, `granola_url`

동일 날짜 daily note가 이미 있으면 `## 회의` 섹션에 회의록 링크를 추가한다. 과거 회의 동기화로 daily note가 대량 생성되는 것을 피하기 위해 daily note 신규 생성은 기본 비활성화되어 있다.

기존 회의록이 이미 있으면 파일 전체를 덮어쓰지 않고 `<!-- generated:granola ... -->` 블록만 교체한다. 사람이 보강한 `결정`, `후속 액션`, 관련 티켓/도메인 링크는 보존한다.

### 사용법

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"

# 권장: macOS Keychain 등록
security add-generic-password -U -s "team2-granola-api-key" -a "$(whoami)" -w

# dry-run: 저장될 파일만 확인
python3 tools/sync_granola_meetings.py \
  --vault "$VAULT" \
  --updated-after 2026-06-01

# 실제 저장
python3 tools/sync_granola_meetings.py \
  --vault "$VAULT" \
  --updated-after 2026-06-01 \
  --apply

# daily note가 없으면 생성까지 수행
python3 tools/sync_granola_meetings.py \
  --vault "$VAULT" \
  --created-after 2026-06-01 \
  --create-daily \
  --apply

# Granola 원제목 대신 vault/Tolaría 표시 제목을 한글로 지정
python3 tools/sync_granola_meetings.py \
  --vault "$VAULT" \
  --created-after 2026-05-01 \
  --created-before 2026-06-01 \
  --title-map granola-title-map.json \
  --apply
```

`granola-title-map.json`은 Granola note id를 표시 제목으로 매핑한다.

```json
{
  "not_6P42imQvvJn4Au": "주문/결제 프로세스 검토"
}
```

### 운영 원칙

- API key는 `GRANOLA_API_KEY` 환경변수 또는 macOS Keychain service `team2-granola-api-key`에서 읽는다. 값은 출력하지 않는다.
- 월 단위 동기화는 `--created-after YYYY-MM-01 --created-before 다음달-01`처럼 상한을 함께 지정한다.
- transcript는 기본 저장하지 않는다. 필요할 때만 `--include-transcript`를 사용한다.
- 회의록 원문 확인은 `granola_url`을 우선 사용하고, vault에는 Granola generated block + 사람이 보강한 결정·후속 액션 중심으로 정리한다.
- `--title-map`을 사용하면 기존 회의록의 frontmatter `title`, H1, daily note 링크 alias도 갱신한다. 파일명과 `canonical_id`는 기존 링크 안정성을 위해 유지한다.
- 저장 후 `tools/lint_vault.py`와 `tools/generate_vault_indexes.py --target processes --apply`를 실행하면 Tolaría 탐색성이 좋아진다.

## run_granola_sync_cycle.py — Hermes Granola 회의록 주기 sync

Hermes cron에서 10분마다 실행하는 deterministic runner. 최근 Granola 변경분을 vault meeting note로 동기화하고, 변경된 회의록에만 `<!-- generated:granola-ai-enrichment -->` 후보 block을 추가한 뒤 process index, lint, team2 knowledge cycle을 이어서 실행한다.

```bash
# dry-run
python3 tools/run_granola_sync_cycle.py --harness "$REPO" --vault "$VAULT" --json

# 실 실행
python3 tools/run_granola_sync_cycle.py --harness "$REPO" --vault "$VAULT" --apply
```

Hermes Docker에서는 `/Users/jm/.hermes-team2/scripts/team2-granola-sync-cycle.sh`가 이 runner를 호출한다. cron job은 `/Users/jm/.hermes-team2/cron/jobs.json`의 `team2 granola meeting sync cycle`이며 `every 10m`, `no_agent` 모드다. 변경이 없으면 wrapper가 `[SILENT]`만 출력해 Discord delivery를 억제한다.

경계:

- Granola 원본은 read-only다.
- 기본으로 transcript를 저장하지 않고 daily note를 새로 만들지 않는다.
- AI 보강은 티켓/서비스 후보 block만 작성한다. `결정`, `후속 액션`, `confirmed`, `canonical`, YouTrack/KB/DB/git 변경은 자동 처리하지 않는다.
- API key는 Hermes `.env`의 `GRANOLA_API_KEY` 또는 host Keychain에서 관리하고 값은 출력하지 않는다.

## enrich_vault_relations.py — LLM 위키 관계 필드 보강

vault 노트의 본문/frontmatter에서 확실한 관계를 추출해 `related_*` 필드를 보강한다.

### 사용법

```bash
VAULT="/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"

# dry-run
python3 tools/enrich_vault_relations.py --vault "$VAULT"

# 전체 적용
python3 tools/enrich_vault_relations.py --vault "$VAULT" --apply

# 일부 파일만
python3 tools/enrich_vault_relations.py \
  --vault "$VAULT" \
  --files wiki/processes/meetings/2026-06-05-order-and-payment-process-review.md \
  --apply
```

### 동작

- `DEV2-NNNN` 본문 참조 → `related_tickets`
- 티켓의 `service` / `service_id` → `related_services`
- OKR 본문의 DEV2 티켓 → `related_tickets` + 티켓 서비스 연결
- daily의 회의 wikilink → `related_meetings`
- Granola 회의 제목/요약의 서비스 키워드 → `related_services` 후보
- 자동 보강 관계는 `relation_status: inferred`, `relation_sources: [auto-backfill, ...]`로 남긴다.

실행 기준은 `docs/llm-wiki-operating-guide.md`를 따른다.

## import_from_archive.py — 옛 vault → 새 vault (Sub C)

team2-archive에서 단일 파일을 새 team2 vault로 selective import.

```bash
# 매치 파일 찾기
python3 tools/import_from_archive.py --archive ARCHIVE --vault VAULT --find dev2-5749

# dry-run dst 확인
python3 tools/import_from_archive.py --archive ARCHIVE --vault VAULT --file wiki/tickets/dev2-5749.md

# 실 복사
python3 tools/import_from_archive.py --archive ARCHIVE --vault VAULT --file ... --apply
```

dst 위치는 src frontmatter type 기준 자동 결정. 서비스 prefix 자동 제거.

## vault_sweep.sh — 정기 sweep (Sub D)

generate_vault_indexes + sync_harness_links + lint 일괄.

```bash
# 수동
tools/vault_sweep.sh           # dry-run
tools/vault_sweep.sh --apply   # 실 실행

# cron 권장
# 0 9 * * * /Users/jm/Documents/workspace/team2/tools/vault_sweep.sh --apply --quiet
```

## promote_notes.py — promote 마커 분리 (Sub 8)

ticket note 또는 임의 vault md 안에 다음 마커 작성 → 도구가 별도 노트로 promote.

마커:
```
<!-- promote:{type}/{svc?}/{slug} title="제목" [domain="..."] -->
{본문}
<!-- /promote -->
```

지원 type:
- `domain` → `services/{svc}/domains/{slug}.md` (또는 `domain="..."` 시 `domains/{domain}/{slug}.md`)
- `analysis` → `services/{svc}/analysis/{slug}.md`
- `decision` → `services/{svc}/decisions/{slug}.md`
- `proposal` → `services/{svc}/proposals/{slug}.md`
- `glossary` → `glossary/{slug}.md` (svc 무시)

```bash
# 단일 파일
python3 tools/promote_notes.py --vault "$VAULT" --file wiki/processes/tickets/dev2-XXXX.md

# 전체 scan + 실 실행
python3 tools/promote_notes.py --vault "$VAULT" --all --apply
```

원본 마커 영역 = `[[stem|title]]` wikilink 한 줄로 치환. 새 노트는 template frontmatter 자동 채움.

## archive_vault.py — hot/cold 자동 archive (Sub E)

frontmatter `updated_at` 또는 `date`가 N일 전 이상이면 `archive/YYYY/`로 이동.

대상: `processes/tickets/*` 중 `ticket_status: done` + `processes/{daily, meetings, weekly}/*`. okr·incidents·capacity는 영구 보관.

```bash
python3 tools/archive_vault.py --vault "$VAULT" --days 180
python3 tools/archive_vault.py --vault "$VAULT" --days 180 --apply
```

## harness_context_audit.py — 컨텍스트·스택·훅 감사

`/ad:harness-optimize 스택` 모드가 호출한다. 하네스 **바깥**(환경)이 모델의 사고 대역을 좁히고 있는지 실측한다.

### 사용법

```bash
python3 tools/harness_context_audit.py              # 기본 90일
python3 tools/harness_context_audit.py --days 30
python3 tools/harness_context_audit.py --json       # 기계 판독용
```

### 출력

1. **상주 컨텍스트 예산** — CLAUDE.md·AGENTS.md·개인 메모리·모델 호출 스킬 description. `disable-model-invocation: true`인 스킬은 0으로 계산
2. **훅 목록** — 이벤트·매처·명령. 훅은 상주 예산이 아니라 왕복 지연으로 나타난다
3. **세션 지표** — 호출당 평균 컨텍스트, Bash 비중, Bash 중 `cd` 비율
4. **툴 분포·지연** — 호출 수, 지연 중앙값, 총 소요, 결과 chars, 오류
5. **반복 Read** — 같은 파일 재독. 스킬의 SoT 참조가 여기 뜨면 절 단위 참조 대상
6. **설치 스킬 실사용** — Claude 슬래시 + Skill 툴 + Codex `$alias` 집계, 미사용 목록

### 임계값

코드 상단 `LIMITS`에 있다. 초과 시 `[경고]`로 표시된다. 조정하려면 근거를 함께 남긴다.

| 키 | 기본값 | 의미 |
|---|---:|---|
| `resident_tokens` | 8,000 | 상주 컨텍스트 상한 |
| `avg_context_tokens` | 200,000 | 호출당 평균 컨텍스트 (smart zone 약 150k) |
| `bash_share` | 0.50 | Bash가 전체 툴 호출에서 차지하는 비중 |
| `cd_share` | 0.20 | Bash 중 `cd` 비율 |
| `reread_count` | 5 | 같은 파일 재독 보고 기준 |

### 한계

- Claude Code 세션 로그(`~/.claude/projects`)와 Codex 세션(`~/.codex/sessions`)만 집계한다. **Hermes cron 실행은 안 잡힌다** — 0회여도 즉시 비활성 판단 금지
- 토큰은 chars/4 근사. 절대값보다 회차 간 추이를 본다
- 판정·조치는 사람이 한다. 도구는 후보만 surface한다

### 기준 문서

정책은 [policies/harness-governance-policy.md](../policies/harness-governance-policy.md) §컨텍스트 예산, 판정 근거는 [docs/skill-stack-and-workflow-plan.md](../docs/skill-stack-and-workflow-plan.md).

## setup_harness.py — 환경 수렴 (초기화 도구)

`harness.manifest.json` 선언 상태로 `~/.claude`, `~/.codex`를 맞춘다. 멱등 — "초기화 후 재설치"가 아니라 "선언으로 수렴". 새 머신 = clone → 실행 → 토큰 입력. Mac/Windows 동일 (Windows는 junction 폴백, 실기 검증 필요).

```bash
python3 tools/setup_harness.py            # 수렴 — 부족한 것 추가, 초과분 경고
python3 tools/setup_harness.py --check    # 보고만 (드리프트 시 exit 1)
python3 tools/setup_harness.py --reset    # 관리 영역 초과분 격리 후 수렴
```

- 관리 영역: skills, commands/ad, codex skills, 훅, env, 팀 메모리 링크
- 절대 안 건드림: 인증·토큰 값, 세션 로그, 개인 CLAUDE.md 내용, 플러그인 on/off(경고만)
- `--reset`도 삭제하지 않는다 — `~/.claude/harness-quarantine-<ts>/` 이동, 되돌리기는 `mv`
- 의존성 stdlib만 (새 머신에서 pip 없이 실행)
- 계획 스택(`planned`)은 `[계획]`으로 표시만 — 설치는 사람이 결정

## cred.py — 로컬 자격증명 접근 (OS 공통)

macOS Keychain / Windows Credential Manager를 한 인터페이스로. 정책: [policies/local-credentials-policy.md](../policies/local-credentials-policy.md).

```bash
python3 tools/cred.py get <name>     # 값 stdout (파이프 용도)
python3 tools/cred.py set <name>     # 프롬프트 입력 — 인자로 값 안 받음 (셸 히스토리 방지)
python3 tools/cred.py check          # manifest credentials 선언분 존재 검사 (값 미출력)
```

- macOS: `security` CLI — 의존성 0. Windows: `pip install keyring` 1회
- 필요한 이름 목록은 `harness.manifest.json` `credentials` (값 절대 아님). `setup_harness.py --check`에 포함됨

## db_sqlcmd_guard.py — 개발 SQL 명령 보조 검사

정책: [로컬 자격증명](../policies/local-credentials-policy.md) · [운영 DB 접근](../policies/production-db-access-policy.md).

`.claude/hooks/sqlcmd-readonly.sh`는 기존 연결을 유지하는 진입점이며 Python 표준 라이브러리 검사기를 호출한다. 등록된 dev의 리터럴 `-S/-d/-Q` 한 문장 SELECT를 처리한다. 직접 DML은 전용 실행기로 안내하며 DDL/SP·미등록/운영 호스트·파일/동적 SQL은 거부한다. `tool_input.command`와 `tool_input.cmd` 입력을 지원한다.

```bash
python3 -m unittest discover -s tools/tests -p 'test_db_*.py'
```

테스트는 DB·자격증명에 접속하지 않고 훅 JSON 입출력을 검증한다. 이 검사기는 SQL 파서·셸 샌드박스·운영 승인 서비스가 아니다. 스크립트/다른 드라이버의 우회, 실제 런타임 훅 등록, DB 권한·트리거, 서버 쿼리 취소는 별도 검증 대상이다. 현재 계정용 운영 실행기는 아래 `db_prod_client.py` 절을 따른다.

Claude 프로젝트의 기존 `PreToolUse/Bash` 연결은 호환 스크립트를 유지한다. `.codex/hooks.json`의 실제 로드·matcher 발화는 런타임에서 별도로 검증한다. 입력 필드 지원과 JSON 파일 존재만으로 Codex 연결 완료를 주장하지 않는다.

실제 SQL Server 권한 검증은 [Docker 통합 검증](./tests/integration/sqlserver/README.md)을 사용한다. 합성 데이터·임시 계정·공개 포트 없는 일회성 컨테이너에서 개발 DML과 운영 최소 조회 권한, 잠금/쿼리 timeout을 검사하고 컨테이너를 정리한다.

## db_execute.py — 개발 DML 행 수 제한 실행기

등록된 개발 DB의 단순 INSERT/UPDATE/DELETE를 stdin으로 받아 실행한다. SQLCMDPASSWORD는 기존 자격증명 경로에서 환경변수로 전달한다. 예: `python3 tools/db_execute.py --task DEV2-1234 --database WebCatalog --user dev_dml_user < /보호된/경로/change.sql`. 도구는 개발 host를 고정하며 운영 host 옵션은 없다.

실제 영향 행 수가 작업당 남은 100행 예산을 초과하면 트랜잭션 전체를 롤백한다. 동일 작업 ID의 누적 건수·진행 중 상태를 `~/.local/state/team2/db-execution.sqlite3`에 저장한다. 같은 작업은 DB·호출이 달라도 같은 ID를 사용한다. 이유: 분할 실행과 동시 실행에 의한 실수로 한도를 초과하지 않게 한다. 원장에는 SQL 해시만 저장한다.

출력은 JSON이며 `ok=true/status=committed`만 성공이다. timeout·커밋 응답 유실은 `unknown`으로 남겨 후속 실행을 차단한다. 작업 ID 변경이나 원장 삭제로 재시도하지 않는다. 이유: 이미 커밋된 실행을 반복할 수 있다. 실제 반영·세션 상태를 담당자가 대조한 뒤 복구한다. 자동 승인·예산 초기화 기능은 없다.

개발 계정은 대상 테이블 DML과 DB `VIEW DEFINITION` 권한이 필요하다. 활성 트리거·연쇄 FK·temporal 테이블·뷰는 별도 검토 경로로 보낸다. 권한 부여와 실제 훅 등록은 별도 작업이다. 로컬 코드·원장은 수정 가능하므로 운영 보안 경계로 재사용하지 않는다.

## db_query_control.py — 운영 조회 중앙 제어 코어

여러 에이전트·운영 DB가 공유하는 전역 실행 슬롯 1개와 단일 실행 승인을 관리한다. `prepare`의 SQL 전문·owner·대상·timeout·행/바이트 범위를 사용자에게 보여준 뒤 인증된 operator만 `approve`를 호출한다. 승인 없는 요청·payload 변경·승인 재사용은 DB 연결 전에 거부한다. timeout은 최대 60초이며 행·바이트는 실행별 승인 값 또는 명시적 제한 없음이다.

`Supervisor`는 승인 소비→연결 준비→중단 상태와 직렬화한 SQL 전송→실행 감시→서버 종료 확인 순으로 진행한다. 원장 코어의 `Supervisor.stop`은 지속 차단을 사용하며 `resume`이 필요하다. 오류·timeout은 서버 종료 증거가 없을 때 active 슬롯과 차단을 유지하고, 종료 증거와 `active=null`, `phase=idle`이 확인되면 active 슬롯만 정리하며 차단은 유지한다. 현재 계정 Gateway/CLI의 오류 없는 사용자 `stop`만 이 확인 뒤 일시 중단 latch를 자동 해제하지만 기존 승인·재시도는 복원하지 않는다. 오류·timeout, `emergency-stop`, 실행기 재시작 뒤의 차단은 사람의 별도 `resume`과 새 승인이 필요하다.

중앙 서비스가 관리하는 **이미 존재하는 원장**을 대상으로 CLI를 호출한다. 아래 state 경로는 배포 시 관리자가 정할 예시다. 에이전트별 원장으로 분리하거나 유실 원장을 자동 생성하면 전역 잠금이 깨지므로 초기화는 서비스 프로비저닝 때만 한다.

```bash
python3 tools/db_query_control.py --state /관리영역/query-control.sqlite3 status
python3 tools/db_query_control.py --state /관리영역/query-control.sqlite3 stop
```

이 CLI는 차단 접수·상태 확인용이다. `halted=1`만으로 서버 종료가 확인된 것은 아니며 active/phase와 서버 관측을 함께 확인한다. SQL 실행·승인·재개 CLI는 제공하지 않는다. 이유: 상위 서비스의 사용자 인증과 DB transport 없이 로컬 명령으로 운영 권한을 만들 수 없게 한다.

배포 계약: 한 Mac의 모든 에이전트가 동일 원장을 사용한다. 2026-10-15 사용자 선택으로 현재 macOS 계정에서 운영하며 같은 UID의 직접 파일·DB 접근을 OS 권한으로 격리하지 않는다. 여러 호스트의 로컬 복사본이나 공유 네트워크 파일시스템 잠금으로 분산 제어를 주장하지 않는다. backend의 연결 준비·조회·취소·종료 확인은 시간 제한을 지키고, `dispatch`와 `publish`는 짧은 비차단 동작이어야 한다. 결과는 `finish` 승인 후 중단 상태와 직렬화한 작은 청크로만 내보낸다. 불명확한 전송·반환은 자동 반복하지 않는다.

이 모듈은 제어 코어이며 실제 현재 계정용 접속 경로는 아래 실행기를 사용한다. 운영 네트워크·권한·TLS·종료 관찰은 별도 개통 항목이다. [긴급 중단 계약](../docs/production-db-emergency-stop.md).

## db_prod_client.py — 현재 계정용 운영 조회 실행기

상태: 접속 진단·30초 사용자 중단 시험 성공, 일반 운영 조회는 읽기 전용 권한 검증 전(2026-10-15). 중단 시험은 서버 세션 종료(`session_closed=true`)와 `active=null`, `phase=idle`까지 확인했다. 실행은 `sqlcmd`, 자격증명은 현재 사용자의 로그인 키체인을 사용한다. 별도 macOS 서비스 계정을 만들지 않는다. 같은 계정의 모든 에이전트가 `~/Library/Application Support/team2-db` 원장과 `/tmp/team2-db-<uid>/query.sock`을 공유한다. 같은 UID에 대한 변조 방지나 사람과 에이전트의 OS 권한 분리는 제공하지 않는다.

아래는 이후 사용을 위한 명령 설명이며 현재 실행 지시가 아니다. 저장소 루트에서 `python3 tools/db_prod_client.py <명령>`으로 사용한다.

| 명령 | 동작 |
|---|---|
| `init` | 소유자 전용 디렉터리·초기 차단 원장·설정·Swift 키체인 helper 준비. DB 접속 없음 |
| `start` | 로컬 Unix 소켓 실행기 시작. DB 접속 없음. 종료 미확인·오류·`emergency-stop` 차단은 재시작 뒤에도 유지 |
| `status` | 차단 여부·활성 실행·phase 표시 |
| `resume` | `emergency-stop` 또는 종료 미확인·오류·재시작 차단을 사용자 터미널의 `RESUME` 확인 후 해제 |
| `prepare --target lego-prod --database <DB> --timeout 60 --max-rows 100 --max-bytes 102400` | stdin SQL과 대상·내부 제어 SQL·한도를 묶어 검토 요청 생성. 비밀번호 조회와 DB 접속 없음 |
| `review <요청ID>` | 승인할 SQL 전문과 조건 표시 |
| `approve <요청ID>` | 전문 표시 후 사용자 터미널에서 digest 확인 입력 |
| `execute <요청ID>` | 승인 1회 소비 후 접속·실행·서버 세션 종료 확인·결과 전달 |
| `stop` | 독립 중단 파일부터 영속화하고 활성 조회를 취소하며 기존 승인 무효화. 오류 없는 사용자 취소에서 서버 종료 확인과 `active=null`, `phase=idle` 뒤 다음 요청 준비를 자동 허용 |
| `emergency-stop` | 독립 중단 파일부터 영속화하고 활성 조회를 취소하며 기존 승인 무효화. 서버 종료 확인 뒤에도 전체 차단을 유지 |
| `recovery-prepare` / `recovery-review <요청ID>` | 남은 활성 실행의 종료 확인 SQL과 대상·한도를 준비·표시. DB 접속 없음 |
| `recovery-approve <요청ID>` / `recovery-execute <요청ID>` | 새 명시 승인 후 종료된 worker의 서버 세션을 관찰. 복구 성공 뒤에도 안전 차단은 유지하며 별도 `resume` 필요 |

채팅에서 사용자가 표시된 전문을 명시 승인한 경우에만 에이전트가 `approve <요청ID> --from-chat-digest <전체digest>`로 응답을 전달한다. 이 옵션 자체가 사용자의 승인을 증명하지는 않으며 에이전트의 자가 승인에 사용할 수 없다. SQL·대상·프로파일·한도 변경, 실패·재시도에는 새 승인이 필요하다. 준비 요청은 30분 유효하고 실행은 최대 60초, 모든 대상 합계 동시 1개다.

실행기 장애 후 active가 남으면 원장을 지우거나 강제 초기화하지 않는다. 복구도 observer SQL 전문·대상·시간·결과 범위를 새로 승인받는다. 기록된 worker는 PID·생성 시각으로 종료를 증명한다. 시작 실패로 worker 기록이 없으면 원 실행기의 PID·생성 시각을 대조해 종료를 두 번 확인하고, 그 사이 watchdog 유예 5초를 둔다. 이후 현재 UID의 모든 sqlcmd 프로세스가 없음을 Mac의 고정 ps 명령으로 입증해야 서버 관찰을 시작할 수 있다. 파싱 오류·불완전한 목록·조회 실패는 거부하며 서버 관찰 후에도 로컬 부재를 재확인한다. 로컬 증거와 서버 세션 0건 확인이 모두 있어야 슬롯을 정리한다. 복구 성공 뒤에도 종료 미확인·오류·재시작 안전 차단은 유지하며 사용자의 별도 `resume`과 새로운 조회 승인이 필요하다. 일반 `stop`의 확인된 idle 경로만 자동으로 다음 요청을 받는다. 재개 확인 이후 들어온 새 중단 요청은 우선한다.

기본 설정은 `read_only_verified=false`로 `SELECT 1 AS connection_ok;`, 고정 10초 세션 확인 진단(`SESSION_VISIBILITY_PROBE_SQL`), 고정 30초 중단 시험(`SESSION_STOP_PROBE_SQL`)만 준비할 수 있다. 대기 진단은 지정된 시간 뒤 자기 세션 ID·프로그램명만 반환하며 매 실행 전문 승인·시간 상한·전역 슬롯·중단·종료 확인 규칙을 그대로 따른다. 실제 DB의 읽기 전용 권한·SP 변경/실행 거부·격리 설정을 확인한 뒤 개통한다. 종료 관찰에는 동일 계정이 서버 세션을 빠짐없이 볼 수 있는 DMV 권한이 필요하며 권한 부족이나 관찰 실패 시 종료를 확정하지 않고 차단한다. 에이전트가 DB 권한을 자동 확대하지 않는다.

실패 응답의 `diagnostics`와 감사 원장의 `execution_failed`에는 실행 ID, 실패 단계(`journal`·`credentials`·`startup`·`query`·`observer`), 허용된 오류 코드, 확인 가능한 OS errno·프로세스 종료 코드를 남긴다. TLS·로그인·DB 접근·권한·timeout·연결 거부·DNS·sqlcmd 옵션 오류는 출력에서 인식한 고정 설명으로 제공한다. 이 분류는 클라이언트 출력의 단서이며 근본 원인의 확정은 아니다. 최초 실행 실패와 종료 관찰 실패를 따로 보존한다.

`db_prod_diagnostics.py`는 stdout·stderr를 합쳐 단계당 최대 8 KiB만 메모리에 수집한다. 알려진 SQL 오류 번호와 고정 설명만 응답·감사 로그로 내보내며 주소·계정·비밀번호·SQL·결과가 섞일 수 있는 오류 원문은 저장하지 않는다. 모르는 메시지는 원문 비공개와 잘림 여부를 표시한다. 조회 결과 stdout은 진단 수집에서 제외한다. 이전 실패의 상세 오류는 복원할 수 없다. 진단 보완은 로컬 합성 테스트로 검증하고 사용자 재시도 요청에 따라 실행기에 반영했다. 복구 준비에서 발견한 정상 SQL 줄바꿈 거부도 수정했으며, 접속 진단과 30초 중단 시험에서 종료 확인 및 슬롯 자동 정리를 검증했다. 일반 운영 조회는 읽기 전용 권한 검증 후 별도 개통한다.

2026-10-15 사용자 요청으로 `--max-rows`와 `--max-bytes`는 기본 unlimited이며 기존 8 MiB 누적 결과 제한도 제거했다. 기본 조회 한도는 실행 시간뿐이다. 결과는 메모리에서 최대 60초 보관하고 2 KiB씩 전달한 뒤 전체 길이·해시를 검증하여 표시한다. 전송 청크 크기는 결과 총량 제한이 아니다. 중단·실패 시 미반환 결과는 폐기한다. 자동 비정상 종료 확인 SQL은 사용자 요청으로 승인 화면에서 반복 표시하지 않으며 조건부 실행과 digest 연결을 유지한다. 키체인 값·SQL 원문·원본 결과는 감사 원장에 저장하지 않는다.

`db_prod_profiles.py`·`db_prod_keychain.swift`는 정확한 UTF-8 JSON과 키체인 값을 파이프로 읽는다. `db_prod_transport.py`는 사용자 승인에 따라 `-N true -C`로 TLS 암호화를 필수 적용하고 서버 인증서 검증을 생략하는 sqlcmd 자식 프로세스, `db_prod_watchdog.py`는 독립 중단·heartbeat 감시를 맡는다. `Ctrl+C`나 프로세스 종료만으로 서버 종료를 확정하지 않는다. 현재 Mac의 sqlcmd와 운영 서버 조합은 접속 진단·30초 중단 시험에서 TLS 접속과 세션 종료 확인까지 성공했으며, 일반 조회 권한 검증은 남아 있다.

Go sqlcmd v1.10의 `-X1`은 인증 환경변수도 차단하므로 사용하지 않는다. 대신 자식 환경을 고정된 PATH·격리 HOME·locale과 접속 변수 세 개로 구성해 SQLCMDINI·사용자 설정·다른 비밀값 상속을 제거하고, 변수 확장과 sqlcmd 제어 구문을 차단한다. 근거: [Go sqlcmd v1.10 실행 코드](https://github.com/microsoft/go-sqlcmd/blob/v1.10.0/cmd/sqlcmd/sqlcmd.go), [sqlcmd 제어 명령](https://learn.microsoft.com/en-us/sql/tools/sqlcmd/sqlcmd-commands).

2026-10-15 로컬 Go 클라이언트 재현에서 종료 관찰의 추가 빈 줄 거부와 마지막 줄바꿈 없는 SQL의 미실행을 확인했다. 소스는 관찰 결과의 끝 빈 줄을 처리하고 고정 `-i /dev/stdin`으로 승인된 SQL 바이트를 그대로 소비하도록 수정했다. Go 결과의 마지막 빈 구분 줄 하나는 행 상한에서 제외하되 빈 데이터 행·전체 바이트는 계속 계산한다. 출력 reader가 종료되지 않으면 결과를 반환하지 않는다. `python3 tools/tests/integration/sqlserver/go_transport.py`는 현재 Mac 클라이언트와 자체 생성한 localhost Docker 서버로 이 경로를 검증한다. 운영 세션 종료 확인은 별도의 30초 사용자 중단 시험에서 확인했으며, 이 로컬 재현은 운영 검증을 대신하지 않는다.

서버에서 세션 제거가 늦어지는 경우는 승인된 observer SQL 한 배치 안에서 200ms 간격으로 최대 16회 확인한다(대기 합계 최대 3초, observer 전체 timeout 5초). 권한이 있고 해당 실행의 세션이 0건이면 기존 완료 경로가 active 슬롯을 자동으로 정리한다. 오류 없는 사용자 `stop`은 이때 `active=null`, `phase=idle`이면 일시 중단을 자동 해제하고 다음 요청을 받는다. `emergency-stop`과 종료 미확인·재시작 차단은 해제하지 않으며, 오류·timeout은 종료를 입증해도 active 슬롯만 정리하고 차단을 유지하므로 `resume`이 필요하다. 한도 안에 종료를 입증하지 못하면 active 슬롯도 유지한다. 별도 연결이나 SQL 재실행으로 재시도하지 않는다. 이미 실패로 확정된 실행은 새 복구 SQL 승인이 필요하다. 재현 및 슬롯 정리·중단 보존 검증은 `python3 tools/tests/integration/sqlserver/go_transport.py --report docs/verification/sqlserver-go-cleanup-2026-10-15.json`으로 실행한다.

`db_prod_build_sqlcmd.py`는 공식 v1.10.0 소스의 ApplicationName 한 줄만 DataGrip으로 바꾸는 macOS arm64 빌드를 준비하며 출처·패치·바이너리 해시를 남긴다. 설치는 수행하지 않는다. 전용 빌드는 완료됐으나 사용자 지시에 따라 설치·연동은 보류하고 기존 Homebrew 클라이언트를 유지한다. 운영 프로그램명이 DataGrip으로 반영된 상태가 아니다. 오류 수정본은 2026-10-15 로컬 실행기 재시작으로 반영했다. DB 접속 없이 기존 active 슬롯·종료 미확인 상태·중단 마커·차단이 보존됐음을 확인했다.

격리 단위 검증: `python3 -m unittest discover -s tools/tests -p 'test_db*.py'`. 일회성 Docker SQL Server 검증: `python3 tools/tests/integration/sqlserver/verify.py --transport-only --report docs/verification/sqlserver-prod-transport-2026-10-15.json`. 이 검증은 합성 계정과 컨테이너의 ODBC sqlcmd를 사용하며 운영 접속 검증을 대신하지 않는다.

## secret_scan.py — 시크릿 유출 스캔

repo + vault를 자격증명 패턴(YouTrack perm-, AKIA, JWT, gh 토큰, 접속문자열 암호, Bearer, private key)으로 스캔. `/ad:harness-optimize 스택` 모드에 포함. 발견 시 exit 1 — **제거 + 해당 자격증명 재발급**이 원칙.

```bash
python3 tools/secret_scan.py             # 전체
python3 tools/secret_scan.py --staged    # pre-commit 용
```

오탐 방지: placeholder(`<...>`·`XXXX`·`$VAR`), 스캔 명령 자기 자신(rg/grep 패턴 인자), `.obsidian` 서드파티 코드는 제외.

## lint_harness_rules.py — 지시문 표기 규약 준수 검사 (ratchet)

[instruction-precedence-policy.md](../policies/instruction-precedence-policy.md) §표기 규약을 문장이 아니라 검사로 지킨다 (북극성 1·5). 정책·스킬·템플릿·CLAUDE.md·AGENTS.md를 heading 트리로 파싱해 item 단위로 판정하고, `docs/harness-rule-baseline.json`에 fingerprint로 기록한 기존 위반은 허용하되 **신규 유입은 차단**한다. `/ad:harness-optimize 제약` 모드 Step 1. Claude·Codex 어느 세션에서든 같은 명령.

```bash
python3 tools/lint_harness_rules.py                  # 전체 발견 + 규칙별 요약
python3 tools/lint_harness_rules.py --summary        # 카운트와 베이스라인 대비 추이만
python3 tools/lint_harness_rules.py --check          # 신규 위반·회귀·generated 드리프트만 → exit 1 (PR 게이트)
python3 tools/lint_harness_rules.py --update-baseline                    # 해결분을 베이스라인에서 내림 (신규는 추가 안 함)
python3 tools/lint_harness_rules.py --update-baseline --accept-new "사유"  # 신규 위반을 사유와 함께 수용 — 사유가 PR diff에 남는다
python3 tools/lint_harness_rules.py --sync-generated # canonical 블록 → generated 블록 재생성 (AGENTS.md 등)
```

| 규칙 | 잡는 것 | 등급 |
|---|---|---|
| R1a | 하드룰(반드시·필수·금지…)인데 이유 단서가 그 item·하위 불릿·**같은 절의 설명 문단·절 제목**에 없고, 조상 preamble에도 명시 표지(`근거:`·`의도:`·`이유:`)가 없음. 이유 단서 = 인과(`근거:`·때문·위해·~므로·~라서·~않으면)와 결과·목적 서술(위함·실패한다·낡는다·되돌릴 수 없다·비가역). 규칙이 아닌 라벨·명사구(표 셀 `필수`/`선택`, `[분할 필수]`, `확인 필수 항목:`, `금지 사항`, 등록부 행, `절대경로`의 절대)는 대상 아님. 형제 규칙 항목이나 다른 절의 이유로는 면책 안 됨 | block(신규만) |
| R1b | 베이스라인에 `근거:`가 있던 절에서 근거가 사라짐 | block(회귀) |
| R2 | 모델 내장 행동 재지시("다시 확인", "단계별로 생각", "꼼꼼히") — 규약 설명문 자체는 제외 | block |
| R3 | 강조 인플레(IMPORTANT/MUST 등 ASCII 대문자, `!!`, 한 문장 반드시 2회, 단독 `**반드시**`) — `**필수 작성 요소**` 같은 라벨은 아님 | block |
| R4 | 에이전트 절차 문서(스킬·`.codex/skills`·memory·CLAUDE/AGENTS.md)의 Step-N 헤딩 또는 번호 목록 4개 이상 시퀀스에 이탈 허용 표기 없음 — 가이드·템플릿의 절 번호는 대상 아님 | warn |
| R5 | 추정 토큰(한글 1자≈1, 그 외 4자≈1) 한도 초과 — 바이트는 한국어를 3배로 세므로 쓰지 않는다. 분리 지시가 아니라 로드량 측정 신호 | warn |
| R6 | `catalog/*.yaml`에 `service_id` 있는데 `verification` 없음 | block |
| R7 | `generated:` 블록이 `canonical:` 원본과 바이트 불일치, `targets=`로 선언된 파일에 완결된 블록이 정확히 1개가 아님 | block(항상, 베이스라인 없음) |

ratchet 세부: fingerprint = `sha1(rule|path|heading|정규화 문장)`. 같은 절의 동일 문장은 `count`로 세어 개수 증가도 차단한다(multiset). 위반을 다른 파일로 옮기면 path가 바뀌어 신규로 잡힌다. 베이스라인은 `schema_version`·`matcher_version`을 검증해 규칙 패턴이 바뀐 뒤 옛 판정을 그대로 믿지 않는다 — 불일치면 `--update-baseline --accept-new "<사유>"`로 재판정. 수용 사유는 `acceptance_batches`에 한 번 저장되고 각 finding이 id로 참조한다.

pre-commit: `.githooks/pre-commit`이 `secret_scan --staged`와(하네스 지시문·린터·베이스라인·훅이 staged일 때) `--check`를 돈다. 설치는 `setup_harness.py`가 `core.hooksPath=.githooks`로 수렴(`harness.manifest.json` `git_hooks`). Claude·Codex 어느 세션이 커밋하든 같은 게이트.

기계가 못 하는 것: invariant/policy/heuristic **등급 판정** — 표면 토큰이 같다. R1a 발견을 사람이 훑어 등급을 정하고 완화·이유 부착·`근거:` 부착 중 하나를 택한다.

## rotate_hermes_outbox.py — Discord outbox 회전

vault의 `hermes-discord-outbox/`가 무한 누적되지 않게 14일 경과 요청 디렉토리를 `~/.hermes-team2/archive/discord-outbox/YYYY-MM/`로 이동. dry-run 기본, `--apply`로 실행. `/ad:harness-optimize 스택` 주기에 포함 권장. 근거: 2026-08-08 실측 — 15,447 JSON/74MB가 vault git의 94.6% 점유.

## export_wbs.py — YouTrack 하위 트리 → WBS·간트 엑셀 + HTML 간트 (시제품)

루트 이슈 ID 하나에서 Subtask 링크를 재귀로 따라가 프로젝트 경계(DEV2·DEVSY·DEVDG)와 무관하게 하위 트리 전체를 모아 `.xlsx`로 낸다. 시트: WBS / 간트(날짜 열 칸 색칠, 레벨별 행 그룹) / 팀별 요약 / 점검 / 메타. YouTrack은 GET만 호출하고, 토큰은 `YOUTRACK_TOKEN` 또는 `cred.py get youtrack-token`에서 받아 헤더에만 쓴다.

```bash
python3 tools/export_wbs.py DEV2-5237 --out ~/Downloads/wbs-DEV2-5237.xlsx              # --out 필수, repo 안 경로는 거부
python3 tools/export_wbs.py DEV2-5237 --out ~/Downloads/wbs.xlsx --html ~/Downloads/gantt.html --html-title "SF 프로젝트 간트"
python3 tools/export_wbs.py DEV2-5237 --out ~/Downloads/wbs.xlsx --gantt-unit week --today 2026-10-07
```

- `--html`: 단일 파일 HTML 간트(인라인 JSON, 외부 스크립트 없음, 템플릿 `export_wbs_gantt.html`) — 표(엑셀 WBS 전 열·열 선택·열 폭 드래그)와 타임라인(폭 맞춤/주/일)을 분할선으로 나누고, 팀별 요약·점검 목록·Depend/Relates 연결선을 보여준다. 엑셀과 같은 계산(진척률·rollup·점검)을 쓴다
- 계획 일정은 `Sprints`(월 단위) 최소월 1일~최대월 말일 근사 — 시작일·완료일 필드가 생기면 `planned_dates()`만 바꾼다
- 실제 시작 = State(`상태`)가 처음 In Progress가 된 날, 실제 종료 = `resolved`. 진척률은 취소성 종료(Won't fix 등)를 분모에서 뺀다
- 상위 행은 자기 일정이 없거나 하위가 더 넓으면 하위 범위를 빗금(rollup)으로 표시한다
- '유형' 칸(엑셀 WBS 시트 채움·HTML 표 배지)은 `TYPE_COLORS` 한 표로 칠한다 — Epic 보라·Feature 청록·Task 회색·Bug 빨강, 그 밖·빈 값은 중립 회색
- 산출물은 업무 데이터라 repo 밖에 쓴다

## ticket_schedule.py — 계획 항목 일정 점검·일정 코멘트 일괄 작성

`/ad:ticket-schedule` 스킬의 결정적 층이다. `scan`은 `tag: {YYMM}-planned Type: Feature State: Open, {In Progress}` Feature와 진행중 Feature의 미해결 하위 Task를 모아 항목별 계획 일정(Open → `시작예정일`, In Progress → `완료목표일`)과 status를 JSON으로 낸다. `apply`는 사용자가 확정한 계획 JSON의 각 항목을 검증하고 상태를 다시 조회한 뒤 표준 코멘트 한 줄을 단다. 날짜 제안과 사용자 확인은 스킬이 맡고, 분류와 쓰기는 이 도구가 맡는다. 토큰은 `YOUTRACK_TOKEN` 또는 `cred.py get youtrack-token`에서 받아 헤더에만 쓴다.

```bash
python3 tools/ticket_schedule.py scan --month 2610                                   # stdout JSON
python3 tools/ticket_schedule.py scan --month 2610 --assignee jmkim heum2 --today 2026-10-19 --out /tmp/scan.json
python3 tools/ticket_schedule.py apply --plan /tmp/plan.json --dry-run               # POST 없이 쓸 본문만
python3 tools/ticket_schedule.py apply --plan /tmp/plan.json                         # {"entries":[{"id","kind","date"}]}
```

- status: `ok`(날짜 ≥ 기준일) / `overdue`(날짜 < 기준일, 상태 그대로) / `unparsed`(필요 라벨은 없지만 날짜처럼 보이는 코멘트, 반대 kind 라벨만 있는 경우 포함) / `unscheduled` — 추정값(월말·생성일)으로 채우지 않는다
- 라벨: 코멘트 어느 줄이든 `{라벨}: {날짜}`. 시작 `시작예정일`·레거시 `예상 시작일`·`예상 시작 일자`·`예상시작일`, 완료 `완료목표일`·레거시 `예상 종료일`·`예상 완료일`. 같은 kind는 가장 최근 코멘트가 이긴다
- 날짜는 `YYYY-MM-DD`와 `M월 D일`만 인정한다. `M월 D일` 연도는 대상 월 연도이고, 6개월 넘게 떨어지면 ±1년 보정한다
- `--assignee`는 하위 확장 뒤 항목 단위(Feature·Task)로 login을 거른다. 정렬은 담당자 → Feature → 그 하위 Task
- apply 결과 `posted` / `skipped`(`state_changed`: 현재 상태의 kind가 계획과 다름, `already_set`: 같은 날짜가 이미 최신 라벨) / `error`(입력 검증·조회·POST 실패). POST는 재시도하지 않는다 — 중복 코멘트를 막는다
- scan `--out`은 티켓 코멘트를 담은 업무 데이터라 repo 밖 경로만 받는다
