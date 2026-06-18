from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Sequence


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "import_hermes_board_actions.py"
spec = importlib.util.spec_from_file_location("import_hermes_board_actions", MODULE_PATH)
importer = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(importer)


def completed(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def write_state(vault: Path) -> None:
    path = vault / importer.DEFAULT_KANBAN_STATE_JSON
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
                        "ticket_id": "DEV2-1001",
                        "service": "[[max]]",
                        "column": "Decision Needed",
                        "vault_path": "wiki/processes/tickets/dev2-1001.md",
                        "source_of_truth": "wiki-note",
                        "status": "blocked",
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


class ImportHermesBoardActionsTests(unittest.TestCase):
    def test_parse_slash_command_comment(self) -> None:
        parsed = importer.parse_action_comment("/brief 결정 브리프 만들어줘")

        self.assertEqual(parsed["action"], "brief")
        self.assertEqual(parsed["instruction"], "결정 브리프 만들어줘")

    def test_apply_imports_hermes_comments_into_action_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            write_state(vault)
            show_payload = {
                "task": {"id": "t_1001"},
                "comments": [
                    {
                        "author": "jm",
                        "body": "/delegate planner에게 맡겨",
                        "created_at": 1781640000,
                    }
                ],
            }

            def runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
                return completed(stdout="Container hermes-team2 Running\n" + json.dumps(show_payload, ensure_ascii=False))

            result = importer.import_actions(
                vault,
                apply=True,
                hermes_cli="/tmp/hermes",
                command_runner=runner,
                updated_at="2026-06-17T00:00:00+09:00",
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["summary"]["imported"], 1)
            snapshot = json.loads((vault / importer.DEFAULT_QUEUE_JSON).read_text(encoding="utf-8"))
            self.assertEqual(snapshot["items"][0]["action"], "delegate")
            self.assertEqual(snapshot["items"][0]["source"], "hermes-comment")
            self.assertEqual(snapshot["items"][0]["source_of_truth"], "wiki-note")
            self.assertEqual(snapshot["items"][0]["vault_path"], "wiki/processes/tickets/dev2-1001.md")
            self.assertEqual(snapshot["items"][0]["ticket_id"], "DEV2-1001")
            self.assertEqual(snapshot["items"][0]["service"], "[[max]]")


if __name__ == "__main__":
    unittest.main()
