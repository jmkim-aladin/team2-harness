#!/usr/bin/env bash
# Push/PR/YouTrack gate. Body: tools/agent_run_guard.py
# Human sessions (no PAPERCLIP_RUN_ID): python runs only when input mentions push / "pr "; any failure stays open.
# Agent runs (PAPERCLIP_RUN_ID set): always judged; if the body cannot run, deny — unattended runs fail closed.
if [ -z "${PAPERCLIP_RUN_ID:-}" ]; then
  input="$(cat)"
  case "$input" in
    *push*|*pr[[:space:]\\]*) ;;
    *) exit 0 ;;
  esac
  repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
  out="$(printf '%s' "$input" | python3 "$repo_dir/tools/agent_run_guard.py" 2>/dev/null)" || exit 0
  [ -n "$out" ] && printf '%s\n' "$out"
  exit 0
fi
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
if out="$(python3 "$repo_dir/tools/agent_run_guard.py" 2>/dev/null)"; then
  [ -n "$out" ] && printf '%s\n' "$out"
  exit 0
fi
cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"에이전트 실행(PAPERCLIP_RUN_ID)에서 가드 본체(tools/agent_run_guard.py)를 실행하지 못해 차단. 하네스 설치를 확인할 것."}}
JSON
exit 0
