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
        "attention": "human",
        "human_request": {
            "question": "A안으로 결정하나?",
            "reason": "결제 정책은 사업 결정이다",
            "recommendation": "A안",
            "evidence": "wiki/processes/tickets/dev2-1001.md §근거",
        },
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
            self.assertIn("질문: A안으로 결정하나?", markdown)
            self.assertIn("근거: wiki/processes/tickets/dev2-1001.md §근거", markdown)
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

        self.assertEqual(len(items), 41)
        self.assertLess(markdown.count("\n"), 500)

    def test_only_ready_human_requests_become_user_items(self) -> None:
        legacy = sample_card() | {"id": "legacy"}
        legacy.pop("attention")
        incomplete = sample_card() | {"id": "incomplete", "human_request": {"question": "q", "reason": "r"}}
        review = sample_card() | {"id": "review", "column": "Review Needed", "attention": "agent"}
        approval = sample_card() | {"id": "approval", "column": "Approval Needed", "attention": "agent"}
        ready = sample_card() | {"id": "ready"}
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            write_json(vault / cockpit.DEFAULT_BOARD_JSON,
                       {"cards": [legacy, incomplete, review, approval, ready]})

            result = cockpit.generate_cockpit(vault, apply=True, updated_at="2026-09-27T00:00:00+09:00")

            self.assertEqual([item["card_id"] for item in result["items"]], ["ready"])
            self.assertEqual(result["cards"], 1)
            self.assertEqual(result["board_cards"], 5)
            self.assertEqual(result["ai_review_queued"], 4)
            self.assertEqual(result["ai_question_prep"], 3)
            markdown = (vault / cockpit.DEFAULT_MARKDOWN_PATH).read_text(encoding="utf-8")
            self.assertIn("- AI 검토 대기: 4 (보드 카드 5)", markdown)
            self.assertIn("- AI 검토·질문 준비: 3", markdown)
            self.assertEqual(markdown.count("### ["), 1)

    def test_empty_user_requests_still_report_unfinished_agent_work(self) -> None:
        approval = sample_card() | {"column": "Approval Needed", "attention": "agent"}
        items = cockpit.build_items({"cards": [approval]}, {"cards": {}}, {"items": []})
        counts = cockpit.board_counts({"cards": [approval]}, {"cards": {}}, {"items": []})
        markdown = cockpit.render_markdown(cockpit.render_json(items, "2026-09-27T00:00:00+09:00", "apply", counts))

        self.assertIn("- 현재 사용자에게 올릴 결정·승인 요청 없음", markdown)
        self.assertIn("- AI 검토·질문 준비: 1", markdown)
        self.assertIn("요청이 없다는 것은 완료나 승인을 뜻하지 않는다", markdown)
        self.assertIn("라벨만으로 사람이 필요한 일이 되지 않는다", markdown)
        self.assertIn("스스로 승인하지 않는다", markdown)


if __name__ == "__main__":
    unittest.main()
