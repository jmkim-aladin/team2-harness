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

운영 위키에서 다음을 실행한다.

```bash
python3 scripts/generate_wiki.py
python3 scripts/lint_wiki.py
```

### Graphify sidecar 없음/stale

직접 실행하지 **않는다**. 대신 운영 위키에서 queue에 등록한다.

```bash
python3 scripts/plan_graphify_runs.py
# 또는
python3 scripts/enqueue_graphify_trigger.py --service {service_id} --trigger ticket-graph-missing --reason "{이유}"
```
