# GBrain 설정

DEV2 공유 brain(gbrain)의 설정값과 검색 가이드. [CLAUDE.md](../CLAUDE.md)에서 분리해 여기를 SoT로 둔다.

## GBrain Configuration (configured by /setup-gbrain)

- Mode: remote-http shared team2 brain
- Local agent MCP URL: `http://127.0.0.1:3131/mcp`
- Hermes MCP URL: `http://gbrain-team2:3131/mcp`
- Server: Docker service `gbrain-team2` in `/Users/jm/.hermes-team2/docker-compose.yml`
- Engine: pglite at `/Users/jm/.hermes-team2/.gbrain/brain.pglite` (container path: `/opt/data/.gbrain/brain.pglite`)
- Setup date: 2026-06-17
- MCP registered: Hermes `cli`/`discord`, Codex global, Claude Code user scope
- Token storage: `/Users/jm/.hermes-team2/.env` and local agent config only. Do not commit tokens.
- Indexed sources: `team2-harness`, `team2-vault`; code files are indexed under `team2-harness`.
- Default source scope: Docker runtime sets `GBRAIN_SOURCE=team2-vault`; use explicit source selection for `team2-harness` when needed.
- Embeddings: enabled with ZeroEntropy `zembed-1`; run shared maintenance from the Docker service, not the Mac-local `~/.gbrain` PGLite.
- Hermes runtime: cron runs `tools/run_team2_knowledge_cycle.py`; Granola meeting sync runs every 10m through `tools/run_granola_sync_cycle.py`; nightly agent jobs use GBrain MCP for domain hardening drafts. Hermes may write vault draft/projection files but must not mutate YouTrack/KB/DB/prod or promote canonical state without approval.
- GBrain PGLite maintenance: host LaunchAgent `com.team2.gbrain-maintenance` runs `/Users/jm/.hermes-team2/scripts/gbrain-maintenance.sh` at 01:40 KST. This stops `gbrain-team2`, runs `sync --all`, a forced `sync --source team2-vault --full`, `extract --stale`, `embed --stale`, source-level `dream`, writes `/Users/jm/.hermes-team2/gbrain-maintenance-status.json`, then restarts the server. Read status with `/Users/jm/.hermes-team2/scripts/gbrain-maintenance.sh --status`; it must not run maintenance.

## GBrain Search Guidance (configured by /sync-gbrain)
<!-- gstack-gbrain-search-guidance:start -->

GBrain is available through the shared team2 HTTP MCP. The agent should prefer gbrain over Grep when the question is semantic, cross-document, or when the exact identifier is unknown.

Current indexed corpora:
- DEV2 harness markdown, policies, command documentation, and code files.
- Local Obsidian team2 vault notes for tickets, analyses, meetings, and domain knowledge.

Prefer gbrain when:
- "Where is X handled?" or intent-based lookup: use MCP `search` or `query`.
- "Where is symbol Y defined?" or "Who references Y?": use MCP `code_def` or `code_refs`.
- "What calls Y?" / "What does Y depend on?": use MCP `code_callers` / `code_callees`.
- "What did we decide about X?": use MCP `search` or `think`, then verify against source documents.

Grep is still right for exact strings, regex, multiline patterns, and file globs. gbrain results are retrieval candidates, not confirmed source of truth. For shared brain CLI maintenance, run commands inside the Docker service, for example `docker exec gbrain-team2 sh -lc 'HOME=/opt/data /opt/data/.local/bin/gbrain stats'`.

<!-- gstack-gbrain-search-guidance:end -->
