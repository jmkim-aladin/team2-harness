#!/usr/bin/env bash
# vault 정기 sweep — generate_vault_indexes + sync_harness_links + lint_vault 일괄.
#
# 권장 cron (매일 09:00):
#   0 9 * * * /Users/jm/Documents/workspace/team2/tools/vault_sweep.sh
# 또는 launchd plist로 등록.
#
# Usage:
#   tools/vault_sweep.sh              # dry-run (default)
#   tools/vault_sweep.sh --apply      # 실 실행
#   tools/vault_sweep.sh --apply --quiet  # 출력 최소화

set -e

HARNESS_ROOT="${HARNESS_ROOT:-/Users/jm/Documents/workspace/team2}"
VAULT="${VAULT:-/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2}"

APPLY=""
QUIET=""
for arg in "$@"; do
  case "$arg" in
    --apply) APPLY="--apply" ;;
    --quiet) QUIET="1" ;;
  esac
done

log() {
  [ -z "$QUIET" ] && echo "[vault_sweep $(date +%H:%M:%S)] $*"
}

log "vault: $VAULT"
log "harness: $HARNESS_ROOT"
log "mode: ${APPLY:-dry-run}"

# 1. _index.md regen (services/processes/hub)
log "=== generate_vault_indexes ==="
python3 "$HARNESS_ROOT/tools/generate_vault_indexes.py" --vault "$VAULT" $APPLY \
  2>&1 | grep -E "^(mode|created|replaced|inserted|skipped|staged)" | sed 's/^/  /'

# 2. harness-link / team-members / policy-index 갱신
log "=== sync_harness_links ==="
python3 "$HARNESS_ROOT/tools/sync_harness_links.py" \
  --vault "$VAULT" --harness "$HARNESS_ROOT" $APPLY \
  2>&1 | grep -E "^(mode|created|replaced|inserted|skipped|missing|staged)" | sed 's/^/  /'

# 3. lint 전체 — apply가 아니어도 항상 lint (검증성)
log "=== lint_vault ==="
if python3 "$HARNESS_ROOT/tools/lint_vault.py" --vault "$VAULT" --all 2>&1 | tail -3; then
  LINT_RC=0
else
  LINT_RC=$?
fi

log "done (lint exit=$LINT_RC)"
exit $LINT_RC
