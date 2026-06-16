from __future__ import annotations

import importlib.util
import subprocess
import unittest
from pathlib import Path
from typing import Sequence


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "team2_agent.py"
spec = importlib.util.spec_from_file_location("team2_agent", MODULE_PATH)
agent = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(agent)


def completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class Team2AgentTests(unittest.TestCase):
    def test_cycle_builds_knowledge_cycle_apply_command(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")
        parsed = agent.parse_args(["cycle"])

        command = agent.command_for(parsed, config)

        self.assertEqual(command[1:], ["/repo/tools/run_team2_knowledge_cycle.py", "--harness", "/repo", "--vault", "/vault", "--apply"])

    def test_cockpit_builds_generate_command(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")
        parsed = agent.parse_args(["cockpit"])

        command = agent.command_for(parsed, config)

        self.assertEqual(command[1:], ["/repo/tools/generate_decision_cockpit.py", "--vault", "/vault", "--apply"])

    def test_board_builds_hermes_stats_command(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")
        parsed = agent.parse_args(["board"])

        command = agent.command_for(parsed, config)

        self.assertEqual(command, ["/hermes", "kanban", "--board", "team2", "stats"])

    def test_brief_queues_action_with_default_instruction_and_hermes_comment(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")
        parsed = agent.parse_args(["brief", "t_123"])

        command = agent.command_for(parsed, config)

        self.assertIn("/repo/tools/queue_agent_board_action.py", command)
        self.assertIn("--task-id", command)
        self.assertIn("t_123", command)
        self.assertIn("--action", command)
        self.assertIn("brief", command)
        self.assertIn("결정 브리프 만들어줘", command)
        self.assertIn("--comment-hermes", command)

    def test_delegate_embeds_role_in_instruction(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")
        parsed = agent.parse_args(["delegate", "t_123", "planner", "추천안 정리"])

        command = agent.command_for(parsed, config)

        self.assertIn("delegate", command)
        self.assertIn("planner에게 위임: 추천안 정리", command)

    def test_decide_queues_decision_instruction(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")
        parsed = agent.parse_args(["decide", "t_123", "A안으로 결정"])

        command = agent.command_for(parsed, config)

        self.assertIn("decide", command)
        self.assertIn("A안으로 결정", command)

    def test_run_invokes_runner_and_returns_exit_code(self) -> None:
        seen: list[list[str]] = []

        def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            seen.append(list(command))
            return completed(returncode=7)

        code = agent.run(["board"], config=agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2"), runner=runner)

        self.assertEqual(code, 7)
        self.assertEqual(seen[0], ["/hermes", "kanban", "--board", "team2", "stats"])


if __name__ == "__main__":
    unittest.main()
