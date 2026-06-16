from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Sequence


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "queue_agent_board_action.py"
spec = importlib.util.spec_from_file_location("queue_agent_board_action", MODULE_PATH)
queue = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(queue)


def completed(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def write_state(vault: Path) -> None:
    path = vault / queue.DEFAULT_KANBAN_STATE_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "team2.hermes_kanban_sync_state.v1",
                "cards": {
                    "wiki/processes/tickets/dev2-1001.md": {
                        "task_id": "t_1001",
                        "title": "[Decision Needed] DEV2-1001",
                        "work_id": "DEV2-1001",
                        "status": "blocked",
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


class QueueAgentBoardActionTests(unittest.TestCase):
    def test_dry_run_builds_action_without_writing_or_commenting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            write_state(vault)
            calls: list[Sequence[str]] = []

            result = queue.queue_action(
                vault,
                task_id="t_1001",
                card_id=None,
                action="brief",
                instruction="결정 브리프 만들어줘",
                actor="jm",
                apply=False,
                comment_hermes=True,
                command_runner=lambda command: calls.append(command) or completed(),
                updated_at="2026-06-17T00:00:00+09:00",
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["mode"], "dry-run")
            self.assertEqual(result["item"]["card_id"], "wiki/processes/tickets/dev2-1001.md")
            self.assertEqual(calls, [])
            self.assertFalse((vault / queue.DEFAULT_QUEUE_JSONL).exists())

    def test_apply_appends_queue_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            write_state(vault)

            result = queue.queue_action(
                vault,
                task_id=None,
                card_id="wiki/processes/tickets/dev2-1001.md",
                action="delegate",
                instruction="planner에게 맡겨",
                actor="jm",
                apply=True,
                comment_hermes=False,
                updated_at="2026-06-17T00:00:00+09:00",
            )

            self.assertEqual(result["status"], "ok")
            self.assertTrue((vault / queue.DEFAULT_QUEUE_JSONL).exists())
            self.assertTrue((vault / queue.DEFAULT_QUEUE_JSON).exists())
            snapshot = json.loads((vault / queue.DEFAULT_QUEUE_JSON).read_text(encoding="utf-8"))
            self.assertEqual(snapshot["items"][0]["action"], "delegate")
            self.assertEqual(snapshot["items"][0]["task_id"], "t_1001")

    def test_apply_can_post_structured_comment_to_hermes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            write_state(vault)
            calls: list[list[str]] = []

            result = queue.queue_action(
                vault,
                task_id="t_1001",
                card_id=None,
                action="ask",
                instruction="근거를 더 찾아줘",
                actor="jm",
                apply=True,
                comment_hermes=True,
                hermes_cli="/tmp/hermes",
                command_runner=lambda command: calls.append(list(command)) or completed(stdout="commented\n"),
                updated_at="2026-06-17T00:00:00+09:00",
            )

            self.assertEqual(result["comment_status"], "posted")
            self.assertTrue(any(call[:5] == ["/tmp/hermes", "kanban", "--board", "team2", "comment"] for call in calls))
            self.assertIn("TEAM2-ACTION", " ".join(calls[0]))

    def test_rejects_unknown_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            write_state(vault)

            result = queue.queue_action(
                vault,
                task_id="t_1001",
                card_id=None,
                action="delete-everything",
                instruction="bad",
                actor="jm",
                apply=True,
                updated_at="2026-06-17T00:00:00+09:00",
            )

            self.assertEqual(result["status"], "failed")
            self.assertIn("unsupported action", result["errors"][0]["error"])


if __name__ == "__main__":
    unittest.main()
