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


HUMAN_REQUEST_FIELDS = ("question", "reason", "recommendation", "evidence")
UNRESOLVED_COLUMNS = {"Decision Needed", "Approval Needed", "Blocked"}
REVIEW_COLUMNS = {"Review Needed", "Done Candidate"}


def is_ready_human_request(card: dict[str, Any]) -> bool:
    """Only attention=human with a complete four-field packet reaches the user."""
    if card.get("attention") != "human":
        return False
    request = card.get("human_request")
    if not isinstance(request, dict):
        return False
    return all(isinstance(request.get(field), str) and request[field].strip() for field in HUMAN_REQUEST_FIELDS)


def attention_state(card: dict[str, Any]) -> str:
    attention = card.get("attention")
    if attention == "human":
        return "human" if is_ready_human_request(card) else "human-incomplete"
    if attention == "agent":
        return "agent"
    return "legacy-unrouted"


def needs_human_prep(card: dict[str, Any]) -> bool:
    """Decision/approval/blocker labels whose question an agent must check or prepare.

    The label alone is not a human dependency; it only marks work to review.
    """
    if is_ready_human_request(card):
        return False
    return (card.get("agent_task") or {}).get("kind") == "complete-human-request" or card.get("attention") == "human" or card_value(card, "column") in UNRESOLVED_COLUMNS


def split_cards(cards: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    human = [card for card in cards if is_ready_human_request(card)]
    agent = [card for card in cards if not is_ready_human_request(card)]
    return human, agent


def agent_roles(card: dict[str, Any]) -> list[str]:
    roles = [role for role in card.get("suggested_roles", []) if role in ROLE_CHANNELS]
    if roles:
        return list(dict.fromkeys(roles))
    return ["qa" if card_value(card, "column") in REVIEW_COLUMNS else "domain_analyst"]


def build_board_summary(cards: list[dict[str, Any]], updated_at: str) -> str:
    counts = {column: 0 for column in COLUMN_ORDER}
    for card in cards:
        column = card_value(card, "column")
        counts[column] = counts.get(column, 0) + 1
    human, agent = split_cards(cards)
    states = [attention_state(card) for card in agent]
    lines = [f"## Agent Board Summary ({updated_at})", ""]
    for column in COLUMN_ORDER:
        lines.append(f"- {column}: {counts.get(column, 0)}")
    lines.extend(
        [
            "",
            f"- 사용자 요청 준비 완료: {len(human)}",
            f"- AI 검토 대기: {len(agent)}"
            f" (attention 미지정 {states.count('legacy-unrouted')}, human 패킷 미완성 {states.count('human-incomplete')})",
            f"- AI 검토·질문 준비: {sum(1 for card in agent if needs_human_prep(card))}",
        ]
    )
    return "\n".join(lines)


def build_user_digest(cards: list[dict[str, Any]], updated_at: str) -> str:
    human, agent = split_cards(cards)
    prep = sum(1 for card in agent if needs_human_prep(card))
    lines = [f"## Orchestrator Digest ({updated_at})", ""]
    if human:
        lines.append(f"사용자 결정·승인 요청 {len(human)}건.")
    else:
        lines.append("현재 사용자에게 올릴 결정·승인 요청 없음.")
    lines.extend(
        [
            f"AI 검토 대기 {len(agent)}건 · AI 검토·질문 준비 {prep}건 — 요청이 없다는 것이 완료나 승인을 뜻하지 않는다.",
            "",
        ]
    )
    for index, card in enumerate(human, start=1):
        request = card["human_request"]
        lines.extend(
            [
                f"### {index}. {card_heading(card)}",
                f"- 질문: {request['question'].strip()}",
                f"- 이유: {request['reason'].strip()}",
                f"- 권장: {request['recommendation'].strip()}",
                f"- 근거: {request['evidence'].strip()}",
                f"- Work: `{card_value(card, 'work_id')}` · Ticket: {ticket_text(card)}",
                f"- Source: `{card_value(card, 'path')}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def build_task_brief(card: dict[str, Any], role: str) -> str:
    state = attention_state(card)
    lines = [
        "## Task Brief",
        "",
        f"- Role: {role} (profile: `configs/discord-agent-profiles.yaml` roles.{role})",
        f"- Card: {card_value(card, 'id') or card_value(card, 'path')}",
        f"- Work: `{card_value(card, 'work_id')}`",
        f"- Ticket: {ticket_text(card)}",
        f"- Service: {card_value(card, 'service') or '없음'}",
        f"- Goal: {card_value(card, 'title')}",
        f"- Current Status: {card_value(card, 'column')}",
        f"- Attention: {state}",
        f"- Source Note: `{card_value(card, 'path')}`",
        "- First: read the source note, related source code and test output yourself before concluding",
        "- Verify: independently validate each material conclusion; record source revision, environment, result and limits in the vault note",
        "- Review Rule: resolve a factual review only after recording that evidence; needs-review alone is not a user request",
    ]
    if state == "legacy-unrouted":
        lines.append("- Triage: attention is missing (legacy card); classify it with evidence instead of escalating to the user")
    if state == "human-incomplete":
        lines.append("- Triage: human packet is incomplete; fill question/reason/recommendation/evidence from verified facts before the orchestrator asks")
    if needs_human_prep(card):
        lines.append(
            "- Labels: the column label alone does not establish a human dependency. Close a factual or stale request "
            "only on recorded evidence or an existing documented decision; genuinely unresolved policy choices and "
            "execution approvals stay pending and are never self-approved. If a genuine user decision remains, "
            "draft human_request (question, reason, recommendation, evidence) for the orchestrator"
        )
    agent_task = card.get("agent_task")
    next_action = agent_task.get("next_action") if isinstance(agent_task, dict) else None
    if isinstance(next_action, str) and next_action.strip():
        lines.append(f"- Next Action: {next_action.strip()}")
    lines.extend(
        [
            "- Allowed Actions: read-only analysis, local tests, evidence recording and vault note updates within authorization",
            "- Forbidden Actions: YouTrack/KB/git/DB/prod mutation or canonical promotion without user approval",
            "- Expected Output: verification evidence and either a resolved factual review or a human_request draft back to orchestrator",
            "- Verification Guidance: read `$TEAM2_HARNESS_PATH/docs/agents/verification.md` before completion or handoff",
        ]
    )
    return "\n".join(lines)


def build_payloads(board: dict[str, Any]) -> list[dict[str, str]]:
    cards = [card for card in board.get("cards") or [] if isinstance(card, dict)]
    updated_at = str(board.get("updated_at") or now_stamp())
    payloads: list[dict[str, str]] = [
        {"channel": "agent-board", "content": build_board_summary(cards, updated_at)},
        {"channel": "jm-orchestrator", "content": build_user_digest(cards, updated_at)},
    ]
    _, agent = split_cards(cards)
    for card in agent:
        for role in agent_roles(card):
            payloads.append({"channel": ROLE_CHANNELS[role], "content": build_task_brief(card, role)})
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
