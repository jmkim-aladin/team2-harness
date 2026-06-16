#!/usr/bin/env python3
"""Prepare pending Hermes Discord dispatch payloads.

This is a reference consumer core for Hermes. It reads the dispatch request and
ack files, calculates idempotent pending payloads, and can render the ack Hermes
should write after its existing Discord bot has sent messages.

It does not call Discord APIs and does not mutate YouTrack, KB, git, DB, or
production systems.
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


DEFAULT_VAULT = "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
DEFAULT_REQUEST_PATH = "wiki/projects/agentic-os/hermes-discord-dispatch-request.json"
DEFAULT_ACK_PATH = "wiki/projects/agentic-os/hermes-discord-dispatch-ack.json"


def request_id(request: dict[str, Any]) -> str:
    return str(request.get("request_id") or "")


def payload_id(payload: dict[str, Any]) -> str:
    return str(payload.get("payload_id") or "")


def ack_matches_request(request: dict[str, Any], ack: dict[str, Any] | None) -> bool:
    return bool(ack) and str(ack.get("request_id") or "") == request_id(request)


def dispatched_ids_from_ack(request: dict[str, Any], ack: dict[str, Any] | None) -> set[str]:
    if not ack_matches_request(request, ack):
        return set()
    assert ack is not None
    return {
        str(item.get("payload_id") or "")
        for item in ack.get("payloads") or []
        if str(item.get("status") or "") == "dispatched"
    }


def pending_payloads(request: dict[str, Any], ack: dict[str, Any] | None) -> list[dict[str, Any]]:
    dispatched_ids = dispatched_ids_from_ack(request, ack)
    return [payload for payload in request.get("payloads") or [] if payload_id(payload) not in dispatched_ids]


def build_batch(request: dict[str, Any], ack: dict[str, Any] | None) -> dict[str, Any]:
    payloads = pending_payloads(request, ack)
    return {
        "schema": "team2.hermes_discord_dispatch_batch.v1",
        "request_id": request_id(request),
        "dispatch_required": bool(payloads),
        "payload_count": len(payloads),
        "payloads": payloads,
    }


def build_updated_ack(
    request: dict[str, Any],
    *,
    ack: dict[str, Any] | None,
    dispatched_payload_ids: set[str] | None,
    acked_at: str | None = None,
) -> dict[str, Any]:
    if dispatched_payload_ids is None:
        merged_ids = {payload_id(payload) for payload in request.get("payloads") or []}
    else:
        merged_ids = dispatched_ids_from_ack(request, ack) | set(dispatched_payload_ids)
    return ack_hermes_dispatch.build_ack(request, dispatched_payload_ids=merged_ids, acked_at=acked_at)


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
    parser.add_argument("--ack", type=Path)
    parser.add_argument("--payload-id", action="append", default=[])
    parser.add_argument("--mark-dispatched", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    vault = args.vault.resolve()
    request_path = args.request or (vault / DEFAULT_REQUEST_PATH)
    ack_path = args.ack or (vault / DEFAULT_ACK_PATH)
    request = read_json(request_path)
    ack = read_json_optional(ack_path)

    if args.mark_dispatched:
        dispatched = set(args.payload_id) if args.payload_id else None
        updated_ack = build_updated_ack(request, ack=ack, dispatched_payload_ids=dispatched)
        messages = write_ack(ack_path, updated_ack, apply=args.apply)
        print(f"mode: {'apply' if args.apply else 'dry-run'}", file=sys.stderr)
        print(f"request_id: {updated_ack['request_id']}", file=sys.stderr)
        print(f"dispatch_status: {updated_ack['dispatch_status']}", file=sys.stderr)
        for message in messages:
            print(message, file=sys.stderr)
        if not args.apply:
            print(json.dumps(updated_ack, ensure_ascii=False, indent=2))
        return 0

    batch = build_batch(request, ack)
    print(f"request_id: {batch['request_id']}", file=sys.stderr)
    print(f"pending_payloads: {batch['payload_count']}", file=sys.stderr)
    print(json.dumps(batch, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
