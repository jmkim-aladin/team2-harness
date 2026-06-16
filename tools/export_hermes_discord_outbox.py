#!/usr/bin/env python3
"""Export Hermes Discord pending batch into file-based outbox items.

The outbox is a handoff format for the existing Hermes Discord bot adapter. It
does not call Discord APIs and does not mark payloads as dispatched.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


DEFAULT_VAULT = "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
DEFAULT_BATCH_PATH = "wiki/projects/agentic-os/hermes-discord-dispatch-batch.json"
DEFAULT_OUTBOX_PATH = "wiki/projects/agentic-os/hermes-discord-outbox"


def safe_id(value: Any) -> str:
    text = str(value or "")
    return "".join(ch for ch in text if ch.isalnum() or ch in ("-", "_")) or "unknown"


def item_rel_path(base_rel_path: str, request_id: str, payload_id: str) -> str:
    return f"{base_rel_path.rstrip('/')}/{safe_id(request_id)}/{safe_id(payload_id)}.json"


def manifest_rel_path(base_rel_path: str, request_id: str) -> str:
    return f"{base_rel_path.rstrip('/')}/{safe_id(request_id)}/manifest.json"


def build_outbox(batch: dict[str, Any], *, base_rel_path: str = DEFAULT_OUTBOX_PATH) -> dict[str, Any]:
    request_id = str(batch.get("request_id") or "")
    items: list[dict[str, str]] = []
    for payload in batch.get("payloads") or []:
        payload_id = str(payload.get("payload_id") or "")
        items.append(
            {
                "payload_id": payload_id,
                "channel": str(payload.get("channel") or ""),
                "path": item_rel_path(base_rel_path, request_id, payload_id),
            }
        )
    return {
        "schema": "team2.hermes_discord_outbox.v1",
        "request_id": request_id,
        "dispatch_required": bool(batch.get("dispatch_required")) and bool(items),
        "payload_count": len(items),
        "base_path": f"{base_rel_path.rstrip('/')}/{safe_id(request_id)}",
        "manifest_path": manifest_rel_path(base_rel_path, request_id),
        "items": items,
    }


def build_outbox_item(batch: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "team2.hermes_discord_outbox_item.v1",
        "request_id": str(batch.get("request_id") or ""),
        "payload_id": str(payload.get("payload_id") or ""),
        "channel": str(payload.get("channel") or ""),
        "content": str(payload.get("content") or ""),
    }


def write_json(path: Path, payload: dict[str, Any], *, apply: bool) -> str:
    if not apply:
        return f"would write {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return f"wrote {path}"


def write_outbox(vault: Path, batch: dict[str, Any], manifest: dict[str, Any], *, apply: bool) -> list[str]:
    messages: list[str] = []
    payloads_by_id = {str(payload.get("payload_id") or ""): payload for payload in batch.get("payloads") or []}
    for item in manifest.get("items") or []:
        payload = payloads_by_id.get(str(item.get("payload_id") or ""), {})
        messages.append(write_json(vault / str(item["path"]), build_outbox_item(batch, payload), apply=apply))
    messages.append(write_json(vault / str(manifest["manifest_path"]), manifest, apply=apply))
    return messages


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", type=Path, default=Path(os.environ.get("LOCAL_WIKI_PATH", DEFAULT_VAULT)))
    parser.add_argument("--batch", type=Path)
    parser.add_argument("--outbox", default=DEFAULT_OUTBOX_PATH)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    vault = args.vault.resolve()
    batch_path = args.batch or (vault / DEFAULT_BATCH_PATH)
    if not batch_path.is_absolute():
        batch_path = vault / batch_path
    batch = read_json(batch_path)
    manifest = build_outbox(batch, base_rel_path=args.outbox)
    messages = write_outbox(vault, batch, manifest, apply=args.apply)

    print(f"mode: {'apply' if args.apply else 'dry-run'}", file=sys.stderr)
    print(f"request_id: {manifest['request_id']}", file=sys.stderr)
    print(f"payloads: {manifest['payload_count']}", file=sys.stderr)
    for message in messages:
        print(message, file=sys.stderr)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
