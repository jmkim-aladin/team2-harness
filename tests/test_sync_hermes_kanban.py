from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Sequence


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "sync_hermes_kanban.py"
spec = importlib.util.spec_from_file_location("sync_hermes_kanban", MODULE_PATH)
sync = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(sync)


def completed(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def write_board(vault: Path, cards: list[dict[str, object]]) -> Path:
    board_path = vault / sync.DEFAULT_BOARD_JSON
    board_path.parent.mkdir(parents=True, exist_ok=True)
    board_path.write_text(
        json.dumps(
            {
                "schema": "team2.hermes_decision_board.v1",
                "updated_at": "2026-06-17",
                "source": "vault",
                "cards": cards,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return board_path


class SyncHermesKanbanTests(unittest.TestCase):
    def test_task_body_points_back_to_wiki_source_of_truth(self) -> None:
        card = {
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

        body = sync.card_body(card)

        self.assertIn("Source of truth: wiki note", body)
        self.assertIn("Projection: Hermes task", body)
        self.assertIn("Vault path: wiki/processes/tickets/dev2-1001.md", body)
        self.assertIn("Do not mark this task done only in Hermes.", body)

    def test_dry_run_plans_active_and_stale_operations_without_cli_or_state_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            write_board(
                vault,
                [
                    {
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
                ],
            )
            state_path = vault / sync.DEFAULT_STATE_JSON
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps(
                    {
                        "schema": "team2.hermes_kanban_sync_state.v1",
                        "cards": {
                            "wiki/processes/tickets/dev2-9999.md": {
                                "task_id": "t_old",
                                "status": "blocked",
                            }
                        },
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            calls: list[Sequence[str]] = []

            result = sync.sync_from_vault(
                vault,
                apply=False,
                command_runner=lambda command: calls.append(command) or completed(),
                updated_at="2026-06-17T00:00:00+09:00",
            )

            self.assertEqual(result["mode"], "dry-run")
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["summary"]["ensure_active"], 1)
            self.assertEqual(result["summary"]["complete_stale"], 1)
            self.assertEqual(calls, [])
            stored_state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertNotIn("wiki/processes/tickets/dev2-1001.md", stored_state["cards"])

    def test_apply_creates_board_creates_task_blocks_ready_task_and_writes_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            write_board(
                vault,
                [
                    {
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
                ],
            )
            calls: list[list[str]] = []

            def runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
                calls.append(list(command))
                text = " ".join(command)
                if "boards list" in text:
                    return completed(stdout="SLUG NAME COUNTS\n")
                if "boards create" in text:
                    return completed(stdout="created board team2\n")
                if " create " in text and "--json" in command:
                    return completed(stdout='Container hermes-team2 Running\n{"id":"t_new","status":"ready"}')
                if " block " in text:
                    return completed(stdout="blocked t_new\n")
                return completed()

            result = sync.sync_from_vault(
                vault,
                apply=True,
                command_runner=runner,
                hermes_cli="/tmp/hermes",
                updated_at="2026-06-17T00:00:00+09:00",
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["summary"]["ensure_active"], 1)
            self.assertEqual(result["summary"]["block_active"], 1)
            self.assertTrue(any(call[:4] == ["/tmp/hermes", "kanban", "boards", "create"] for call in calls))
            self.assertTrue(any("block" in call for call in calls))
            state = json.loads((vault / sync.DEFAULT_STATE_JSON).read_text(encoding="utf-8"))
            item = state["cards"]["wiki/processes/tickets/dev2-1001.md"]
            self.assertEqual(item["task_id"], "t_new")
            self.assertEqual(item["status"], "blocked")
            self.assertEqual(item["source_of_truth"], "wiki-note")
            self.assertEqual(item["vault_path"], "wiki/processes/tickets/dev2-1001.md")
            self.assertEqual(item["ticket_id"], "DEV2-1001")
            self.assertEqual(item["service"], "[[max]]")

    def test_apply_completes_stale_tasks_from_previous_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            write_board(vault, [])
            state_path = vault / sync.DEFAULT_STATE_JSON
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps(
                    {
                        "schema": "team2.hermes_kanban_sync_state.v1",
                        "cards": {
                            "wiki/processes/tickets/dev2-1001.md": {
                                "task_id": "t_old",
                                "status": "blocked",
                            }
                        },
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            calls: list[list[str]] = []

            def runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
                calls.append(list(command))
                if command[-2:] == ["boards", "list"]:
                    return completed(stdout="team2 DEV2 Team2 blocked=1\n")
                return completed(stdout="ok\n")

            result = sync.sync_from_vault(
                vault,
                apply=True,
                command_runner=runner,
                hermes_cli="/tmp/hermes",
                updated_at="2026-06-17T00:00:00+09:00",
            )

            self.assertEqual(result["summary"]["complete_stale"], 1)
            self.assertTrue(any("complete" in call and "t_old" in call for call in calls))
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["cards"]["wiki/processes/tickets/dev2-1001.md"]["status"], "done")

    def test_apply_blocks_new_task_even_when_create_reports_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            write_board(
                vault,
                [
                    {
                        "id": "wiki/processes/tickets/dev2-1001.md",
                        "column": "Review Needed",
                        "title": "DEV2-1001 검토",
                        "work_id": "DEV2-1001",
                        "ticket_id": "DEV2-1001",
                        "service": "[[max]]",
                        "type": "ticket",
                        "path": "wiki/processes/tickets/dev2-1001.md",
                        "summary": "검토 필요",
                        "suggested_roles": ["orchestrator"],
                    }
                ],
            )
            calls: list[list[str]] = []

            def runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
                calls.append(list(command))
                text = " ".join(command)
                if "boards list" in text:
                    return completed(stdout="team2 DEV2 Team2 blocked=1\n")
                if " create " in text and "--json" in command:
                    return completed(stdout='{"id":"t_new","status":"blocked"}')
                return completed(stdout="ok\n")

            result = sync.sync_from_vault(
                vault,
                apply=True,
                command_runner=runner,
                hermes_cli="/tmp/hermes",
                updated_at="2026-06-17T00:00:00+09:00",
            )

            self.assertEqual(result["summary"]["block_active"], 1)
            self.assertTrue(any("block" in call and "t_new" in call for call in calls))

    def test_apply_adds_source_link_comment_to_existing_task_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            card = {
                "id": "wiki/processes/tickets/dev2-1001.md",
                "column": "Decision Needed",
                "title": "DEV2-1001 결제 정책 선택",
                "work_id": "DEV2-1001",
                "ticket_id": "DEV2-1001",
                "service": "[[max]]",
                "type": "ticket",
                "path": "wiki/processes/tickets/dev2-1001.md",
                "summary": "A안을 선택할지 결정 필요",
                "suggested_roles": ["orchestrator"],
            }
            write_board(vault, [card])
            state_path = vault / sync.DEFAULT_STATE_JSON
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps(
                    {
                        "schema": "team2.hermes_kanban_sync_state.v1",
                        "cards": {
                            "wiki/processes/tickets/dev2-1001.md": {
                                "task_id": "t_existing",
                                "status": "blocked",
                            }
                        },
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            calls: list[list[str]] = []

            def runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
                calls.append(list(command))
                text = " ".join(command)
                if "boards list" in text:
                    return completed(stdout="team2 DEV2 Team2 blocked=1\n")
                if " create " in text and "--json" in command:
                    return completed(stdout='{"id":"t_existing","status":"blocked"}')
                return completed(stdout="ok\n")

            result = sync.sync_from_vault(
                vault,
                apply=True,
                command_runner=runner,
                hermes_cli="/tmp/hermes",
                updated_at="2026-06-17T00:00:00+09:00",
            )

            self.assertEqual(result["status"], "ok")
            comment_calls = [call for call in calls if "comment" in call]
            self.assertEqual(len(comment_calls), 1)
            comment_text = "\n".join(comment_calls[0])
            self.assertIn("TEAM2-SOURCE-LINK", comment_text)
            self.assertIn("vault_path: wiki/processes/tickets/dev2-1001.md", comment_text)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            item = state["cards"]["wiki/processes/tickets/dev2-1001.md"]
            self.assertEqual(item["source_link_comment_at"], "2026-06-17T00:00:00+09:00")

    def test_apply_does_not_repeat_source_link_comment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            write_board(
                vault,
                [
                    {
                        "id": "wiki/processes/tickets/dev2-1001.md",
                        "column": "Decision Needed",
                        "title": "DEV2-1001 결제 정책 선택",
                        "work_id": "DEV2-1001",
                        "ticket_id": "DEV2-1001",
                        "service": "[[max]]",
                        "type": "ticket",
                        "path": "wiki/processes/tickets/dev2-1001.md",
                        "summary": "A안을 선택할지 결정 필요",
                        "suggested_roles": ["orchestrator"],
                    }
                ],
            )
            state_path = vault / sync.DEFAULT_STATE_JSON
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps(
                    {
                        "schema": "team2.hermes_kanban_sync_state.v1",
                        "cards": {
                            "wiki/processes/tickets/dev2-1001.md": {
                                "task_id": "t_existing",
                                "status": "blocked",
                                "source_link_comment_at": "2026-06-16T00:00:00+09:00",
                            }
                        },
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            calls: list[list[str]] = []

            def runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
                calls.append(list(command))
                text = " ".join(command)
                if "boards list" in text:
                    return completed(stdout="team2 DEV2 Team2 blocked=1\n")
                if " create " in text and "--json" in command:
                    return completed(stdout='{"id":"t_existing","status":"blocked"}')
                return completed(stdout="ok\n")

            sync.sync_from_vault(
                vault,
                apply=True,
                command_runner=runner,
                hermes_cli="/tmp/hermes",
                updated_at="2026-06-17T00:00:00+09:00",
            )

            self.assertFalse(any("comment" in call for call in calls))


if __name__ == "__main__":
    unittest.main()
