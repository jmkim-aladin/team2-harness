#!/usr/bin/env python3
"""Run an explicit Hermes Discord adapter command for outbox items.

This runner does not know Discord tokens or APIs. It only reads outbox item
files, passes each item path to an explicit adapter command, and writes a
delivery receipt that can later be imported into ack state.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_VAULT = "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
DEFAULT_BATCH_PATH = "wiki/projects/agentic-os/hermes-discord-dispatch-batch.json"
DEFAULT_OUTBOX_PATH = "wiki/projects/agentic-os/hermes-discord-outbox"
DEFAULT_RECEIPT_PATH = "wiki/projects/agentic-os/hermes-discord-delivery-receipt.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], *, apply: bool) -> str:
    if not apply:
        return f"would write {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return f"wrote {path}"


def item_path(vault: Path, manifest_item: dict[str, Any]) -> Path:
    path = Path(str(manifest_item.get("path") or ""))
    if path.is_absolute():
        return path
    return vault / path


def skipped_result(manifest_item: dict[str, Any], reason: str) -> dict[str, str]:
    return {
        "payload_id": str(manifest_item.get("payload_id") or ""),
        "channel": str(manifest_item.get("channel") or ""),
        "status": "skipped",
        "error": reason,
    }


def run_item(vault: Path, manifest_item: dict[str, Any], adapter_command: list[str], *, apply: bool) -> dict[str, str]:
    path = item_path(vault, manifest_item)
    if not apply:
        return skipped_result(manifest_item, "dry-run")
    if not adapter_command:
        return skipped_result(manifest_item, "adapter command missing")
    completed = subprocess.run(
        adapter_command + [str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    result = {
        "payload_id": str(manifest_item.get("payload_id") or ""),
        "channel": str(manifest_item.get("channel") or ""),
    }
    if completed.returncode == 0:
        result["status"] = "dispatched"
        external_id = completed.stdout.strip()
        if external_id:
            result["external_id"] = external_id
        return result
    result["status"] = "failed"
    error = completed.stderr.strip() or completed.stdout.strip() or f"adapter exited with {completed.returncode}"
    result["error"] = error
    return result


def build_receipt(manifest: dict[str, Any], results: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "schema": "team2.hermes_discord_delivery_receipt.v1",
        "request_id": str(manifest.get("request_id") or ""),
        "results": results,
    }


def run_adapter(
    vault: Path,
    manifest: dict[str, Any],
    *,
    adapter_command: list[str],
    receipt_output: Path,
    apply: bool,
) -> tuple[dict[str, Any], list[str]]:
    results = [
        run_item(vault, manifest_item, adapter_command, apply=apply)
        for manifest_item in manifest.get("items") or []
    ]
    receipt = build_receipt(manifest, results)
    messages = [
        f"{item['status']} {item.get('payload_id', '')} {item.get('channel', '')}".strip()
        for item in results
    ]
    messages.append(write_json(receipt_output, receipt, apply=apply))
    return receipt, messages


def resolve_manifest_path(vault: Path, manifest_path: Path | None, batch_path: Path, outbox_base: str) -> Path:
    if manifest_path:
        return manifest_path if manifest_path.is_absolute() else vault / manifest_path
    batch = read_json(batch_path if batch_path.is_absolute() else vault / batch_path)
    request_id = str(batch.get("request_id") or "")
    return vault / outbox_base.rstrip("/") / request_id / "manifest.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", type=Path, default=Path(os.environ.get("LOCAL_WIKI_PATH", DEFAULT_VAULT)))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--batch", type=Path, default=Path(DEFAULT_BATCH_PATH))
    parser.add_argument("--outbox", default=DEFAULT_OUTBOX_PATH)
    parser.add_argument("--receipt", type=Path, default=Path(DEFAULT_RECEIPT_PATH))
    parser.add_argument("--adapter-command", default="")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    vault = args.vault.resolve()
    manifest_path = resolve_manifest_path(vault, args.manifest, args.batch, args.outbox)
    receipt_path = args.receipt if args.receipt.is_absolute() else vault / args.receipt
    adapter_command = shlex.split(args.adapter_command) if args.adapter_command else []
    manifest = read_json(manifest_path)
    receipt, messages = run_adapter(
        vault,
        manifest,
        adapter_command=adapter_command,
        receipt_output=receipt_path,
        apply=args.apply,
    )

    print(f"mode: {'apply' if args.apply else 'dry-run'}", file=sys.stderr)
    print(f"request_id: {receipt['request_id']}", file=sys.stderr)
    print(f"results: {len(receipt['results'])}", file=sys.stderr)
    for message in messages:
        print(message, file=sys.stderr)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
