#!/usr/bin/env python3
"""Create a Hermes dispatch acknowledgement file.

Hermes can write this after it consumes hermes-discord-dispatch-request.json.
The ack is for idempotency and audit; it does not mutate Discord, YouTrack, KB,
git, DB, or production systems.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_VAULT = "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
DEFAULT_REQUEST_PATH = "wiki/projects/agentic-os/hermes-discord-dispatch-request.json"
DEFAULT_ACK_PATH = "wiki/projects/agentic-os/hermes-discord-dispatch-ack.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def build_ack(
    request: dict[str, Any],
    *,
    dispatched_payload_ids: set[str] | None,
    acked_at: str | None = None,
) -> dict[str, Any]:
    payloads = list(request.get("payloads") or [])
    dispatched = dispatched_payload_ids
    ack_payloads: list[dict[str, str]] = []
    for payload in payloads:
        payload_id = str(payload.get("payload_id") or "")
        is_dispatched = dispatched is None or payload_id in dispatched
        ack_payloads.append(
            {
                "payload_id": payload_id,
                "channel": str(payload.get("channel") or ""),
                "status": "dispatched" if is_dispatched else "pending",
            }
        )
    all_dispatched = all(item["status"] == "dispatched" for item in ack_payloads)
    return {
        "schema": "team2.hermes_discord_dispatch_ack.v1",
        "request_id": str(request.get("request_id") or ""),
        "acked_at": acked_at or now_iso(),
        "dispatch_status": "dispatched" if all_dispatched else "partial",
        "payloads": ack_payloads,
    }


def read_request(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_ack(path: Path, ack: dict[str, Any], *, apply: bool) -> list[str]:
    if not apply:
        return [f"would write {path}"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return [f"wrote {path}"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", type=Path, default=Path(os.environ.get("LOCAL_WIKI_PATH", DEFAULT_VAULT)))
    parser.add_argument("--request", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--payload-id", action="append", default=[])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    vault = args.vault.resolve()
    request_path = args.request or (vault / DEFAULT_REQUEST_PATH)
    output_path = args.output or (vault / DEFAULT_ACK_PATH)
    request = read_request(request_path)
    dispatched_ids = set(args.payload_id) if args.payload_id else None
    ack = build_ack(request, dispatched_payload_ids=dispatched_ids)
    messages = write_ack(output_path, ack, apply=args.apply)
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
