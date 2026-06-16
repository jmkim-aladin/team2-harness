#!/usr/bin/env python3
"""Import Hermes Discord delivery receipts into dispatch ack state.

Hermes writes a delivery receipt after its existing Discord bot adapter sends
outbox items. This tool merges successful receipt rows into the idempotency ack.
Failed rows remain pending for retry.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import ack_hermes_dispatch
import hermes_dispatch_consumer


DEFAULT_VAULT = "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
DEFAULT_RECEIPT_PATH = "wiki/projects/agentic-os/hermes-discord-delivery-receipt.json"
DEFAULT_REQUEST_PATH = "wiki/projects/agentic-os/hermes-discord-dispatch-request.json"
DEFAULT_ACK_PATH = "wiki/projects/agentic-os/hermes-discord-dispatch-ack.json"


def dispatched_ids_from_receipt(receipt: dict[str, Any]) -> set[str]:
    return {
        str(item.get("payload_id") or "")
        for item in receipt.get("results") or []
        if str(item.get("status") or "") == "dispatched"
    }


def validate_receipt_request(request: dict[str, Any], receipt: dict[str, Any]) -> None:
    request_id = str(request.get("request_id") or "")
    receipt_id = str(receipt.get("request_id") or "")
    if request_id != receipt_id:
        raise ValueError(f"receipt request_id {receipt_id} does not match request {request_id}")


def build_ack_from_receipt(
    request: dict[str, Any],
    receipt: dict[str, Any],
    *,
    existing_ack: dict[str, Any] | None,
    acked_at: str | None = None,
) -> dict[str, Any]:
    validate_receipt_request(request, receipt)
    dispatched = hermes_dispatch_consumer.dispatched_ids_from_ack(request, existing_ack)
    dispatched |= dispatched_ids_from_receipt(receipt)
    return ack_hermes_dispatch.build_ack(request, dispatched_payload_ids=dispatched, acked_at=acked_at)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_optional(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return read_json(path)


def write_ack(path: Path, ack: dict[str, Any], *, apply: bool) -> list[str]:
    return ack_hermes_dispatch.write_ack(path, ack, apply=apply)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", type=Path, default=Path(os.environ.get("LOCAL_WIKI_PATH", DEFAULT_VAULT)))
    parser.add_argument("--request", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--ack", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    vault = args.vault.resolve()
    request_path = args.request or (vault / DEFAULT_REQUEST_PATH)
    receipt_path = args.receipt or (vault / DEFAULT_RECEIPT_PATH)
    ack_path = args.ack or (vault / DEFAULT_ACK_PATH)
    request = read_json(request_path)
    receipt = read_json(receipt_path)
    existing_ack = read_json_optional(ack_path)
    ack = build_ack_from_receipt(request, receipt, existing_ack=existing_ack)
    messages = write_ack(ack_path, ack, apply=args.apply)

    print(f"mode: {'apply' if args.apply else 'dry-run'}", file=sys.stderr)
    print(f"request_id: {ack['request_id']}", file=sys.stderr)
    print(f"dispatch_status: {ack['dispatch_status']}", file=sys.stderr)
    for message in messages:
        print(message, file=sys.stderr)
    if not args.apply:
        print(json.dumps(ack, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
