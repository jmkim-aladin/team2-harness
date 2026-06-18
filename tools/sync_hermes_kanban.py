#!/usr/bin/env python3
"""Sync the DEV2 vault decision board projection into Hermes Kanban.

The vault projection remains the source of truth. This script creates or
reuses Hermes Kanban tasks for active decision/review cards, blocks them so
they wait for human/orchestrator action, and completes tasks when their source
cards disappear from the projection.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Sequence


DEFAULT_VAULT = "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
DEFAULT_BOARD_JSON = "wiki/projects/agentic-os/hermes-decision-board.json"
DEFAULT_STATE_JSON = "wiki/projects/agentic-os/hermes-kanban-sync-state.json"
DEFAULT_HERMES_CLI = "/Users/jm/.hermes-team2/bin/cli"
DEFAULT_KANBAN_BOARD = "team2"
DEFAULT_KANBAN_BOARD_NAME = "DEV2 Team2"
DEFAULT_KANBAN_BOARD_DESCRIPTION = "DEV2 decision/review board synced from team2 vault projection"
DEFAULT_WORKSPACE = "dir:/workspace/team2"
DEFAULT_CREATED_BY = "team2-kanban-sync"
STATE_SCHEMA = "team2.hermes_kanban_sync_state.v1"
RESULT_SCHEMA = "team2.hermes_kanban_sync.v1"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def resolve_under_vault(vault: Path, rel_or_abs: str) -> Path:
    path = Path(rel_or_abs)
    return path if path.is_absolute() else vault / path


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_board(board_path: Path, *, apply: bool) -> dict[str, Any]:
    if not board_path.exists():
        if apply:
            raise FileNotFoundError(f"board projection not found: {board_path}")
        return {
            "schema": "team2.hermes_decision_board.v1",
            "updated_at": None,
            "source": "missing-board-dry-run",
            "cards": [],
        }
    board = read_json(board_path)
    if board.get("schema") != "team2.hermes_decision_board.v1":
        raise ValueError(f"unsupported board schema: {board.get('schema')}")
    cards = board.get("cards")
    if not isinstance(cards, list):
        raise ValueError("board JSON must contain a cards list")
    return board


def load_state(state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return {"schema": STATE_SCHEMA, "cards": {}}
    state = read_json(state_path)
    if state.get("schema") != STATE_SCHEMA:
        raise ValueError(f"unsupported state schema: {state.get('schema')}")
    if not isinstance(state.get("cards"), dict):
        raise ValueError("state JSON must contain a cards object")
    return state


def write_state(state_path: Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def board_exists(boards_stdout: str, board_slug: str) -> bool:
    for line in boards_stdout.splitlines():
        stripped = line.replace("●", " ").strip()
        if not stripped:
            continue
        parts = stripped.split()
        if parts and parts[0] == board_slug:
            return True
    return False


def command_error(command: Sequence[str], proc: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "command": list(command),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def card_assignee(card: dict[str, Any]) -> str:
    roles = card.get("suggested_roles")
    if isinstance(roles, list):
        for role in roles:
            if isinstance(role, str) and role:
                return role
    return "orchestrator"


def card_title(card: dict[str, Any]) -> str:
    label = card.get("work_id") or card.get("ticket_id") or card.get("title") or card.get("path") or card.get("id")
    return f"[{card.get('column') or 'Needs Review'}] {label}"


def card_body(card: dict[str, Any]) -> str:
    summary = str(card.get("summary") or "No summary")
    vault_path = str(card.get("path") or card.get("id") or "")
    return "\n".join(
        [
            "Source of truth: wiki note",
            "Projection: Hermes task",
            f"Column: {card.get('column') or ''}",
            f"Work ID: {card.get('work_id') or ''}",
            f"Ticket ID: {card.get('ticket_id') or ''}",
            f"Service: {card.get('service') or ''}",
            f"Type: {card.get('type') or ''}",
            f"Vault path: {vault_path}",
            "Do not mark this task done only in Hermes. Update the wiki note status fields first.",
            "",
            summary,
        ]
    )


def source_link_comment(card: dict[str, Any]) -> str:
    return "\n".join(
        [
            "TEAM2-SOURCE-LINK",
            "source_of_truth: wiki-note",
            "projection: hermes-task",
            f"vault_path: {card.get('path') or card.get('id') or ''}",
            f"work_id: {card.get('work_id') or ''}",
            f"ticket_id: {card.get('ticket_id') or ''}",
            f"service: {card.get('service') or ''}",
            "rule: update wiki note status before marking this task done",
        ]
    )


def task_spec(card: dict[str, Any], *, workspace: str) -> dict[str, str]:
    card_id = str(card.get("id") or card.get("path") or "")
    return {
        "card_id": card_id,
        "title": card_title(card),
        "body": card_body(card),
        "assignee": card_assignee(card),
        "workspace": workspace,
        "idempotency_key": f"team2-vault:{card_id}",
        "desired_status": "blocked",
        "block_reason": f"team2 vault projection: {card.get('column') or 'card'} requires human review",
    }


def hermes_create_command(
    hermes_cli: str,
    board_slug: str,
    spec: dict[str, str],
    *,
    created_by: str,
) -> list[str]:
    return [
        hermes_cli,
        "kanban",
        "--board",
        board_slug,
        "create",
        spec["title"],
        "--body",
        spec["body"],
        "--assignee",
        spec["assignee"],
        "--workspace",
        spec["workspace"],
        "--idempotency-key",
        spec["idempotency_key"],
        "--created-by",
        created_by,
        "--initial-status",
        "blocked",
        "--json",
    ]


def ensure_board(
    *,
    hermes_cli: str,
    board_slug: str,
    board_name: str,
    board_description: str,
    default_workdir: str,
    runner: Callable[[Sequence[str]], subprocess.CompletedProcess[str]],
) -> tuple[bool, list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    list_command = [hermes_cli, "kanban", "boards", "list"]
    proc = runner(list_command)
    if proc.returncode != 0:
        errors.append(command_error(list_command, proc))
        return False, errors
    if board_exists(proc.stdout, board_slug):
        return True, errors
    create_command = [
        hermes_cli,
        "kanban",
        "boards",
        "create",
        board_slug,
        "--name",
        board_name,
        "--description",
        board_description,
        "--default-workdir",
        default_workdir,
    ]
    created = runner(create_command)
    if created.returncode != 0:
        errors.append(command_error(create_command, created))
        return False, errors
    return True, errors


def summarize_operations(operations: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "ensure_active": sum(1 for item in operations if item["action"] == "ensure_active"),
        "block_active": sum(1 for item in operations if item["action"] == "block_active"),
        "complete_stale": sum(1 for item in operations if item["action"] == "complete_stale"),
    }


def sync_from_vault(
    vault: Path,
    *,
    apply: bool,
    command_runner: Callable[[Sequence[str]], subprocess.CompletedProcess[str]] | None = None,
    board_json: str = DEFAULT_BOARD_JSON,
    state_json: str = DEFAULT_STATE_JSON,
    hermes_cli: str = DEFAULT_HERMES_CLI,
    kanban_board: str = DEFAULT_KANBAN_BOARD,
    kanban_board_name: str = DEFAULT_KANBAN_BOARD_NAME,
    kanban_board_description: str = DEFAULT_KANBAN_BOARD_DESCRIPTION,
    workspace: str = DEFAULT_WORKSPACE,
    created_by: str = DEFAULT_CREATED_BY,
    updated_at: str | None = None,
) -> dict[str, Any]:
    runner = command_runner or run_command
    timestamp = updated_at or now_iso()
    board_path = resolve_under_vault(vault, board_json)
    state_path = resolve_under_vault(vault, state_json)
    board = load_board(board_path, apply=apply)
    state = load_state(state_path)
    previous_cards: dict[str, Any] = dict(state.get("cards", {}))
    cards = [card for card in board.get("cards", []) if isinstance(card, dict)]
    current_ids = {str(card.get("id") or card.get("path") or "") for card in cards}
    current_ids.discard("")
    operations: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    if apply:
        ok, board_errors = ensure_board(
            hermes_cli=hermes_cli,
            board_slug=kanban_board,
            board_name=kanban_board_name,
            board_description=kanban_board_description,
            default_workdir=workspace.removeprefix("dir:"),
            runner=runner,
        )
        errors.extend(board_errors)
        if not ok:
            return {
                "schema": RESULT_SCHEMA,
                "mode": "apply",
                "status": "failed",
                "updated_at": timestamp,
                "source_board": str(board_path),
                "state_path": str(state_path),
                "hermes_board": kanban_board,
                "cards": len(cards),
                "operations": operations,
                "summary": summarize_operations(operations),
                "errors": errors,
            }

    next_cards: dict[str, Any] = dict(previous_cards)
    for card in cards:
        spec = task_spec(card, workspace=workspace)
        if not spec["card_id"]:
            continue
        previous_item = previous_cards.get(spec["card_id"], {})
        previous_source_link_comment_at = ""
        if isinstance(previous_item, dict):
            previous_source_link_comment_at = str(previous_item.get("source_link_comment_at") or "")
        operation: dict[str, Any] = {
            "action": "ensure_active",
            "card_id": spec["card_id"],
            "title": spec["title"],
            "assignee": spec["assignee"],
            "desired_status": spec["desired_status"],
        }
        if apply:
            create_command = hermes_create_command(hermes_cli, kanban_board, spec, created_by=created_by)
            created = runner(create_command)
            if created.returncode != 0:
                errors.append(command_error(create_command, created))
                operation["status"] = "failed"
                operations.append(operation)
                continue
            try:
                task = parse_json_object(created.stdout)
            except (json.JSONDecodeError, ValueError) as exc:
                errors.append({"command": create_command, "returncode": created.returncode, "error": str(exc), "stdout": created.stdout})
                operation["status"] = "failed"
                operations.append(operation)
                continue
            task_id = str(task.get("id") or "")
            task_status = str(task.get("status") or "")
            operation.update({"task_id": task_id, "task_status": task_status, "status": "ok"})
            state_item = {
                "task_id": task_id,
                "title": spec["title"],
                "column": card.get("column") or "",
                "work_id": card.get("work_id") or "",
                "ticket_id": card.get("ticket_id") or "",
                "service": card.get("service") or "",
                "type": card.get("type") or "",
                "path": card.get("path") or card.get("id") or "",
                "vault_path": card.get("path") or card.get("id") or "",
                "source_of_truth": "wiki-note",
                "status": spec["desired_status"],
                "last_seen_at": timestamp,
                "last_synced_at": timestamp,
            }
            if previous_source_link_comment_at:
                state_item["source_link_comment_at"] = previous_source_link_comment_at
            next_cards[spec["card_id"]] = state_item
            operations.append(operation)
            is_new_mapping = spec["card_id"] not in previous_cards
            if task_id and not is_new_mapping and not previous_source_link_comment_at:
                comment_command = [
                    hermes_cli,
                    "kanban",
                    "--board",
                    kanban_board,
                    "comment",
                    task_id,
                    source_link_comment(card),
                    "--author",
                    created_by,
                ]
                commented = runner(comment_command)
                comment_operation = {
                    "action": "source_link_comment",
                    "card_id": spec["card_id"],
                    "task_id": task_id,
                }
                if commented.returncode != 0:
                    errors.append(command_error(comment_command, commented))
                    comment_operation["status"] = "failed"
                else:
                    comment_operation["status"] = "ok"
                    next_cards[spec["card_id"]]["source_link_comment_at"] = timestamp
                operations.append(comment_operation)
            if task_id and (is_new_mapping or task_status != spec["desired_status"]):
                block_command = [
                    hermes_cli,
                    "kanban",
                    "--board",
                    kanban_board,
                    "block",
                    task_id,
                    spec["block_reason"],
                ]
                blocked = runner(block_command)
                block_operation = {
                    "action": "block_active",
                    "card_id": spec["card_id"],
                    "task_id": task_id,
                    "reason": spec["block_reason"],
                }
                if blocked.returncode != 0:
                    errors.append(command_error(block_command, blocked))
                    block_operation["status"] = "failed"
                else:
                    block_operation["status"] = "ok"
                operations.append(block_operation)
        else:
            operation["status"] = "planned"
            operations.append(operation)

    for card_id, item in previous_cards.items():
        if card_id in current_ids:
            continue
        if item.get("status") in {"done", "archived"}:
            continue
        task_id = item.get("task_id")
        if not task_id:
            continue
        operation = {
            "action": "complete_stale",
            "card_id": card_id,
            "task_id": task_id,
            "reason": "source card no longer requires user intervention",
        }
        if apply:
            metadata = json.dumps(
                {
                    "source": DEFAULT_CREATED_BY,
                    "card_id": card_id,
                    "resolved_at": timestamp,
                },
                ensure_ascii=False,
            )
            complete_command = [
                hermes_cli,
                "kanban",
                "--board",
                kanban_board,
                "complete",
                str(task_id),
                "--result",
                operation["reason"],
                "--summary",
                operation["reason"],
                "--metadata",
                metadata,
            ]
            completed = runner(complete_command)
            if completed.returncode != 0:
                errors.append(command_error(complete_command, completed))
                operation["status"] = "failed"
            else:
                operation["status"] = "ok"
                stale = dict(item)
                stale.update({"status": "done", "resolved_at": timestamp, "last_synced_at": timestamp})
                next_cards[card_id] = stale
        else:
            operation["status"] = "planned"
        operations.append(operation)

    if apply and not errors:
        next_state = {
            "schema": STATE_SCHEMA,
            "updated_at": timestamp,
            "source_board": board_json,
            "hermes_board": kanban_board,
            "cards": next_cards,
        }
        write_state(state_path, next_state)

    return {
        "schema": RESULT_SCHEMA,
        "mode": "apply" if apply else "dry-run",
        "status": "failed" if errors else "ok",
        "updated_at": timestamp,
        "source_board": str(board_path),
        "state_path": str(state_path),
        "hermes_board": kanban_board,
        "cards": len(cards),
        "operations": operations,
        "summary": summarize_operations(operations),
        "errors": errors,
    }


def print_summary(result: dict[str, Any]) -> None:
    summary = result.get("summary", {})
    print(f"hermes kanban sync: {result['status']}")
    print(f"mode: {result['mode']}")
    print(f"board: {result['hermes_board']}")
    print(f"cards: {result['cards']}")
    print(
        "operations: "
        f"ensure_active={summary.get('ensure_active', 0)} "
        f"block_active={summary.get('block_active', 0)} "
        f"complete_stale={summary.get('complete_stale', 0)}"
    )
    for error in result.get("errors", []):
        print(f"error: {error}", file=sys.stderr)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=Path(os.environ.get("LOCAL_WIKI_PATH", DEFAULT_VAULT)))
    parser.add_argument("--board-json", default=DEFAULT_BOARD_JSON)
    parser.add_argument("--state-json", default=DEFAULT_STATE_JSON)
    parser.add_argument("--hermes-cli", default=os.environ.get("HERMES_CLI", DEFAULT_HERMES_CLI))
    parser.add_argument("--kanban-board", default=os.environ.get("HERMES_KANBAN_BOARD", DEFAULT_KANBAN_BOARD))
    parser.add_argument("--kanban-board-name", default=DEFAULT_KANBAN_BOARD_NAME)
    parser.add_argument("--kanban-board-description", default=DEFAULT_KANBAN_BOARD_DESCRIPTION)
    parser.add_argument("--workspace", default=DEFAULT_WORKSPACE)
    parser.add_argument("--created-by", default=DEFAULT_CREATED_BY)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = sync_from_vault(
            args.vault.resolve(),
            apply=args.apply,
            board_json=args.board_json,
            state_json=args.state_json,
            hermes_cli=args.hermes_cli,
            kanban_board=args.kanban_board,
            kanban_board_name=args.kanban_board_name,
            kanban_board_description=args.kanban_board_description,
            workspace=args.workspace,
            created_by=args.created_by,
        )
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "schema": RESULT_SCHEMA,
            "mode": "apply" if args.apply else "dry-run",
            "status": "failed",
            "updated_at": now_iso(),
            "source_board": str(resolve_under_vault(args.vault.resolve(), args.board_json)),
            "state_path": str(resolve_under_vault(args.vault.resolve(), args.state_json)),
            "hermes_board": args.kanban_board,
            "cards": 0,
            "operations": [],
            "summary": {"ensure_active": 0, "block_active": 0, "complete_stale": 0},
            "errors": [{"error": str(exc)}],
        }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_summary(result)
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
