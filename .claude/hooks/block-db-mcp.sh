#!/usr/bin/env bash
# Block DB-related MCP tool calls. Non-DB MCP servers are allowed.
set -euo pipefail

tool=$(jq -r '.tool_name // ""')

# DB keywords. Matched case-insensitively as substring in tool_name ("mcp__<server>__<tool>").
db_re='(sql|mssql|sqlserver|postgres|postgresql|mysql|mariadb|oracle|sqlite|mongo|mongodb|redis|dynamo|dynamodb|bigquery|snowflake|cassandra|cosmos|firestore|elasticsearch|opensearch|clickhouse|database|rdbms)'

if [[ "$tool" == mcp__* ]] && printf '%s' "$tool" | grep -qiE "$db_re"; then
  cat <<JSON
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"DB 관련 MCP는 이 프로젝트에서 사용 금지 (도구: ${tool}). sqlcmd/REST/팀 스킬로 대체할 것."}}
JSON
fi
exit 0
