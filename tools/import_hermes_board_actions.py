#!/usr/bin/env python3
"""Import structured Hermes Kanban comments into the DEV2 board action queue."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Sequence


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import queue_agent_board_action as action_queue


DEFAULT_VAULT = action_queue.DEFAULT_VAULT
DEFAULT_KANBAN_STATE_JSON = action_queue.DEFAULT_KANBAN_STATE_JSON
DEFAULT_QUEUE_JSON = action_queue.DEFAULT_QUEUE_JSON
DEFAULT_HERMES_CLI = action_queue.DEFAULT_HERMES_CLI
DEFAULT_KANBAN_BOARD = action_queue.DEFAULT_KANBAN_BOARD
RESULT_SCHEMA = "team2.hermes_board_action_import.v1"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def run_command(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        text=True,
        capture_output=True,
        check=False,
    )


def parse_json_object(stdout: str) -> dict[str, Any]:
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start < 0 or end < start:
        raise ValueError("stdout did not contain a JSON object")
    return json.loads(stdout[start : end + 1])


def parse_action_comment(body: str) -> dict[str, str] | None:
    stripped = body.strip()
    if not stripped:
        return None
    first, _, rest = stripped.partition(" ")
    if first.startswith("/") and first[1:] in action_queue.ALLOWED_ACTIONS:
        return {"action": first[1:], "instruction": rest.strip()}
    lines = stripped.splitlines()
    if not lines or lines[0].strip() != "TEAM2-ACTION":
        return None
    parsed: dict[str, str] = {}
    for line in lines[1:]:
        key, sep, value = line.partition(":")
        if sep:
            parsed[key.strip()] = value.strip()
    action = parsed.get("action", "")
    if action not in action_queue.ALLOWED_ACTIONS:
        return None
    return {
        "action_id": parsed.get("action_id", ""),
        "action": action,
        "instruction": parsed.get("instruction", ""),
    }


def task_ids_from_state(state: dict[str, Any]) -> list[tuple[str, str]]:
    cards = state.get("cards", {})
    if not isinstance(cards, dict):
        return []
    pairs: list[tuple[str, str]] = []
    for card_id, item in cards.items():
        if not isinstance(item, dict) or item.get("status") in {"done", "archived"}:
            continue
        task_id = str(item.get("task_id") or "")
        if task_id:
            pairs.append((card_id, task_id))
    return pairs


def import_actions(
    vault: Path,
    *,
    apply: bool,
    hermes_cli: str = DEFAULT_HERMES_CLI,
    kanban_board: str = DEFAULT_KANBAN_BOARD,
    command_runner: Callable[[Sequence[str]], subprocess.CompletedProcess[str]] | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    timestamp = updated_at or now_iso()
    runner = command_runner or run_command
    errors: list[dict[str, Any]] = []
    imported: list[dict[str, Any]] = []
    seen = 0
    try:
        state = action_queue.load_state(vault)
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "schema": RESULT_SCHEMA,
            "mode": "apply" if apply else "dry-run",
            "status": "failed",
            "updated_at": timestamp,
            "summary": {"seen": 0, "imported": 0, "skipped": 0},
            "items": [],
            "errors": [{"error": str(exc)}],
        }
    existing = action_queue.read_queue_items(vault)
    existing_ids = {item.get("action_id") for item in existing}
    queued = list(existing)
    for card_id, task_id in task_ids_from_state(state):
        command = [hermes_cli, "kanban", "--board", kanban_board, "show", task_id, "--json"]
        proc = runner(command)
        if proc.returncode != 0:
            errors.append({"command": command, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})
            continue
        try:
            show = parse_json_object(proc.stdout)
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append({"command": command, "error": str(exc), "stdout": proc.stdout})
            continue
        comments = show.get("comments", [])
        if not isinstance(comments, list):
            continue
        for comment in comments:
            if not isinstance(comment, dict):
                continue
            parsed = parse_action_comment(str(comment.get("body") or ""))
            if not parsed:
                continue
            seen += 1
            action_id = parsed.get("action_id") or action_queue.action_id_for(
                task_id,
                comment.get("created_at"),
                comment.get("author"),
                comment.get("body"),
            )
            if action_id in existing_ids:
                continue
            mapping = action_queue.resolve_card_mapping(state, task_id=task_id, card_id=card_id)
            item = action_queue.build_action_item(
                mapping=mapping,
                action=parsed["action"],
                instruction=parsed.get("instruction", ""),
                actor=str(comment.get("author") or "user"),
                created_at=timestamp,
                source="hermes-comment",
                action_id=action_id,
            )
            queued.append(item)
            existing_ids.add(action_id)
            imported.append(item)
    if apply and imported and not errors:
        action_queue.write_queue_files(vault, queued, updated_at=timestamp)
    return {
        "schema": RESULT_SCHEMA,
        "mode": "apply" if apply else "dry-run",
        "status": "failed" if errors else "ok",
        "updated_at": timestamp,
        "summary": {
            "seen": seen,
            "imported": len(imported),
            "skipped": seen - len(imported),
        },
        "items": imported,
        "errors": errors,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=Path(os.environ.get("LOCAL_WIKI_PATH", DEFAULT_VAULT)))
    parser.add_argument("--hermes-cli", default=os.environ.get("HERMES_CLI", DEFAULT_HERMES_CLI))
    parser.add_argument("--kanban-board", default=os.environ.get("HERMES_KANBAN_BOARD", DEFAULT_KANBAN_BOARD))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = import_actions(
        args.vault.resolve(),
        apply=args.apply,
        hermes_cli=args.hermes_cli,
        kanban_board=args.kanban_board,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        summary = result["summary"]
        print(f"hermes board action import: {result['status']}")
        print(f"mode: {result['mode']}")
        print(f"seen={summary['seen']} imported={summary['imported']} skipped={summary['skipped']}")
        for error in result.get("errors", []):
            print(f"error: {error}", file=sys.stderr)
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
