#!/usr/bin/env bash
# Compatibility entry point: dev SELECT guard; DML uses db_execute.py.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
exec python3 "$repo_dir/tools/db_sqlcmd_guard.py"
