from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "generate_decision_cockpit.py"
spec = importlib.util.spec_from_file_location("generate_decision_cockpit", MODULE_PATH)
cockpit = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(cockpit)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sample_card() -> dict[str, object]:
    return {
        "id": "wiki/processes/tickets/dev2-1001.md",
        "column": "Decision Needed",
        "title": "DEV2-1001 결제 정책 선택",
        "work_id": "DEV2-1001",
        "ticket_id": "DEV2-1001",
        "service": "[[max]]",
        "type": "ticket",
        "path": "wiki/processes/tickets/dev2-1001.md",
        "summary": "A안을 선택할지 결정 필요",
        "suggested_roles": ["orchestrator", "planner"],
    }


class GenerateDecisionCockpitTests(unittest.TestCase):
    def test_apply_writes_cockpit_markdown_and_json_with_task_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            write_json(
                vault / cockpit.DEFAULT_BOARD_JSON,
                {
                    "schema": "team2.hermes_decision_board.v1",
                    "updated_at": "2026-06-17",
                    "cards": [sample_card()],
                },
            )
            write_json(
                vault / cockpit.DEFAULT_KANBAN_STATE_JSON,
                {
                    "schema": "team2.hermes_kanban_sync_state.v1",
                    "cards": {
                        "wiki/processes/tickets/dev2-1001.md": {
                            "task_id": "t_1001",
                            "status": "blocked",
                        }
                    },
                },
            )
            write_json(
                vault / cockpit.DEFAULT_ACTION_QUEUE_JSON,
                {
                    "schema": "team2.hermes_board_action_queue.v1",
                    "items": [
                        {
                            "action_id": "hba-test",
                            "task_id": "t_1001",
                            "card_id": "wiki/processes/tickets/dev2-1001.md",
                            "action": "brief",
                            "status": "queued",
                        }
                    ],
                },
            )

            result = cockpit.generate_cockpit(vault, apply=True, updated_at="2026-06-17T00:00:00+09:00")

            self.assertEqual(result["schema"], "team2.desktop_decision_cockpit.v1")
            self.assertEqual(result["cards"], 1)
            self.assertEqual(result["pending_actions"], 1)
            self.assertEqual(result["items"][0]["task_id"], "t_1001")
            self.assertIn("brief", result["items"][0]["recommended_actions"])
            markdown = (vault / cockpit.DEFAULT_MARKDOWN_PATH).read_text(encoding="utf-8")
            self.assertIn("# DEV2 Desktop Decision Cockpit", markdown)
            self.assertIn("t_1001", markdown)
            self.assertIn("wiki/processes/tickets/dev2-1001.md", markdown)
            self.assertIn("team2-agent brief t_1001", markdown)
            stored = json.loads((vault / cockpit.DEFAULT_JSON_PATH).read_text(encoding="utf-8"))
            self.assertEqual(stored["items"][0]["pending_actions"][0]["action_id"], "hba-test")

    def test_dry_run_does_not_write_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            write_json(
                vault / cockpit.DEFAULT_BOARD_JSON,
                {
                    "schema": "team2.hermes_decision_board.v1",
                    "updated_at": "2026-06-17",
                    "cards": [sample_card()],
                },
            )

            result = cockpit.generate_cockpit(vault, apply=False, updated_at="2026-06-17T00:00:00+09:00")

            self.assertEqual(result["mode"], "dry-run")
            self.assertEqual(result["cards"], 1)
            self.assertFalse((vault / cockpit.DEFAULT_MARKDOWN_PATH).exists())
            self.assertFalse((vault / cockpit.DEFAULT_JSON_PATH).exists())

    def test_markdown_stays_below_vault_lint_warning_for_full_board(self) -> None:
        cards = [sample_card() | {"id": f"wiki/processes/tickets/dev2-{index}.md"} for index in range(41)]
        items = cockpit.build_items({"cards": cards}, {"cards": {}}, {"items": []})
        markdown = cockpit.render_markdown(cockpit.render_json(items, "2026-06-17T00:00:00+09:00", "apply"))

        self.assertLess(markdown.count("\n"), 500)


if __name__ == "__main__":
    unittest.main()
