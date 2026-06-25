#!/usr/bin/env python3
"""Generate the DEV2 desktop decision cockpit projection."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_VAULT = "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
DEFAULT_BOARD_JSON = "wiki/projects/agentic-os/hermes-decision-board.json"
DEFAULT_KANBAN_STATE_JSON = "wiki/projects/agentic-os/hermes-kanban-sync-state.json"
DEFAULT_ACTION_QUEUE_JSON = "wiki/projects/agentic-os/hermes-board-action-queue.json"
DEFAULT_MARKDOWN_PATH = "wiki/projects/agentic-os/desktop-decision-cockpit.md"
DEFAULT_JSON_PATH = "wiki/projects/agentic-os/desktop-decision-cockpit.json"
RESULT_SCHEMA = "team2.desktop_decision_cockpit.v1"


ACTION_GUIDE = {
    "Decision Needed": ["brief", "decide", "ask", "delegate", "snooze"],
    "Approval Needed": ["approve", "revise", "ask", "snooze"],
    "Review Needed": ["brief", "done", "revise", "delegate"],
    "Blocked": ["ask", "delegate", "split", "snooze"],
    "Done Candidate": ["done", "revise"],
}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def resolve_under_vault(vault: Path, rel_or_abs: str) -> Path:
    path = Path(rel_or_abs)
    return path if path.is_absolute() else vault / path


def read_json_if_exists(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def pending_actions_for(queue: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in queue.get("items", []):
        if not isinstance(item, dict) or item.get("status") not in {"queued", "in-progress"}:
            continue
        keys = [str(item.get("card_id") or ""), str(item.get("task_id") or "")]
        for key in keys:
            if key:
                grouped.setdefault(key, []).append(item)
    return grouped


def build_items(board: dict[str, Any], state: dict[str, Any], queue: dict[str, Any]) -> list[dict[str, Any]]:
    state_cards = state.get("cards", {}) if isinstance(state.get("cards"), dict) else {}
    pending = pending_actions_for(queue)
    items: list[dict[str, Any]] = []
    for card in board.get("cards", []):
        if not isinstance(card, dict):
            continue
        card_id = str(card.get("id") or card.get("path") or "")
        mapping = state_cards.get(card_id, {}) if isinstance(state_cards.get(card_id, {}), dict) else {}
        task_id = str(mapping.get("task_id") or "")
        column = str(card.get("column") or "Review Needed")
        item_pending_by_id: dict[str, dict[str, Any]] = {}
        for action in pending.get(card_id, []) + pending.get(task_id, []):
            action_id = str(action.get("action_id") or "")
            if action_id:
                item_pending_by_id[action_id] = action
        item_pending = list(item_pending_by_id.values())
        items.append(
            {
                "card_id": card_id,
                "task_id": task_id,
                "task_status": mapping.get("status") or "unmapped",
                "column": column,
                "title": card.get("title") or "",
                "work_id": card.get("work_id") or "",
                "ticket_id": card.get("ticket_id") or "",
                "service": card.get("service") or "",
                "type": card.get("type") or "",
                "vault_path": card.get("path") or card_id,
                "summary": card.get("summary") or "요약 없음",
                "recommended_actions": ACTION_GUIDE.get(column, ["brief", "delegate", "snooze"]),
                "pending_actions": item_pending,
            }
        )
    return items


def render_json(items: list[dict[str, Any]], updated_at: str, mode: str) -> dict[str, Any]:
    pending_count = sum(len(item["pending_actions"]) for item in items)
    return {
        "schema": RESULT_SCHEMA,
        "mode": mode,
        "updated_at": updated_at,
        "cards": len(items),
        "pending_actions": pending_count,
        "items": items,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "---",
        "type: project",
        "status: draft",
        "review_state: none",
        "decision_status: none",
        "canonical_id: project:agentic-os/desktop-decision-cockpit",
        f"updated_at: {payload['updated_at']}",
        "---",
        "",
        "# DEV2 Desktop Decision Cockpit",
        "",
        "<!-- llm-hint -->",
        "컴퓨터 앞에서 Hermes blocked card를 처리하기 위한 cockpit projection이다. 원장은 각 vault note이며 이 문서는 직접 원장처럼 수정하지 않는다.",
        "<!-- /llm-hint -->",
        "",
        f"- 카드: {payload['cards']}",
        f"- pending action: {payload['pending_actions']}",
        "",
        "## 처리 규칙",
        "",
        "- Hermes Board는 지휘/승인 UI다.",
        "- Wiki note가 결정/근거/상태 원장이다.",
        "- 보드 지시는 action queue에 남기고, 최종 상태 변경은 원본 note frontmatter에 반영한다.",
        "",
        "## 지금 볼 카드",
        "",
    ]
    if not payload["items"]:
        lines.append("- 현재 확인할 카드 없음")
    for item in payload["items"]:
        title = item["work_id"] or item["title"] or item["card_id"]
        lines.extend(
            [
                f"### [{item['column']}] {title}",
                "",
                f"- Hermes task: `{item['task_id'] or 'unmapped'}` ({item['task_status']})",
                f"- 원본 위키: `{item['vault_path']}`",
                f"- 서비스: {item['service'] or '-'}",
                f"- 요약: {item['summary']}",
                f"- 권장 액션: {', '.join('`' + action + '`' for action in item['recommended_actions'])}",
                f"- 지시 예시: `team2-agent {item['recommended_actions'][0]} {item['task_id'] or '<task-id>'} \"필요한 지시를 여기에 작성\"`",
            ]
        )
        if item["pending_actions"]:
            lines.extend(["", "대기 중인 지시:"])
            for action in item["pending_actions"]:
                lines.append(f"- `{action.get('action_id')}` {action.get('action')}: {action.get('instruction', '')}")
        lines.append("")
    return "\n".join(lines)


def generate_cockpit(
    vault: Path,
    *,
    apply: bool,
    updated_at: str | None = None,
    board_json: str = DEFAULT_BOARD_JSON,
    state_json: str = DEFAULT_KANBAN_STATE_JSON,
    queue_json: str = DEFAULT_ACTION_QUEUE_JSON,
    markdown_path: str = DEFAULT_MARKDOWN_PATH,
    json_path: str = DEFAULT_JSON_PATH,
) -> dict[str, Any]:
    timestamp = updated_at or now_iso()
    board = read_json_if_exists(
        resolve_under_vault(vault, board_json),
        {"schema": "team2.hermes_decision_board.v1", "cards": []},
    )
    state = read_json_if_exists(
        resolve_under_vault(vault, state_json),
        {"schema": "team2.hermes_kanban_sync_state.v1", "cards": {}},
    )
    queue = read_json_if_exists(
        resolve_under_vault(vault, queue_json),
        {"schema": "team2.hermes_board_action_queue.v1", "items": []},
    )
    items = build_items(board, state, queue)
    payload = render_json(items, timestamp, "apply" if apply else "dry-run")
    if apply:
        md_target = resolve_under_vault(vault, markdown_path)
        json_target = resolve_under_vault(vault, json_path)
        md_target.parent.mkdir(parents=True, exist_ok=True)
        md_target.write_text(render_markdown(payload), encoding="utf-8")
        json_target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, default=Path(os.environ.get("LOCAL_WIKI_PATH", DEFAULT_VAULT)))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = generate_cockpit(args.vault.resolve(), apply=args.apply)
    except (json.JSONDecodeError, ValueError) as exc:
        result = {
            "schema": RESULT_SCHEMA,
            "mode": "apply" if args.apply else "dry-run",
            "status": "failed",
            "updated_at": now_iso(),
            "cards": 0,
            "pending_actions": 0,
            "items": [],
            "errors": [{"error": str(exc)}],
        }
    else:
        result["status"] = "ok"
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"desktop decision cockpit: {result['status']}")
        print(f"mode: {result['mode']}")
        print(f"cards: {result['cards']}")
        print(f"pending_actions: {result['pending_actions']}")
        for error in result.get("errors", []):
            print(f"error: {error}", file=sys.stderr)
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
