# Granola 회의록 동기화

Granola 공식 REST API에서 회의록을 가져와 로컬 Obsidian vault의 Tolaría 호환 `type: meeting` 노트로 저장한다.

## 사용법

```text
/ad:granola-sync                              # 최근 갱신 회의록 확인
/ad:granola-sync 2026-05                     # 2026년 5월 회의록 동기화
/ad:granola-sync 2026-05-01..2026-05-31      # 명시 기간 동기화
/ad:granola-sync 이번달                       # 이번달 회의록 동기화
/ad:granola-sync 지난달                       # 지난달 회의록 동기화
/ad:granola-sync 2026-05 한글제목             # vault/Tolaría 표시 제목 한글화
/ad:granola-sync 2026-05 전문                 # transcript 포함
/ad:granola-sync 2026-05 daily생성            # daily note가 없으면 생성
```

## 목적

- Granola 원본을 읽어 `wiki/processes/meetings/`에 회의록 노트를 생성/갱신한다.
- 기존 daily note가 있으면 `## 회의`에 회의록 링크를 추가한다.
- 사람이 보강한 `결정`, `후속 액션`, 관련 티켓/도메인 링크는 보존하고 Granola generated block만 갱신한다.
- Agentic OS의 회의/업무 준비 컨텍스트를 vault와 Tolaría에서 검색 가능하게 만든다.

## 실행 전제

| 항목 | 값 |
|---|---|
| 하네스 | `/Users/jm/Documents/workspace/team2` |
| vault | `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2` |
| 도구 | `tools/sync_granola_meetings.py` |
| API key | `GRANOLA_API_KEY` 또는 macOS Keychain service `team2-granola-api-key` |

API key 값은 절대 출력하지 않는다.

## 인자 파싱

| 입력 신호 | 처리 |
|---|---|
| `YYYY-MM` | 해당 월 1일 00:00 이상, 다음 달 1일 미만 |
| `YYYY-MM-DD..YYYY-MM-DD` | 시작일 이상, 종료일 다음 날 미만 |
| `이번달` | 현재 월 범위 |
| `지난달` | 이전 월 범위 |
| `한글제목`, `한글`, `제목` | Granola 원제목 대신 vault 표시 제목 한글화 |
| `전문`, `transcript` | `--include-transcript` 사용 |
| `daily생성`, `create-daily` | `--create-daily` 사용 |

범위가 없으면 `--updated-after` 기준으로 최근 7일을 사용한다.

## 실행 절차

1. `TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"`와 `LOCAL_WIKI_PATH="${LOCAL_WIKI_PATH:-/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2}"`를 기준 경로로 잡는다.
2. 요청에서 기간과 옵션을 파싱한다.
3. 먼저 dry-run을 실행해 생성/갱신 후보를 확인한다.
4. 사용자가 `한글제목`을 요청했거나 Granola 제목이 영어이면, Granola note id별 한글 표시 제목 매핑을 임시 JSON으로 만든다.
   - 제목은 회의 주제를 짧게 드러내는 한국어 명사구로 쓴다.
   - 파일명과 `canonical_id`는 기존 링크 안정성을 위해 영어 slug를 유지한다.
5. 실제 반영은 `--apply`를 붙여 실행한다.
6. 저장 후 `tools/generate_vault_indexes.py --vault "$LOCAL_WIKI_PATH" --target processes --apply`를 실행한다.
7. 변경된 `wiki/processes/meetings/*`, `wiki/processes/daily/*`, `wiki/processes/meetings/meetings-index.md`를 대상으로 `tools/lint_vault.py`를 실행한다.
8. 결과에는 생성/갱신 건수, daily link 여부, lint 결과를 요약한다.

## 명령 예시

최근 7일 갱신분:

```bash
python3 "$TEAM2_HARNESS_PATH/tools/sync_granola_meetings.py" \
  --vault "$LOCAL_WIKI_PATH" \
  --updated-after "$(date -v-7d +%Y-%m-%d)"
```

2026년 5월:

```bash
python3 "$TEAM2_HARNESS_PATH/tools/sync_granola_meetings.py" \
  --vault "$LOCAL_WIKI_PATH" \
  --created-after 2026-05-01 \
  --created-before 2026-06-01 \
  --apply
```

한글 표시 제목 매핑:

```bash
python3 "$TEAM2_HARNESS_PATH/tools/sync_granola_meetings.py" \
  --vault "$LOCAL_WIKI_PATH" \
  --created-after 2026-05-01 \
  --created-before 2026-06-01 \
  --title-map /tmp/granola-title-map.json \
  --apply
```

## 보존 규칙

- Granola API는 읽기 전용으로 사용한다. Granola 원본 제목/본문을 수정하지 않는다.
- vault 기존 회의록은 `granola_id`로 찾아 중복 생성을 피한다.
- 기존 회의록의 generated block만 갱신한다.
- `--title-map`이 있으면 frontmatter `title`, H1, daily link alias만 갱신한다.
- transcript는 기본 저장하지 않는다. 사용자가 명시한 경우에만 저장한다.
- daily note 신규 생성은 기본 비활성화한다. 사용자가 명시한 경우에만 `--create-daily`를 사용한다.

## 검증

```bash
python3 "$TEAM2_HARNESS_PATH/tools/lint_vault.py" \
  --vault "$LOCAL_WIKI_PATH" \
  --files wiki/processes/meetings/meetings-index.md

python3 -m unittest tests/test_sync_granola_meetings.py
```

ARGUMENTS: $ARGUMENTS
