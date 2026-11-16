#!/usr/bin/env bash
# AI footer gate for git commit / gh pr create|edit. Body: tools/ai_footer_guard.py
# Style rule, not a security boundary: if the body cannot run, allow (no output).
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
python3 "$repo_dir/tools/ai_footer_guard.py" 2>/dev/null
exit 0
