# 운영 위키 탐색 가이드

로컬 Obsidian 운영 지식 위키와 Graphify 산출물을 활용해 서비스/API/SP/Table 관계를 효율적으로 탐색하기 위한 절차.

## 운영 위키 위치

- 로컬 Obsidian 운영 지식 위키 경로: `/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2`
- 환경 변수 참조 시: `$LOCAL_WIKI_PATH` (Claude Code `~/.claude/settings.json` env 등록)

## 탐색 우선순위

### 1. 기계적 그래프 탐색 (서비스/API/SP/Table 관계)

운영 위키의 다음 파일을 먼저 확인한다.

- `graph/contract-graph.json`
- `graph/source-inventory.json`
- `graph/unresolved-queue.json`

### 2. 사람이 문서처럼 탐색

운영 위키의 인덱스와 각 문서의 `Related Links` generated block을 먼저 본다.

- `wiki/indexes/services.md`
- `wiki/indexes/domains.md`
- `wiki/indexes/graphify.md`

### 3. Graphify sidecar

`graph/generated/graphify/{service_id}/`에 최신 Graphify sidecar 산출물이 있으면 `GRAPH_REPORT.md`의 god node, surprise edge, suggested questions를 먼저 참고한다.

## 판단 기준

- Graphify 결과는 **후보 지식**이다. canonical 판단은 다음을 따른다.
  - source path/hash
  - DEV2 graph
  - 사람 검토 기준

## 유지보수

### 링크/인덱스가 낡았을 때

팀 하네스에서 다음을 실행한다.

```bash
TEAM2_HARNESS_PATH="${TEAM2_HARNESS_PATH:-/Users/jm/Documents/workspace/team2}"
LOCAL_WIKI_PATH="${LOCAL_WIKI_PATH:-/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2}"

python3 "$TEAM2_HARNESS_PATH/tools/generate_vault_indexes.py" --vault "$LOCAL_WIKI_PATH"
python3 "$TEAM2_HARNESS_PATH/tools/lint_vault.py" --vault "$LOCAL_WIKI_PATH" --all
```

### Graphify sidecar 없음/stale

직접 실행하지 **않는다**. Graphify queue 도구가 연결된 환경에서는 queue에 등록하고, 없으면 티켓 노트나 서비스 unresolved evidence에 `ticket-graph-missing` 후보로 남긴다.

```bash
# 예: 티켓 노트 또는 서비스 unresolved evidence에 남길 후보
trigger: ticket-graph-missing
service_id: {service_id}
reason: "{이유}"
```
