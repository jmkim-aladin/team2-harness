#!/usr/bin/env python3
"""Generate the DEV2 Hermes decision board projection from vault notes.

The board is a projection, not a source of truth. It only surfaces notes that
need user decision, approval, review, or explicit unblock work.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_VAULT = "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
DEFAULT_MARKDOWN_PATH = "wiki/projects/agentic-os/hermes-decision-board.md"
DEFAULT_JSON_PATH = "wiki/projects/agentic-os/hermes-decision-board.json"

COLUMN_ORDER = [
    "Decision Needed",
    "Approval Needed",
    "Review Needed",
    "Blocked",
    "Done Candidate",
]

ROLE_ROUTING = {
    "Decision Needed": ["orchestrator", "planner"],
    "Approval Needed": ["orchestrator"],
    "Review Needed": ["orchestrator", "qa"],
    "Blocked": ["orchestrator"],
    "Done Candidate": ["orchestrator", "qa"],
}


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def split_frontmatter(text: str) -> tuple[list[str], str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    fm = text[4:end].splitlines()
    body = text[end + 5 :]
    if body.startswith("\n"):
        body = body[1:]
    return fm, body


def clean_value(value: str) -> str:
    return value.strip().strip('"').strip("'")


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str] | None:
    split = split_frontmatter(text)
    if not split:
        return None
    lines, body = split
    fm: dict[str, Any] = {}
    index = 0
    while index < len(lines):
        line = lines[index].rstrip()
        if not line or line.startswith("#") or line[:1].isspace() or ":" not in line:
            index += 1
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        raw = raw.strip()
        if raw:
            fm[key] = clean_value(raw)
            index += 1
            continue
        values: list[str] = []
        child = index + 1
        while child < len(lines) and lines[child][:1].isspace():
            match = re.match(r"^\s*-\s+(.+)$", lines[child])
            if match:
                values.append(clean_value(match.group(1)))
            child += 1
        fm[key] = values
        index = child
    return fm, body


def scalar(fm: dict[str, Any], field: str) -> str:
    value = fm.get(field)
    if isinstance(value, list):
        return value[0] if value else ""
    return str(value or "")


def list_values(fm: dict[str, Any], field: str) -> list[str]:
    value = fm.get(field)
    if isinstance(value, list):
        return [v for v in value if v]
    if isinstance(value, str) and value:
        return [value]
    return []


def classify(fm: dict[str, Any]) -> str | None:
    decision_status = scalar(fm, "decision_status")
    ticket_status = scalar(fm, "ticket_status")
    review_state = scalar(fm, "review_state")
    if decision_status == "approval-needed":
        return "Approval Needed"
    if decision_status == "decision-needed":
        return "Decision Needed"
    if decision_status == "blocked" or ticket_status == "blocked":
        return "Blocked"
    if decision_status == "review-needed" or ticket_status == "review-needed" or review_state == "needs-review":
        return "Review Needed"
    if ticket_status == "done-candidate":
        return "Done Candidate"
    return None


def title_from_body(body: str, fallback: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def note_title(fm: dict[str, Any], body: str, path: Path) -> str:
    return scalar(fm, "title") or title_from_body(body, path.stem)


def note_ticket_id(fm: dict[str, Any], rel_path: str) -> str:
    raw = scalar(fm, "ticket_id") or rel_path
    match = re.search(r"DEV2-\d+", raw, re.IGNORECASE)
    return match.group(0).upper() if match else ""


def note_work_id(fm: dict[str, Any], rel_path: str, ticket_id: str) -> str:
    if ticket_id:
        return ticket_id
    canonical_id = scalar(fm, "canonical_id")
    if canonical_id:
        return canonical_id
    return Path(rel_path).stem


def note_service(fm: dict[str, Any]) -> str:
    service = scalar(fm, "service")
    if service:
        return service
    service_id = scalar(fm, "service_id")
    if service_id:
        return f"[[{service_id}]]"
    related = list_values(fm, "related_services")
    return related[0] if related else ""


def note_summary(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("<!--"):
            continue
        if stripped.startswith("- ["):
            continue
        if stripped.startswith("- "):
            return stripped[2:].strip()
        return stripped
    return ""


def collect_cards(vault: Path) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    wiki = vault / "wiki"
    if not wiki.exists():
        return cards
    default_board = Path(DEFAULT_MARKDOWN_PATH)
    for path in sorted(wiki.rglob("*.md")):
        rel_path = path.relative_to(vault)
        if rel_path == default_board:
            continue
        parsed = parse_frontmatter(path.read_text(encoding="utf-8"))
        if not parsed:
            continue
        fm, body = parsed
        column = classify(fm)
        if not column:
            continue
        rel = str(rel_path)
        ticket_id = note_ticket_id(fm, rel)
        card = {
            "id": rel,
            "column": column,
            "title": note_title(fm, body, path),
            "work_id": note_work_id(fm, rel, ticket_id),
            "ticket_id": ticket_id,
            "service": note_service(fm),
            "type": scalar(fm, "type"),
            "path": rel,
            "summary": note_summary(body),
            "suggested_roles": ROLE_ROUTING[column],
        }
        cards.append(card)
    order = {column: index for index, column in enumerate(COLUMN_ORDER)}
    cards.sort(key=lambda card: (order.get(card["column"], 99), card["work_id"] or card["path"]))
    return cards


def card_link(card: dict[str, Any]) -> str:
    ticket_id = card.get("ticket_id", "")
    if ticket_id:
        return f"[[{ticket_id.lower()}|{ticket_id}]]"
    title = card.get("title") or card.get("work_id") or card.get("path")
    stem = Path(card.get("path", "")).stem
    if stem:
        return f"[[{stem}|{title}]]"
    return str(title)


def work_id_text(card: dict[str, Any]) -> str:
    work_id = card.get("work_id") or card.get("ticket_id") or card.get("path")
    return f"`{work_id}`"


def role_text(roles: list[str]) -> str:
    return ", ".join(f"`{role}`" for role in roles)


def render_card(card: dict[str, Any]) -> list[str]:
    service = f" · {card['service']}" if card.get("service") else ""
    summary = card.get("summary") or "요약 없음"
    return [
        f"- {card_link(card)}{service} · `{card.get('type', '')}` · 작업: {work_id_text(card)} · 역할: {role_text(card['suggested_roles'])}",
        f"  - 제목: {card['title']}",
        f"  - 요약: {summary}",
        f"  - 원본: `{card['path']}`",
    ]


def render_markdown(cards: list[dict[str, Any]], updated_at: str) -> str:
    lines = [
        "---",
        "type: project",
        "title: Hermes Decision Board",
        "canonical_id: project:agentic-os/hermes-decision-board",
        "status: draft",
        f"updated_at: {updated_at}",
        "---",
        "",
        "# Hermes Decision Board",
        "",
        "<!-- llm-hint -->",
        "이 문서는 Hermes/Discord 오케스트레이션용 decision board projection이다. 원장은 vault 업무/분석 노트와 YouTrack이다.",
        "<!-- /llm-hint -->",
        "",
        f"<!-- generated:decision-board source=vault updated={updated_at} -->",
    ]
    grouped = {column: [] for column in COLUMN_ORDER}
    for card in cards:
        grouped.setdefault(card["column"], []).append(card)
    for column in COLUMN_ORDER:
        lines.extend(["", f"## {column}", ""])
        if not grouped.get(column):
            lines.append("- (없음)")
            continue
        for card in grouped[column]:
            lines.extend(render_card(card))
    lines.extend(["", "<!-- /generated -->", ""])
    return "\n".join(lines)


def render_json(cards: list[dict[str, Any]], updated_at: str) -> dict[str, Any]:
    return {
        "schema": "team2.hermes_decision_board.v1",
        "updated_at": updated_at,
        "source": "vault",
        "cards": cards,
    }


def write_projection(
    vault: Path,
    cards: list[dict[str, Any]],
    updated_at: str,
    *,
    apply: bool,
    markdown_rel: str = DEFAULT_MARKDOWN_PATH,
    json_rel: str = DEFAULT_JSON_PATH,
) -> list[str]:
    markdown_path = vault / markdown_rel
    json_path = vault / json_rel
    messages: list[str] = []
    if apply:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(render_markdown(cards, updated_at), encoding="utf-8")
        json_path.write_text(
            json.dumps(render_json(cards, updated_at), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        messages.extend([f"wrote {markdown_rel}", f"wrote {json_rel}"])
    else:
        messages.extend([f"would write {markdown_rel}", f"would write {json_rel}"])
    return messages


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", type=Path, default=Path(os.environ.get("LOCAL_WIKI_PATH", DEFAULT_VAULT)))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--markdown-path", default=DEFAULT_MARKDOWN_PATH)
    parser.add_argument("--json-path", default=DEFAULT_JSON_PATH)
    args = parser.parse_args()

    vault = args.vault.resolve()
    cards = collect_cards(vault)
    updated_at = today()
    messages = write_projection(
        vault,
        cards,
        updated_at,
        apply=args.apply,
        markdown_rel=args.markdown_path,
        json_rel=args.json_path,
    )
    print(f"mode: {'apply' if args.apply else 'dry-run'}", file=sys.stderr)
    print(f"cards: {len(cards)}", file=sys.stderr)
    for message in messages:
        print(message, file=sys.stderr)
    if not args.apply:
        print(json.dumps(render_json(cards, updated_at), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
