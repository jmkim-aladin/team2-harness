#!/usr/bin/env bash
# Correction gate: team rules born from user corrections (AI footer, subagent model). Body: tools/correction_guard.py
# Style/cost rules, not a security boundary: if the body cannot run, allow (no output).
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
python3 "$repo_dir/tools/correction_guard.py" 2>/dev/null
exit 0
