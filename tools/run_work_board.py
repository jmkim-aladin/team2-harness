#!/usr/bin/env python3
"""Run the DEV2 work-board projection cycle.

This is the shared CLI entry point for Claude Code and Codex. It generates the
Hermes board projection and the Hermes Discord dispatch request without calling
Discord or mutating YouTrack/KB/git/DB.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import generate_decision_board as decision_board
import generate_discord_orchestrator_payload as dispatch_request


DEFAULT_VAULT = "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def run_cycle(vault: Path, *, apply: bool, updated_at: str | None = None) -> dict[str, Any]:
    updated = updated_at or today()
    cards = decision_board.collect_cards(vault)
    messages = decision_board.write_projection(vault, cards, updated, apply=apply)
    board_payload = decision_board.render_json(cards, updated)
    payloads = dispatch_request.build_payloads(board_payload)
    dispatch_path = vault / dispatch_request.DEFAULT_OUTPUT_PATH
    messages.extend(dispatch_request.write_payloads(dispatch_path, payloads, apply=apply))
    return {
        "updated_at": updated,
        "cards": len(cards),
        "payloads": len(payloads),
        "messages": messages,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", type=Path, default=Path(os.environ.get("LOCAL_WIKI_PATH", DEFAULT_VAULT)))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    result = run_cycle(args.vault.resolve(), apply=args.apply)
    print(f"mode: {'apply' if args.apply else 'dry-run'}", file=sys.stderr)
    print(f"cards: {result['cards']}", file=sys.stderr)
    print(f"payloads: {result['payloads']}", file=sys.stderr)
    for message in result["messages"]:
        print(message, file=sys.stderr)
    if not args.apply:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
