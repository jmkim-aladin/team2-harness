from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "run_work_board.py"
spec = importlib.util.spec_from_file_location("run_work_board", MODULE_PATH)
work_board = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(work_board)


def write_note(vault: Path, rel_path: str, text: str) -> None:
    path = vault / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class RunWorkBoardTests(unittest.TestCase):
    def test_apply_generates_board_and_hermes_dispatch_request(self) -> None:
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
                        "---",
                        "",
                        "A안 추천",
                        "",
                    ]
                ),
            )

            result = work_board.run_cycle(vault, apply=True, updated_at="2026-06-17")

            board_json = vault / "wiki/projects/agentic-os/hermes-decision-board.json"
            dispatch_json = vault / "wiki/projects/agentic-os/hermes-discord-dispatch-request.json"
            self.assertEqual(result["cards"], 1)
            self.assertEqual(result["payloads"], 3)
            self.assertTrue(board_json.exists())
            self.assertTrue(dispatch_json.exists())
            self.assertEqual(json.loads(board_json.read_text(encoding="utf-8"))["cards"][0]["work_id"], "DEV2-1001")
            self.assertEqual(
                json.loads(dispatch_json.read_text(encoding="utf-8"))["schema"],
                "team2.hermes_discord_dispatch_request.v1",
            )

    def test_dry_run_does_not_write_projection_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)

            result = work_board.run_cycle(vault, apply=False, updated_at="2026-06-17")

            self.assertEqual(result["cards"], 0)
            self.assertEqual(result["payloads"], 2)
            self.assertFalse((vault / "wiki/projects/agentic-os/hermes-decision-board.json").exists())
            self.assertIn("would write", "\n".join(result["messages"]))


if __name__ == "__main__":
    unittest.main()
