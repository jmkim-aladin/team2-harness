#!/usr/bin/env bash
# Obsidian URI handler wrapper.
# vault 안 파일을 macOS `open`으로 Obsidian에서 즉시 열기.
#
# Usage:
#   tools/obsidian_open.sh wiki/processes/tickets/in-progress/dev2-5749.md
#   tools/obsidian_open.sh wiki/services/max/_index.md
#   tools/obsidian_open.sh --search "DEV2-5749"        # vault 검색
#   tools/obsidian_open.sh --new wiki/processes/tickets/in-progress/dev2-XXXX.md "초기 본문"
#
# 옵션:
#   --vault NAME       Obsidian 안 vault 이름 (기본: team2)
#   --search QUERY     vault 안 검색 패널 열기
#   --new PATH BODY    새 노트 작성 (URI handler)

set -e

VAULT_NAME="${OBSIDIAN_VAULT_NAME:-team2}"

# args 파싱
MODE="open"
if [ "$1" = "--vault" ]; then
  VAULT_NAME="$2"; shift 2
fi
if [ "$1" = "--search" ]; then
  MODE="search"; shift
elif [ "$1" = "--new" ]; then
  MODE="new"; shift
fi

# URL encoder (Python stdlib — 외부 의존 회피)
urlencode() {
  python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=''))" "$1"
}

case "$MODE" in
  open)
    if [ -z "$1" ]; then
      echo "usage: $0 <vault-relative-path>" >&2
      exit 1
    fi
    FILE_ENC=$(urlencode "$1")
    VAULT_ENC=$(urlencode "$VAULT_NAME")
    URI="obsidian://open?vault=${VAULT_ENC}&file=${FILE_ENC}"
    echo "$URI"
    open "$URI"
    ;;
  search)
    if [ -z "$1" ]; then
      echo "usage: $0 --search <query>" >&2
      exit 1
    fi
    QUERY_ENC=$(urlencode "$1")
    VAULT_ENC=$(urlencode "$VAULT_NAME")
    URI="obsidian://search?vault=${VAULT_ENC}&query=${QUERY_ENC}"
    echo "$URI"
    open "$URI"
    ;;
  new)
    if [ -z "$1" ]; then
      echo "usage: $0 --new <path> [body]" >&2
      exit 1
    fi
    FILE_ENC=$(urlencode "$1")
    BODY_ENC=$(urlencode "${2:-}")
    VAULT_ENC=$(urlencode "$VAULT_NAME")
    URI="obsidian://new?vault=${VAULT_ENC}&file=${FILE_ENC}&content=${BODY_ENC}&overwrite=false"
    echo "$URI"
    open "$URI"
    ;;
esac
