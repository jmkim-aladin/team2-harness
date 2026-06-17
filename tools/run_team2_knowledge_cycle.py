#!/usr/bin/env python3
"""Run the DEV2 Hermes knowledge cycle.

This is the deterministic job Hermes should run on a schedule. It updates the
vault projections that agents share, refreshes generated relation/index blocks,
syncs the Hermes Kanban projection, and verifies that the shared GBrain service
is reachable. It does not call YouTrack, mutate YouTrack KB, touch DBs, deploy,
commit, or push.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Sequence


DEFAULT_HARNESS = "/Users/jm/Documents/workspace/team2"
DEFAULT_VAULT = "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
DEFAULT_GBRAIN_HEALTH_URL = "http://127.0.0.1:3131/health"
DEFAULT_STATUS_JSON = "wiki/projects/agentic-os/team2-knowledge-cycle-status.json"
DEFAULT_STATUS_MD = "wiki/projects/agentic-os/team2-knowledge-cycle-status.md"

FORBIDDEN_MUTATIONS = [
    "youtrack_mutation",
    "youtrack_kb_mutation",
    "db_write",
    "production_deploy",
    "git_commit_or_push",
    "canonical_promotion",
]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def tail(text: str, *, max_lines: int = 20) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-max_lines:])


def build_steps(harness: Path, vault: Path, *, apply: bool) -> list[dict[str, Any]]:
    apply_flag = ["--apply"] if apply else []
    python = sys.executable
    tools = harness / "tools"
    return [
        {
            "name": "sync_harness_links",
            "command": [
                python,
                str(tools / "sync_harness_links.py"),
                "--vault",
                str(vault),
                "--harness",
                str(harness),
                *apply_flag,
            ],
        },
        {
            "name": "enrich_vault_relations",
            "command": [
                python,
                str(tools / "enrich_vault_relations.py"),
                "--vault",
                str(vault),
                *apply_flag,
            ],
        },
        {
            "name": "generate_vault_indexes",
            "command": [
                python,
                str(tools / "generate_vault_indexes.py"),
                "--vault",
                str(vault),
                *apply_flag,
            ],
        },
        {
            "name": "run_hermes_dispatch_cycle",
            "command": [
                python,
                str(tools / "run_hermes_dispatch_cycle.py"),
                "--vault",
                str(vault),
                "--default-batch-output",
                "--default-outbox",
                *apply_flag,
            ],
        },
        {
            "name": "sync_hermes_kanban",
            "command": [
                python,
                str(tools / "sync_hermes_kanban.py"),
                "--vault",
                str(vault),
                "--json",
                *apply_flag,
            ],
        },
        {
            "name": "import_hermes_board_actions",
            "command": [
                python,
                str(tools / "import_hermes_board_actions.py"),
                "--vault",
                str(vault),
                "--json",
                *apply_flag,
            ],
        },
        {
            "name": "generate_decision_cockpit",
            "command": [
                python,
                str(tools / "generate_decision_cockpit.py"),
                "--vault",
                str(vault),
                "--json",
                *apply_flag,
            ],
        },
    ]


def run_command(command: Sequence[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def check_gbrain_health(url: str, *, timeout: float = 5.0) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"status": "unreachable", "url": url, "error": str(exc)}

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return {"status": "invalid-response", "url": url, "body_tail": tail(body, max_lines=5)}
    payload["url"] = url
    return payload


def parse_dispatch_result(stdout: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if payload.get("schema") != "team2.hermes_dispatch_cycle.v1":
        return None
    return payload


def parse_kanban_result(stdout: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if payload.get("schema") != "team2.hermes_kanban_sync.v1":
        return None
    return payload


def parse_action_import_result(stdout: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if payload.get("schema") != "team2.hermes_board_action_import.v1":
        return None
    return payload


def parse_cockpit_result(stdout: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if payload.get("schema") != "team2.desktop_decision_cockpit.v1":
        return None
    return payload


def result_from_process(name: str, command: Sequence[str], proc: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    result = {
        "name": name,
        "command": list(command),
        "returncode": proc.returncode,
        "status": "ok" if proc.returncode == 0 else "failed",
        "stdout_tail": tail(proc.stdout),
        "stderr_tail": tail(proc.stderr),
    }
    if name == "run_hermes_dispatch_cycle" and proc.returncode == 0:
        dispatch = parse_dispatch_result(proc.stdout)
        if dispatch:
            result["dispatch"] = {
                "cards": dispatch.get("board", {}).get("cards"),
                "request_id": dispatch.get("dispatch_request", {}).get("request_id"),
                "pending_payloads": dispatch.get("batch", {}).get("payload_count"),
                "dispatch_required": dispatch.get("batch", {}).get("dispatch_required"),
            }
    if name == "sync_hermes_kanban" and proc.returncode == 0:
        kanban = parse_kanban_result(proc.stdout)
        if kanban:
            summary = kanban.get("summary", {})
            result["kanban"] = {
                "cards": kanban.get("cards"),
                "ensure_active": summary.get("ensure_active"),
                "block_active": summary.get("block_active"),
                "complete_stale": summary.get("complete_stale"),
            }
    if name == "import_hermes_board_actions" and proc.returncode == 0:
        imported = parse_action_import_result(proc.stdout)
        if imported:
            summary = imported.get("summary", {})
            result["actions"] = {
                "seen": summary.get("seen"),
                "imported": summary.get("imported"),
                "skipped": summary.get("skipped"),
            }
    if name == "generate_decision_cockpit" and proc.returncode == 0:
        cockpit = parse_cockpit_result(proc.stdout)
        if cockpit:
            result["cockpit"] = {
                "cards": cockpit.get("cards"),
                "pending_actions": cockpit.get("pending_actions"),
            }
    return result


def render_status_markdown(result: dict[str, Any]) -> str:
    review_state = "needs-review" if result["status"] != "ok" else "none"
    lines = [
        "---",
        "type: project",
        "status: draft",
        f"review_state: {review_state}",
        "decision_status: none",
        "canonical_id: project:agentic-os/team2-knowledge-cycle-status",
        f"updated_at: {result['updated_at']}",
        "---",
        "",
        "# DEV2 지식 사이클 상태",
        "",
        f"- 실행 시각: {result['updated_at']}",
        f"- 모드: {result['mode']}",
        f"- 상태: {result['status']}",
        f"- GBrain: {result['gbrain_health'].get('status', 'unknown')}",
        "",
        "## 실행 단계",
        "",
    ]
    for step in result["steps"]:
        lines.append(f"- {step['name']}: {step['status']} ({step['returncode']})")
    dispatch = dispatch_summary(result)
    if dispatch:
        lines.extend(
            [
                "",
                "## Hermes Board",
                "",
                f"- 카드: {dispatch.get('cards')}",
                f"- pending payload: {dispatch.get('pending_payloads')}",
                f"- dispatch required: {dispatch.get('dispatch_required')}",
                f"- request id: {dispatch.get('request_id')}",
            ]
        )
    kanban = kanban_summary(result)
    if kanban:
        lines.extend(
            [
                "",
                "## Hermes Kanban",
                "",
                f"- 카드: {kanban.get('cards')}",
                f"- active sync: {kanban.get('ensure_active')}",
                f"- blocked sync: {kanban.get('block_active')}",
                f"- completed stale: {kanban.get('complete_stale')}",
            ]
        )
    actions = action_summary(result)
    if actions:
        lines.extend(
            [
                "",
                "## Board Actions",
                "",
                f"- seen: {actions.get('seen')}",
                f"- imported: {actions.get('imported')}",
                f"- skipped: {actions.get('skipped')}",
            ]
        )
    cockpit = cockpit_summary(result)
    if cockpit:
        lines.extend(
            [
                "",
                "## Desktop Cockpit",
                "",
                f"- cards: {cockpit.get('cards')}",
                f"- pending actions: {cockpit.get('pending_actions')}",
            ]
        )
    lines.extend(
        [
            "",
            "## 자동 금지",
            "",
        ]
    )
    for item in result["forbidden_mutations"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_status(vault: Path, result: dict[str, Any], *, apply: bool) -> dict[str, str]:
    json_rel = Path(DEFAULT_STATUS_JSON)
    md_rel = Path(DEFAULT_STATUS_MD)
    if not apply:
        return {
            "json": json_rel.as_posix(),
            "markdown": md_rel.as_posix(),
            "status": "dry-run",
        }
    json_path = vault / json_rel
    md_path = vault / md_rel
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_status_markdown(result), encoding="utf-8")
    return {
        "json": json_rel.as_posix(),
        "markdown": md_rel.as_posix(),
        "status": "written",
    }


def dispatch_summary(result: dict[str, Any]) -> dict[str, Any] | None:
    for step in result["steps"]:
        if step.get("name") == "run_hermes_dispatch_cycle":
            return step.get("dispatch")
    return None


def kanban_summary(result: dict[str, Any]) -> dict[str, Any] | None:
    for step in result["steps"]:
        if step.get("name") == "sync_hermes_kanban":
            return step.get("kanban")
    return None


def action_summary(result: dict[str, Any]) -> dict[str, Any] | None:
    for step in result["steps"]:
        if step.get("name") == "import_hermes_board_actions":
            return step.get("actions")
    return None


def cockpit_summary(result: dict[str, Any]) -> dict[str, Any] | None:
    for step in result["steps"]:
        if step.get("name") == "generate_decision_cockpit":
            return step.get("cockpit")
    return None


def run_cycle(
    harness: Path,
    vault: Path,
    *,
    apply: bool,
    gbrain_health_url: str,
    command_runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]] | None = None,
    health_checker: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    runner = command_runner or (lambda command, cwd: run_command(command, cwd=cwd))
    check_health = health_checker or check_gbrain_health
    result: dict[str, Any] = {
        "schema": "team2.knowledge_cycle.v1",
        "mode": "apply" if apply else "dry-run",
        "updated_at": now_iso(),
        "harness_path": str(harness),
        "vault_path": str(vault),
        "gbrain_health": check_health(gbrain_health_url),
        "forbidden_mutations": FORBIDDEN_MUTATIONS,
        "steps": [],
    }

    for step in build_steps(harness, vault, apply=apply):
        proc = runner(step["command"], harness)
        step_result = result_from_process(step["name"], step["command"], proc)
        result["steps"].append(step_result)
        if proc.returncode != 0:
            result["status"] = "failed"
            break
    else:
        result["status"] = "ok"

    result["status_files"] = write_status(vault, result, apply=apply)
    return result


def print_summary(result: dict[str, Any]) -> None:
    print(f"team2 knowledge cycle: {result['status']}")
    print(f"mode: {result['mode']}")
    print(f"gbrain: {result['gbrain_health'].get('status', 'unknown')}")
    print("steps: " + ", ".join(f"{s['name']}={s['status']}" for s in result["steps"]))
    dispatch = dispatch_summary(result)
    if dispatch:
        print(
            "board: "
            f"cards={dispatch.get('cards')} "
            f"pending_payloads={dispatch.get('pending_payloads')} "
            f"dispatch_required={dispatch.get('dispatch_required')}"
        )
    kanban = kanban_summary(result)
    if kanban:
        print(
            "kanban: "
            f"cards={kanban.get('cards')} "
            f"ensure_active={kanban.get('ensure_active')} "
            f"block_active={kanban.get('block_active')} "
            f"complete_stale={kanban.get('complete_stale')}"
        )
    actions = action_summary(result)
    if actions:
        print(
            "actions: "
            f"seen={actions.get('seen')} "
            f"imported={actions.get('imported')} "
            f"skipped={actions.get('skipped')}"
        )
    cockpit = cockpit_summary(result)
    if cockpit:
        print(
            "cockpit: "
            f"cards={cockpit.get('cards')} "
            f"pending_actions={cockpit.get('pending_actions')}"
        )
    files = result.get("status_files") or {}
    if files:
        print(f"status: {files.get('status')} {files.get('markdown')}")
    failed = [s for s in result["steps"] if s["status"] != "ok"]
    for step in failed:
        print(f"failed_step: {step['name']}", file=sys.stderr)
        if step["stderr_tail"]:
            print(step["stderr_tail"], file=sys.stderr)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", type=Path, default=Path(os.environ.get("TEAM2_HARNESS_PATH", DEFAULT_HARNESS)))
    parser.add_argument("--vault", type=Path, default=Path(os.environ.get("LOCAL_WIKI_PATH", DEFAULT_VAULT)))
    parser.add_argument("--gbrain-health-url", default=os.environ.get("GBRAIN_HEALTH_URL", DEFAULT_GBRAIN_HEALTH_URL))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = run_cycle(
        args.harness.resolve(),
        args.vault.resolve(),
        apply=args.apply,
        gbrain_health_url=args.gbrain_health_url,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_summary(result)
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
