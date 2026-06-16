#!/usr/bin/env python3
"""Build read-only Hermes Discord dispatch requests from the board JSON.

This tool does not call Discord APIs. Hermes owns the existing Discord bot
integration and can consume the generated dispatch request.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_VAULT = "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
DEFAULT_BOARD_PATH = "wiki/projects/agentic-os/hermes-decision-board.json"
DEFAULT_OUTPUT_PATH = "wiki/projects/agentic-os/hermes-discord-dispatch-request.json"

COLUMN_ORDER = [
    "Decision Needed",
    "Approval Needed",
    "Review Needed",
    "Blocked",
    "Done Candidate",
]

ROLE_CHANNELS = {
    "planner": "agent-planning",
    "architect": "agent-architecture",
    "developer": "agent-dev",
    "qa": "agent-qa",
    "designer": "agent-design",
    "domain_analyst": "agent-domain",
}


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def card_value(card: dict[str, Any], key: str) -> str:
    value = card.get(key)
    return str(value or "")


def ticket_text(card: dict[str, Any]) -> str:
    return card_value(card, "ticket_id") or "없음"


def card_heading(card: dict[str, Any]) -> str:
    work_id = card_value(card, "work_id") or card_value(card, "id") or card_value(card, "path")
    title = card_value(card, "title")
    service = card_value(card, "service")
    service_part = f" · {service}" if service else ""
    return f"[{card_value(card, 'column')}] {work_id}{service_part} — {title}"


def build_board_summary(cards: list[dict[str, Any]], updated_at: str) -> str:
    counts = {column: 0 for column in COLUMN_ORDER}
    for card in cards:
        column = card_value(card, "column")
        counts[column] = counts.get(column, 0) + 1
    lines = [f"## Agent Board Summary ({updated_at})", ""]
    for column in COLUMN_ORDER:
        lines.append(f"- {column}: {counts.get(column, 0)}")
    if cards:
        lines.extend(["", "### Cards"])
        for card in cards:
            lines.append(f"- {card_heading(card)}")
    else:
        lines.extend(["", "현재 board card가 없습니다."])
    return "\n".join(lines)


def build_user_digest(cards: list[dict[str, Any]], updated_at: str) -> str:
    if not cards:
        return f"## Orchestrator Digest ({updated_at})\n\n현재 사용자 개입 카드 없음."
    lines = [f"## Orchestrator Digest ({updated_at})", ""]
    for index, card in enumerate(cards, start=1):
        lines.extend(
            [
                f"### {index}. {card_heading(card)}",
                f"- Work: `{card_value(card, 'work_id')}`",
                f"- Ticket: {ticket_text(card)}",
                f"- Summary: {card_value(card, 'summary') or '요약 없음'}",
                f"- Source: `{card_value(card, 'path')}`",
                f"- Roles: {', '.join(card.get('suggested_roles', []))}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def build_task_brief(card: dict[str, Any], role: str) -> str:
    return "\n".join(
        [
            "## Task Brief",
            "",
            f"- Role: {role}",
            f"- Card: {card_value(card, 'id') or card_value(card, 'path')}",
            f"- Work: `{card_value(card, 'work_id')}`",
            f"- Ticket: {ticket_text(card)}",
            f"- Service: {card_value(card, 'service') or '없음'}",
            f"- Goal: {card_value(card, 'title')}",
            f"- Current Status: {card_value(card, 'column')}",
            f"- Source Note: `{card_value(card, 'path')}`",
            "- Allowed Actions: read-only analysis, draft evidence, vault note update proposal",
            "- Forbidden Actions: YouTrack/KB/git/DB/prod mutation without user approval",
            "- Expected Output: evidence or Decision Packet draft back to orchestrator",
        ]
    )


def build_payloads(board: dict[str, Any]) -> list[dict[str, str]]:
    cards = list(board.get("cards") or [])
    updated_at = str(board.get("updated_at") or now_stamp())
    payloads: list[dict[str, str]] = [
        {"channel": "agent-board", "content": build_board_summary(cards, updated_at)},
        {"channel": "jm-orchestrator", "content": build_user_digest(cards, updated_at)},
    ]
    for card in cards:
        for role in card.get("suggested_roles", []):
            if role == "orchestrator":
                continue
            channel = ROLE_CHANNELS.get(role)
            if not channel:
                continue
            payloads.append({"channel": channel, "content": build_task_brief(card, role)})
    return payloads


def read_board(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def with_payload_ids(payloads: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for payload in payloads:
        enriched = dict(payload)
        enriched["payload_id"] = f"hdp-{stable_digest(payload)}"
        out.append(enriched)
    return out


def render_payload_file(payloads: list[dict[str, str]]) -> dict[str, Any]:
    enriched_payloads = with_payload_ids(payloads)
    return {
        "schema": "team2.hermes_discord_dispatch_request.v1",
        "request_id": f"hdr-{stable_digest(enriched_payloads)}",
        "target": "hermes",
        "transport": "hermes-existing-discord-bot",
        "dispatch_status": "pending-hermes",
        "payloads": enriched_payloads,
    }


def write_payloads(path: Path, payloads: list[dict[str, str]], *, apply: bool) -> list[str]:
    if not apply:
        return [f"would write {path}"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(render_payload_file(payloads), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return [f"wrote {path}"]


def main() -> int:
    parser = argparse.ArgumentParser()
    default_vault = Path(os.environ.get("LOCAL_WIKI_PATH", DEFAULT_VAULT))
    parser.add_argument("--vault", type=Path, default=default_vault)
    parser.add_argument("--board", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    vault = args.vault.resolve()
    board_path = args.board or (vault / DEFAULT_BOARD_PATH)
    output_path = args.output or (vault / DEFAULT_OUTPUT_PATH)
    board = read_board(board_path)
    payloads = build_payloads(board)
    messages = write_payloads(output_path, payloads, apply=args.apply)

    print(f"mode: {'apply' if args.apply else 'dry-run'}", file=sys.stderr)
    print(f"payloads: {len(payloads)}", file=sys.stderr)
    for message in messages:
        print(message, file=sys.stderr)
    if not args.apply:
        print(json.dumps(render_payload_file(payloads), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
