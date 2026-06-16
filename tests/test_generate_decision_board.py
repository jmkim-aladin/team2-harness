from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "generate_decision_board.py"
spec = importlib.util.spec_from_file_location("generate_decision_board", MODULE_PATH)
board = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(board)


def write_note(vault: Path, rel_path: str, text: str) -> None:
    path = vault / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class GenerateDecisionBoardTests(unittest.TestCase):
    def test_collects_only_user_intervention_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            write_note(
                vault,
                "wiki/processes/tickets/dev2-1001.md",
                "\n".join(
                    [
                        "---",
                        "type: ticket",
                        "title: DEV2-1001 결제 정책 선택",
                        "ticket_id: DEV2-1001",
                        "ticket_status: in-progress",
                        "decision_status: decision-needed",
                        "service: \"[[storefront]]\"",
                        "related_services:",
                        "  - \"[[storefront]]\"",
                        "---",
                        "",
                        "## 결정 패킷",
                        "",
                        "- 추천: A안",
                        "",
                    ]
                ),
            )
            write_note(
                vault,
                "wiki/processes/tickets/dev2-1002.md",
                "\n".join(
                    [
                        "---",
                        "type: ticket",
                        "title: DEV2-1002 자체 진행 가능",
                        "ticket_id: DEV2-1002",
                        "ticket_status: in-progress",
                        "decision_status: none",
                        "service: \"[[max]]\"",
                        "---",
                        "",
                        "agent가 계속 진행한다.",
                        "",
                    ]
                ),
            )
            write_note(
                vault,
                "wiki/services/storefront/analysis/payment-impact.md",
                "\n".join(
                    [
                        "---",
                        "type: analysis",
                        "title: 결제 영향 분석",
                        "service_id: storefront",
                        "review_state: needs-review",
                        "evidence_level: E2",
                        "---",
                        "",
                        "검토 필요.",
                        "",
                    ]
                ),
            )
            write_note(
                vault,
                "wiki/projects/agentic-os/discord-orchestration-upgrade.md",
                "\n".join(
                    [
                        "---",
                        "type: project",
                        "title: Discord 오케스트레이션 고도화",
                        "canonical_id: project:agentic-os/discord-orchestration-upgrade",
                        "decision_status: approval-needed",
                        "---",
                        "",
                        "역할 프로필 적용 승인 필요.",
                        "",
                    ]
                ),
            )

            cards = board.collect_cards(vault)

        self.assertEqual([card["column"] for card in cards], ["Decision Needed", "Approval Needed", "Review Needed"])
        self.assertEqual(cards[0]["ticket_id"], "DEV2-1001")
        self.assertEqual(cards[0]["work_id"], "DEV2-1001")
        self.assertEqual(cards[0]["suggested_roles"], ["orchestrator", "planner"])
        self.assertEqual(cards[1]["ticket_id"], "")
        self.assertEqual(cards[1]["work_id"], "project:agentic-os/discord-orchestration-upgrade")
        self.assertEqual(cards[1]["suggested_roles"], ["orchestrator"])
        self.assertEqual(cards[2]["suggested_roles"], ["orchestrator", "qa"])
        self.assertEqual(cards[2]["service"], "[[storefront]]")

    def test_renders_markdown_and_json_projection(self) -> None:
        cards = [
            {
                "id": "wiki/processes/tickets/dev2-1001.md",
                "column": "Decision Needed",
                "title": "DEV2-1001 결제 정책 선택",
                "work_id": "DEV2-1001",
                "ticket_id": "DEV2-1001",
                "service": "[[storefront]]",
                "type": "ticket",
                "path": "wiki/processes/tickets/dev2-1001.md",
                "summary": "A안 추천",
                "suggested_roles": ["orchestrator", "planner"],
            }
        ]

        markdown = board.render_markdown(cards, "2026-06-17")
        payload = board.render_json(cards, "2026-06-17")

        self.assertIn("type: project", markdown)
        self.assertIn("<!-- generated:decision-board", markdown)
        self.assertIn("## Decision Needed", markdown)
        self.assertIn("[[dev2-1001|DEV2-1001]]", markdown)
        self.assertIn("작업: `DEV2-1001`", markdown)
        self.assertEqual(payload["updated_at"], "2026-06-17")
        self.assertEqual(payload["cards"][0]["suggested_roles"], ["orchestrator", "planner"])

    def test_apply_writes_default_projection_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            cards = [
                {
                    "id": "wiki/processes/tickets/dev2-1001.md",
                    "column": "Approval Needed",
                    "title": "DEV2-1001 PR 승인",
                    "work_id": "DEV2-1001",
                    "ticket_id": "DEV2-1001",
                    "service": "[[storefront]]",
                    "type": "ticket",
                    "path": "wiki/processes/tickets/dev2-1001.md",
                    "summary": "PR 생성 승인 필요",
                    "suggested_roles": ["orchestrator"],
                }
            ]

            result = board.write_projection(vault, cards, "2026-06-17", apply=True)

            markdown_path = vault / "wiki/projects/agentic-os/hermes-decision-board.md"
            json_path = vault / "wiki/projects/agentic-os/hermes-decision-board.json"
            self.assertEqual(result, ["wrote wiki/projects/agentic-os/hermes-decision-board.md", "wrote wiki/projects/agentic-os/hermes-decision-board.json"])
            self.assertTrue(markdown_path.exists())
            self.assertTrue(json_path.exists())
            self.assertIn("Approval Needed", markdown_path.read_text(encoding="utf-8"))
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["cards"][0]["column"], "Approval Needed")


if __name__ == "__main__":
    unittest.main()
