#!/usr/bin/env python3
"""Run one safe Hermes dispatch preparation cycle.

This combines board projection, dispatch request rendering, and pending batch
calculation for the existing Hermes Discord bot adapter. It never calls Discord
APIs and never mutates YouTrack, KB, git, DB, or production systems.
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
import hermes_dispatch_consumer
import export_hermes_discord_outbox


DEFAULT_VAULT = "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
DEFAULT_BATCH_PATH = "wiki/projects/agentic-os/hermes-discord-dispatch-batch.json"
DEFAULT_OUTBOX_PATH = "wiki/projects/agentic-os/hermes-discord-outbox"


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def write_json(path: Path, payload: dict[str, Any], *, apply: bool) -> list[str]:
    if not apply:
        return [f"would write {path}"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return [f"wrote {path}"]


def run_cycle(
    vault: Path,
    *,
    apply: bool,
    updated_at: str | None = None,
    batch_output: Path | None = None,
    outbox_base: str | None = None,
) -> dict[str, Any]:
    updated = updated_at or today()
    cards = decision_board.collect_cards(vault)
    messages = decision_board.write_projection(vault, cards, updated, apply=apply)

    board_payload = decision_board.render_json(cards, updated)
    request_payloads = dispatch_request.build_payloads(board_payload)
    request = dispatch_request.render_payload_file(request_payloads)
    request_path = vault / dispatch_request.DEFAULT_OUTPUT_PATH
    messages.extend(dispatch_request.write_payloads(request_path, request_payloads, apply=apply))

    ack_path = vault / hermes_dispatch_consumer.DEFAULT_ACK_PATH
    ack = hermes_dispatch_consumer.read_json_optional(ack_path)
    batch = hermes_dispatch_consumer.build_batch(request, ack)
    if batch_output:
        messages.extend(write_json(batch_output, batch, apply=apply))
    outbox = None
    if outbox_base:
        outbox = export_hermes_discord_outbox.build_outbox(batch, base_rel_path=outbox_base)
        messages.extend(export_hermes_discord_outbox.write_outbox(vault, batch, outbox, apply=apply))

    result = {
        "schema": "team2.hermes_dispatch_cycle.v1",
        "mode": "apply" if apply else "dry-run",
        "updated_at": updated,
        "board": {
            "cards": len(cards),
            "path": decision_board.DEFAULT_JSON_PATH,
        },
        "dispatch_request": {
            "request_id": request["request_id"],
            "payload_count": len(request.get("payloads") or []),
            "path": dispatch_request.DEFAULT_OUTPUT_PATH,
        },
        "batch": batch,
        "messages": messages,
    }
    if outbox:
        result["outbox"] = outbox
    return result


def resolve_batch_output(vault: Path, value: Path | None) -> Path | None:
    if value is None:
        return None
    if value.is_absolute():
        return value
    return vault / value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", type=Path, default=Path(os.environ.get("LOCAL_WIKI_PATH", DEFAULT_VAULT)))
    parser.add_argument("--batch-output", type=Path)
    parser.add_argument("--default-batch-output", action="store_true")
    parser.add_argument("--outbox", default=None)
    parser.add_argument("--default-outbox", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    vault = args.vault.resolve()
    batch_output = args.batch_output
    if args.default_batch_output and batch_output is None:
        batch_output = Path(DEFAULT_BATCH_PATH)
    outbox_base = args.outbox
    if args.default_outbox and outbox_base is None:
        outbox_base = DEFAULT_OUTBOX_PATH
    result = run_cycle(
        vault,
        apply=args.apply,
        batch_output=resolve_batch_output(vault, batch_output),
        outbox_base=outbox_base,
    )

    print(f"mode: {result['mode']}", file=sys.stderr)
    print(f"cards: {result['board']['cards']}", file=sys.stderr)
    print(f"request_id: {result['dispatch_request']['request_id']}", file=sys.stderr)
    print(f"pending_payloads: {result['batch']['payload_count']}", file=sys.stderr)
    for message in result["messages"]:
        print(message, file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
