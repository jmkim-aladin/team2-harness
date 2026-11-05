#!/usr/bin/env bash
# Push/PR/YouTrack gate. Body: tools/agent_run_guard.py
# Human sessions (no PAPERCLIP_RUN_ID): not judged — push/PR confirmation happens in chat with commit/merge.
# Agent runs (PAPERCLIP_RUN_ID set): always judged; if the body cannot run, deny — unattended runs fail closed.
[ -z "${PAPERCLIP_RUN_ID:-}" ] && exit 0
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
if out="$(python3 "$repo_dir/tools/agent_run_guard.py" 2>/dev/null)"; then
  [ -n "$out" ] && printf '%s\n' "$out"
  exit 0
fi
cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"에이전트 실행(PAPERCLIP_RUN_ID)에서 가드 본체(tools/agent_run_guard.py)를 실행하지 못해 차단. 하네스 설치를 확인할 것."}}
JSON
exit 0
