#!/usr/bin/env python3
"""Queue a DEV2 agent-board action from a Hermes task or vault card.

The queue is a vault artifact. Hermes comments are optional and only mirror the
same structured action marker onto the board for operator visibility.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Sequence


DEFAULT_VAULT = "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
DEFAULT_KANBAN_STATE_JSON = "wiki/projects/agentic-os/hermes-kanban-sync-state.json"
DEFAULT_QUEUE_JSONL = "wiki/projects/agentic-os/hermes-board-action-queue.jsonl"
DEFAULT_QUEUE_JSON = "wiki/projects/agentic-os/hermes-board-action-queue.json"
DEFAULT_HERMES_CLI = "/Users/jm/.hermes-team2/bin/cli"
DEFAULT_KANBAN_BOARD = "team2"
QUEUE_SCHEMA = "team2.hermes_board_action_queue.v1"
ITEM_SCHEMA = "team2.hermes_board_action.v1"
RESULT_SCHEMA = "team2.hermes_board_action_enqueue.v1"
ALLOWED_ACTIONS = {
    "brief",
    "ask",
    "delegate",
    "decide",
    "approve",
    "revise",
    "split",
    "snooze",
    "done",
}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def resolve_under_vault(vault: Path, rel_or_abs: str) -> Path:
    path = Path(rel_or_abs)
    return path if path.is_absolute() else vault / path


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_state(vault: Path, state_json: str = DEFAULT_KANBAN_STATE_JSON) -> dict[str, Any]:
    path = resolve_under_vault(vault, state_json)
    if not path.exists():
        return {"schema": "team2.hermes_kanban_sync_state.v1", "cards": {}}
    state = read_json(path)
    if state.get("schema") != "team2.hermes_kanban_sync_state.v1":
        raise ValueError(f"unsupported state schema: {state.get('schema')}")
    return state


def read_queue_items(vault: Path, queue_jsonl: str = DEFAULT_QUEUE_JSONL) -> list[dict[str, Any]]:
    path = resolve_under_vault(vault, queue_jsonl)
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        items.append(json.loads(line))
    return items


def write_queue_files(
    vault: Path,
    items: list[dict[str, Any]],
    *,
    queue_jsonl: str = DEFAULT_QUEUE_JSONL,
    queue_json: str = DEFAULT_QUEUE_JSON,
    updated_at: str,
) -> None:
    jsonl_path = resolve_under_vault(vault, queue_jsonl)
    json_path = resolve_under_vault(vault, queue_json)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    jsonl_path.write_text(
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in items),
        encoding="utf-8",
    )
    json_path.write_text(
        json.dumps(
            {
                "schema": QUEUE_SCHEMA,
                "updated_at": updated_at,
                "items": items,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def resolve_card_mapping(
    state: dict[str, Any],
    *,
    task_id: str | None,
    card_id: str | None,
) -> dict[str, Any]:
    cards = state.get("cards", {})
    if not isinstance(cards, dict):
        return {}
    if card_id and card_id in cards:
        item = dict(cards[card_id])
        item["card_id"] = card_id
        item.setdefault("task_id", "")
        return item
    if task_id:
        for current_card_id, item in cards.items():
            if isinstance(item, dict) and item.get("task_id") == task_id:
                mapped = dict(item)
                mapped["card_id"] = current_card_id
                mapped["task_id"] = task_id
                return mapped
    return {
        "card_id": card_id or "",
        "task_id": task_id or "",
    }


def action_id_for(*parts: object) -> str:
    raw = "\n".join(str(part or "") for part in parts)
    return "hba-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_action_item(
    *,
    mapping: dict[str, Any],
    action: str,
    instruction: str,
    actor: str,
    created_at: str,
    source: str = "user",
    action_id: str | None = None,
) -> dict[str, Any]:
    item_id = action_id or action_id_for(mapping.get("task_id"), mapping.get("card_id"), action, instruction, created_at)
    return {
        "schema": ITEM_SCHEMA,
        "action_id": item_id,
        "created_at": created_at,
        "actor": actor,
        "source": source,
        "source_of_truth": mapping.get("source_of_truth") or ("wiki-note" if mapping.get("card_id") else ""),
        "task_id": mapping.get("task_id") or "",
        "card_id": mapping.get("card_id") or "",
        "vault_path": mapping.get("vault_path") or mapping.get("path") or mapping.get("card_id") or "",
        "work_id": mapping.get("work_id") or "",
        "ticket_id": mapping.get("ticket_id") or "",
        "service": mapping.get("service") or "",
        "column": mapping.get("column") or "",
        "title": mapping.get("title") or "",
        "action": action,
        "instruction": instruction,
        "status": "queued",
    }


def action_comment(item: dict[str, Any]) -> str:
    lines = [
        "TEAM2-ACTION",
        f"action_id: {item['action_id']}",
        f"action: {item['action']}",
        f"status: {item['status']}",
        f"actor: {item['actor']}",
        f"card_id: {item['card_id']}",
        f"vault_path: {item.get('vault_path', '')}",
        f"instruction: {item['instruction']}",
    ]
    return "\n".join(lines)


def run_command(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        text=True,
        capture_output=True,
        check=False,
    )


def post_hermes_comment(
    item: dict[str, Any],
    *,
    hermes_cli: str,
    kanban_board: str,
    runner: Callable[[Sequence[str]], subprocess.CompletedProcess[str]],
) -> tuple[str, dict[str, Any] | None]:
    task_id = item.get("task_id")
    if not task_id:
        return "skipped", {"error": "task_id is required to comment on Hermes"}
    command = [
        hermes_cli,
        "kanban",
        "--board",
        kanban_board,
        "comment",
        str(task_id),
        action_comment(item),
        "--author",
        str(item.get("actor") or "user"),
    ]
    proc = runner(command)
    if proc.returncode != 0:
        return "failed", {"command": command, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    return "posted", None


def queue_action(
    vault: Path,
    *,
    task_id: str | None,
    card_id: str | None,
    action: str,
    instruction: str,
    actor: str,
    apply: bool,
    comment_hermes: bool = False,
    hermes_cli: str = DEFAULT_HERMES_CLI,
    kanban_board: str = DEFAULT_KANBAN_BOARD,
    command_runner: Callable[[Sequence[str]], subprocess.CompletedProcess[str]] | None = None,
    updated_at: str | None = None,
    source: str = "user",
    action_id: str | None = None,
) -> dict[str, Any]:
    timestamp = updated_at or now_iso()
    errors: list[dict[str, Any]] = []
    runner = command_runner or run_command
    if action not in ALLOWED_ACTIONS:
        return {
            "schema": RESULT_SCHEMA,
            "mode": "apply" if apply else "dry-run",
            "status": "failed",
            "updated_at": timestamp,
            "item": {},
            "comment_status": "skipped",
            "errors": [{"error": f"unsupported action: {action}"}],
        }
    try:
        state = load_state(vault)
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "schema": RESULT_SCHEMA,
            "mode": "apply" if apply else "dry-run",
            "status": "failed",
            "updated_at": timestamp,
            "item": {},
            "comment_status": "skipped",
            "errors": [{"error": str(exc)}],
        }
    mapping = resolve_card_mapping(state, task_id=task_id, card_id=card_id)
    item = build_action_item(
        mapping=mapping,
        action=action,
        instruction=instruction,
        actor=actor,
        created_at=timestamp,
        source=source,
        action_id=action_id,
    )
    comment_status = "skipped"
    if apply:
        items = read_queue_items(vault)
        if not any(existing.get("action_id") == item["action_id"] for existing in items):
            items.append(item)
        write_queue_files(vault, items, updated_at=timestamp)
        if comment_hermes:
            comment_status, error = post_hermes_comment(
                item,
                hermes_cli=hermes_cli,
                kanban_board=kanban_board,
                runner=runner,
            )
            if error:
                errors.append(error)
    return {
        "schema": RESULT_SCHEMA,
        "mode": "apply" if apply else "dry-run",
        "status": "failed" if errors else "ok",
        "updated_at": timestamp,
        "item": item,
        "comment_status": comment_status,
        "queue_path": DEFAULT_QUEUE_JSON,
        "errors": errors,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=Path(os.environ.get("LOCAL_WIKI_PATH", DEFAULT_VAULT)))
    parser.add_argument("--task-id")
    parser.add_argument("--card-id")
    parser.add_argument("--action", required=True, choices=sorted(ALLOWED_ACTIONS))
    parser.add_argument("--instruction", default="")
    parser.add_argument("--actor", default=os.environ.get("USER", "user"))
    parser.add_argument("--comment-hermes", action="store_true")
    parser.add_argument("--hermes-cli", default=os.environ.get("HERMES_CLI", DEFAULT_HERMES_CLI))
    parser.add_argument("--kanban-board", default=os.environ.get("HERMES_KANBAN_BOARD", DEFAULT_KANBAN_BOARD))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = queue_action(
        args.vault.resolve(),
        task_id=args.task_id,
        card_id=args.card_id,
        action=args.action,
        instruction=args.instruction,
        actor=args.actor,
        apply=args.apply,
        comment_hermes=args.comment_hermes,
        hermes_cli=args.hermes_cli,
        kanban_board=args.kanban_board,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"agent board action: {result['status']}")
        print(f"mode: {result['mode']}")
        print(f"action: {result.get('item', {}).get('action', '')}")
        print(f"task: {result.get('item', {}).get('task_id', '')}")
        print(f"comment: {result['comment_status']}")
        for error in result.get("errors", []):
            print(f"error: {error}", file=sys.stderr)
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
