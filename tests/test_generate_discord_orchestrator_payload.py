from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "generate_discord_orchestrator_payload.py"
spec = importlib.util.spec_from_file_location("generate_discord_orchestrator_payload", MODULE_PATH)
payloads = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(payloads)


class GenerateDiscordOrchestratorPayloadTests(unittest.TestCase):
    def test_builds_board_digest_user_digest_and_role_handoffs(self) -> None:
        board = {
            "schema": "team2.hermes_decision_board.v1",
            "updated_at": "2026-06-17",
            "cards": [
                {
                    "column": "Decision Needed",
                    "work_id": "DEV2-1001",
                    "ticket_id": "DEV2-1001",
                    "service": "[[storefront]]",
                    "title": "결제 정책 선택",
                    "summary": "A안 추천",
                    "path": "wiki/processes/tickets/dev2-1001.md",
                    "suggested_roles": ["orchestrator", "planner"],
                },
                {
                    "column": "Review Needed",
                    "work_id": "project:agentic-os/discord-orchestration",
                    "ticket_id": "",
                    "service": "",
                    "title": "Discord 오케스트레이션 설계 검토",
                    "summary": "역할 프로필 계약 검토 필요",
                    "path": "wiki/projects/agentic-os/discord-orchestration.md",
                    "suggested_roles": ["orchestrator", "qa", "designer"],
                },
            ],
        }

        result = payloads.build_payloads(board)

        self.assertEqual(
            [item["channel"] for item in result],
            ["agent-board", "jm-orchestrator", "agent-planning", "agent-qa", "agent-design"],
        )
        self.assertIn("Decision Needed: 1", result[0]["content"])
        self.assertIn("Review Needed: 1", result[0]["content"])
        self.assertIn("DEV2-1001", result[1]["content"])
        self.assertIn("project:agentic-os/discord-orchestration", result[1]["content"])
        self.assertIn("## Task Brief", result[2]["content"])
        self.assertIn("Role: planner", result[2]["content"])
        self.assertIn("Ticket: 없음", result[3]["content"])
        self.assertIn("Role: designer", result[4]["content"])

    def test_empty_board_only_reports_no_user_intervention(self) -> None:
        board = {
            "schema": "team2.hermes_decision_board.v1",
            "updated_at": "2026-06-17",
            "cards": [],
        }

        result = payloads.build_payloads(board)

        self.assertEqual([item["channel"] for item in result], ["agent-board", "jm-orchestrator"])
        self.assertIn("현재 사용자 개입 카드 없음", result[1]["content"])

    def test_apply_writes_hermes_dispatch_request_without_sending_to_discord(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "hermes-discord-dispatch-request.json"
            items = [{"channel": "agent-board", "content": "요약"}]

            messages = payloads.write_payloads(out, items, apply=True)

            self.assertEqual(messages, [f"wrote {out}"])
            stored = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(stored["target"], "hermes")
            self.assertEqual(stored["transport"], "hermes-existing-discord-bot")
            self.assertEqual(stored["dispatch_status"], "pending-hermes")
            self.assertRegex(stored["request_id"], r"^hdr-[0-9a-f]{16}$")
            self.assertRegex(stored["payloads"][0]["payload_id"], r"^hdp-[0-9a-f]{16}$")
            self.assertEqual(stored["payloads"][0]["channel"], items[0]["channel"])
            self.assertEqual(stored["payloads"][0]["content"], items[0]["content"])

    def test_render_payload_file_ids_are_stable_for_same_payloads(self) -> None:
        items = [{"channel": "agent-board", "content": "요약"}]

        first = payloads.render_payload_file(items)
        second = payloads.render_payload_file(items)

        self.assertEqual(first["request_id"], second["request_id"])
        self.assertEqual(first["payloads"][0]["payload_id"], second["payloads"][0]["payload_id"])


if __name__ == "__main__":
    unittest.main()
