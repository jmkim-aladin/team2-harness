# /ad:* 스킬 본문 vault 경로 갱신 (Sub 7) 설계

## 배경

Sub 1~5에서 vault 택소노미, frontmatter 표준, harness ↔ vault sync를 구축했지만 `.claude/commands/ad/*.md` 스킬 본문은 옛 vault 경로(`wiki/{daily,meetings,tickets,okr,domains,inventory,contracts}/`)를 그대로 참조. 일부는 Phase 5에서 부분 갱신됐으나 불충분.

Sub 7은 모든 `/ad:*` 스킬 본문을 새 vault 경로·frontmatter 표준에 일치시킨다.

## 원칙

1. **새 vault 경로** — `processes/{daily,meetings,weekly,tickets,okr,incidents,capacity,sprint,team}/`, `services/{svc}/{domains,analysis,decisions,proposals,processes}/`
2. **frontmatter 표준 사용** — `ticket_id, ticket_status, assignee, service, sprint` 필드 query/write
3. **vault 경로 표현 일관** — 절대 prefix 권장 (사용자 환경 매크로 처리), 본문 설명은 상대
4. **스킬 chain 연결** — work-prep → weekly-report → sprint-close-check 경로 일관
5. **사람 검토 포인트 보존** — 스킬 본문의 사용자 안내·예시는 가능한 보존

## 갱신 대상 스킬

| 스킬 | 핵심 변경 |
|---|---|
| `ad:work-prep` | `auto-prep/{id}.md` 입력 + `in-progress/{id}.md` 출력 + `daily/{date}.md` 아젠다 |
| `ad:weekly-report` | tickets frontmatter query, output `processes/weekly/{YYYY-MM-NW}-draft.md` |
| `ad:weekly-planned` | output `processes/weekly/{date}-w{N}.md` |
| `ad:sprint-close-check` | tickets frontmatter status·assignee 필터 |
| `ad:capacity-plan` | output `processes/capacity/{YYYY-MM}.md` |
| `ad:service-activity` | tickets frontmatter service 필터, output `services/{svc}/processes/activity-{period}.md` |
| `ad:ticket` | OKR/티켓 산출물 링크 새 경로 |
| `ad:okr` | (Phase 5에서 일부 갱신) frontmatter 표준 안내 추가 |
| `ad:data-request` | (Phase 5 갱신) frontmatter 안내 추가 |
| `ad:harness-optimize` | (Sub 1.5 drift 추가) frontmatter validation 단계 추가 |

## 공통 변경

### 경로 표기 컨벤션

- vault 절대 prefix: `/Users/user/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2/` (스킬 본문에서 user 환경 매크로처럼 사용)
- vault 상대 (vault root): `wiki/processes/...`, `wiki/services/...`
- shell 예제 = 절대, 본문 설명 = 상대

### frontmatter 표준 안내

ticket 산출물 다루는 스킬에 한 줄 추가:
```
frontmatter 표준: ticket_id, ticket_status (auto-prep|in-progress|done|backlog), assignee, service, sprint (YYYY-MM). 상세 vault `wiki/guides/frontmatter-spec.md`.
```

### 결정 트리 cross-link

모든 스킬 본문 적절 위치에 한 줄:
```
> 문서 위치 결정: harness `policies/knowledge-base-policy.md` (repo↔vault 경계) + vault `wiki/guides/document-placement.md` (vault 내부 트리).
```

## 스킬별 상세

### `ad:work-prep`

- 출력 위치: `wiki/processes/tickets/in-progress/{DEV2-id}.md` (frontmatter 표준)
- 입력 옵션: vault에 `wiki/processes/tickets/auto-prep/{DEV2-id}.md` 있으면 그 본문을 시작점으로 정리
- daily 아젠다: `wiki/processes/daily/{date}.md` 의 `오늘의 아젠다`에 ticket 링크 추가
- 옛 `wiki/tickets/`, `wiki/daily/` 참조 제거

### `ad:weekly-report`

- 데이터 수집: `find vault wiki/processes/tickets -name '*.md'` + frontmatter parse
- 필터: `assignee == {user}` AND `sprint == {YYYY-MM}` AND (`ticket_status in (in-progress, done)` OR Feature 매칭)
- 출력 경로: `wiki/processes/weekly/{YYYY-MM-NW}-draft.md`
- KB `DEV2-A-696` source of truth + 표기 규칙 §4 그대로 유지

### `ad:weekly-planned`

- 출력 경로: `wiki/processes/weekly/{date}-w{N}.md`
- 회의록 링크: `wiki/processes/meetings/`
- 옛 `wiki/meetings/`, `wiki/weekly/` 직접 참조 제거

### `ad:sprint-close-check`

- 데이터: tickets frontmatter query (status·assignee·sprint·tag)
- 점검 카테고리(미종료/결과물링크/SP/5W1H/OKR 누락)는 기존 유지
- 조회만, 변경 없음

### `ad:capacity-plan`

- 출력 옵션 (`저장`): `wiki/processes/capacity/{YYYY-MM}.md`
- frontmatter 추가:
  ```yaml
  type: capacity-plan
  year: 2026
  month: 6
  assignees: [jmkim, heum2, pms0905, hyeryun]
  ```
- 옛 `wiki/capacity/` 참조 제거

### `ad:service-activity`

- 필터: `frontmatter.service == {service_id}` OR YouTrack 태그 매칭
- 출력 옵션: `wiki/services/{service_id}/processes/activity-{period}.md`
- 옛 vault 저장 경로 갱신

### `ad:ticket`

- OKR 참조 경로: `vault wiki/processes/okr/` (이미 Phase 5 일부 갱신)
- 추가 정리: 본문 내 `docs/okr/` 잔존 표현 없는지 grep 후 정정

### `ad:okr`

- 경로는 Phase 5에서 vault `wiki/processes/okr/`로 갱신됨
- 추가: frontmatter 표준 안내 (`type: okr, year, quarter, scope, assignee`)

### `ad:data-request`

- 경로는 Phase 5 갱신됨
- 추가: 결과물 vault 위치 = `wiki/services/{svc}/proposals/` 또는 `wiki/processes/tickets/{status}/` 선택 명시

### `ad:harness-optimize`

- Sub 1.5에서 drift 점검 절차 추가됨
- 추가 단계: frontmatter 스키마 검증 (`tickets/**/*.md`, `services/*/_index.md` 필수 필드 확인)
- generated block stale 점검 안내 (sync_harness_links --dry-run)

## Sub 7 산출물

1. `.claude/commands/ad/work-prep.md` 갱신
2. `.claude/commands/ad/weekly-report.md` 갱신
3. `.claude/commands/ad/weekly-planned.md` 갱신
4. `.claude/commands/ad/sprint-close-check.md` 갱신
5. `.claude/commands/ad/capacity-plan.md` 갱신
6. `.claude/commands/ad/service-activity.md` 갱신
7. `.claude/commands/ad/ticket.md` 갱신
8. `.claude/commands/ad/okr.md` 갱신 (frontmatter 안내)
9. `.claude/commands/ad/data-request.md` 갱신 (출력 위치 안내)
10. `.claude/commands/ad/harness-optimize.md` 갱신 (frontmatter 검증 추가)
11. harness commit 1건 (단일 통합)

## 비범위

- 스킬 동작 실 테스트 (사용자 평소 사용으로 검증)
- 야간 auto-prep 자동화 구현 (Sub 6)
- 신규 스킬 추가
- vault 내부 구조 추가 변경

## 검증

- `.claude/commands/ad/*.md`에서 옛 `wiki/{daily,meetings,tickets,okr,domains,inventory,contracts}/` (slash로 끝남) 잔존 grep 결과 0 (또는 의도된 표현만)
- 스킬 chain 경로 일관 (work-prep 출력 = weekly-report 입력)
- frontmatter 표준 사용 안내 ticket-handling 스킬에 포함됨
- 결정 트리 cross-link 포함됨
- AI footer 0건
