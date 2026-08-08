# harness tools

팀 하네스 보조 도구 모음. 일회성 또는 정기 실행용 스크립트.

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

vault 안 md를 5 룰로 검사. pre-commit hook + 정기 sweep 호출 진입점.

룰:
1. frontmatter `type` 필수 + type별 필수 필드
2. 파일 위치 = type 기반 결정 트리 일치
3. 파일명 = kebab-case, 서비스 prefix 금지
4. file size warn (≥500 line)
5. `_index.md` 안 `<!-- llm-hint -->` 블록 의무

```bash
# 전체
python3 tools/lint_vault.py --vault "$VAULT" --all

# staged diff (pre-commit)
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

## secret_scan.py — 시크릿 유출 스캔

repo + vault를 자격증명 패턴(YouTrack perm-, AKIA, JWT, gh 토큰, 접속문자열 암호, Bearer, private key)으로 스캔. `/ad:harness-optimize 스택` 모드에 포함. 발견 시 exit 1 — **제거 + 해당 자격증명 재발급**이 원칙.

```bash
python3 tools/secret_scan.py             # 전체
python3 tools/secret_scan.py --staged    # pre-commit 용
```

오탐 방지: placeholder(`<...>`·`XXXX`·`$VAR`), 스캔 명령 자기 자신(rg/grep 패턴 인자), `.obsidian` 서드파티 코드는 제외.

## rotate_hermes_outbox.py — Discord outbox 회전

vault의 `hermes-discord-outbox/`가 무한 누적되지 않게 14일 경과 요청 디렉토리를 `~/.hermes-team2/archive/discord-outbox/YYYY-MM/`로 이동. dry-run 기본, `--apply`로 실행. `/ad:harness-optimize 스택` 주기에 포함 권장. 근거: 2026-08-08 실측 — 15,447 JSON/74MB가 vault git의 94.6% 점유.
