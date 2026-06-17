from __future__ import annotations

import importlib.util
import subprocess
import unittest
from pathlib import Path
from typing import Sequence
from unittest.mock import patch


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

    def test_herdr_doctor_checks_status_integrations_and_workspaces(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")
        parsed = agent.parse_args(["herdr", "doctor"])

        steps = agent.steps_for(parsed, config)

        self.assertEqual(
            [step.command for step in steps],
            [
                ["herdr", "status"],
                ["herdr", "integration", "status"],
                ["herdr", "workspace", "list"],
            ],
        )

    def test_herdr_install_hooks_installs_codex_and_claude_integrations(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")
        parsed = agent.parse_args(["herdr", "install-hooks"])

        steps = agent.steps_for(parsed, config)

        self.assertEqual(
            [step.command for step in steps],
            [
                ["herdr", "integration", "install", "codex"],
                ["herdr", "integration", "install", "claude"],
                ["herdr", "integration", "status"],
            ],
        )

    def test_herdr_open_creates_team2_workspace_and_starts_orchestrator_worker_pool(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")
        parsed = agent.parse_args(["herdr", "open"])

        steps = agent.steps_for(parsed, config)

        self.assertEqual(
            [step.command for step in steps],
            [
                ["herdr", "workspace", "create", "--cwd", "/repo", "--label", "team2-orchestration", "--focus"],
                [
                    "herdr",
                    "agent",
                    "start",
                    "global-orchestrator",
                    "--cwd",
                    "/repo",
                    "--split",
                    "right",
                    "--",
                    *agent.ai_argv("codex", agent.orchestrator_prompt(config), config),
                ],
                [
                    "herdr",
                    "agent",
                    "start",
                    "orch-worker-1",
                    "--cwd",
                    "/repo",
                    "--split",
                    "down",
                    "--",
                    *agent.ai_argv("codex", agent.worker_prompt(config), config),
                ],
                [
                    "herdr",
                    "agent",
                    "start",
                    "orch-worker-2",
                    "--cwd",
                    "/repo",
                    "--split",
                    "down",
                    "--",
                    *agent.ai_argv("codex", agent.worker_prompt(config), config),
                ],
            ],
        )

    def test_board_shell_command_uses_absolute_team2_agent_path(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")

        self.assertEqual(
            agent.board_shell_command(config),
            "/repo/bin/team2-agent board; /repo/bin/team2-agent cockpit; exec zsh",
        )

    def test_orchestrator_prompt_tells_user_to_speak_naturally(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")

        prompt = agent.orchestrator_prompt(config)

        self.assertIn("자연어", prompt)
        self.assertIn("team2-agent board", prompt)
        self.assertIn("/repo/bin/team2-agent herdr worker orch-worker-3", prompt)
        self.assertIn("Decision Needed", prompt)
        self.assertIn("사용자 확인 없이", prompt)
        self.assertIn("inbox/router", prompt)
        self.assertIn("herdr agent send orch-worker", prompt)
        self.assertIn("오래 걸리는 작업은 직접 수행하지 않는다", prompt)

    def test_worker_prompt_accepts_delegated_work_from_orchestrator(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")

        prompt = agent.worker_prompt(config)

        self.assertIn("global-orchestrator가 `herdr agent send orch-worker", prompt)
        self.assertIn("완료/막힘/결정 필요", prompt)

    def test_worker_prompt_can_include_initial_instruction(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")

        prompt = agent.worker_prompt(config, "DEV2-6509 브리프")

        self.assertIn("초기 위임 작업: DEV2-6509 브리프", prompt)

    def test_ai_argv_starts_codex_with_local_workspace_permissions(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")

        argv = agent.ai_argv("codex", "hello", config)

        self.assertEqual(argv[:2], ["zsh", "-ic"])
        self.assertIn("codex --sandbox danger-full-access --ask-for-approval never hello", argv[2])

    def test_herdr_sync_runs_cycle_cockpit_and_notifies(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")
        parsed = agent.parse_args(["herdr", "sync"])

        steps = agent.steps_for(parsed, config)

        self.assertEqual(steps[0].command[1:], ["/repo/tools/run_team2_knowledge_cycle.py", "--harness", "/repo", "--vault", "/vault", "--apply"])
        self.assertEqual(steps[1].command[1:], ["/repo/tools/generate_decision_cockpit.py", "--vault", "/vault", "--apply"])
        self.assertEqual(
            steps[2].command,
            [
                "herdr",
                "notification",
                "show",
                "team2-agent",
                "--body",
                "Hermes board and desktop cockpit synced",
                "--sound",
                "done",
            ],
        )

    def test_herdr_notify_uses_default_title_and_body(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")
        parsed = agent.parse_args(["herdr", "notify", "결정 필요"])

        steps = agent.steps_for(parsed, config)

        self.assertEqual(
            steps[0].command,
            [
                "herdr",
                "notification",
                "show",
                "team2-agent",
                "--body",
                "결정 필요",
                "--sound",
                "request",
            ],
        )

    def test_run_herdr_open_focuses_existing_orchestration_workspace(self) -> None:
        seen: list[list[str]] = []
        workspace_stdout = (
            '{"result":{"workspaces":['
            '{"workspace_id":"w1","label":"max","focused":false,"pane_count":1},'
            '{"workspace_id":"w2","label":"team2-orchestration","focused":true,"pane_count":3},'
            '{"workspace_id":"w3","label":"team2","focused":false,"pane_count":1}'
            ']}}'
        )
        panes_stdout = (
            '{"result":{"panes":['
            '{"pane_id":"p1","label":"orchestrator","agent":"codex"},'
            '{"pane_id":"p2","label":"worker","agent":"codex"},'
            '{"pane_id":"p3","label":"board"}'
            ']}}'
        )

        def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            seen.append(list(command))
            if command == ["herdr", "workspace", "list"]:
                return completed(stdout=workspace_stdout)
            if command == ["herdr", "pane", "list", "--workspace", "w2"]:
                return completed(stdout=panes_stdout)
            return completed()

        with patch.dict(agent.os.environ, {}, clear=True):
            code = agent.run(["herdr", "open"], config=agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2"), runner=runner)

        self.assertEqual(code, 0)
        self.assertEqual(
            seen,
            [
                ["herdr", "workspace", "list"],
                ["herdr", "pane", "list", "--workspace", "w2"],
                ["herdr", "workspace", "focus", "w2"],
                ["herdr", "agent", "rename", "p1", "global-orchestrator"],
                ["herdr", "agent", "rename", "p2", "orch-worker-1"],
                [
                    "herdr",
                    "agent",
                    "start",
                    "orch-worker-2",
                    "--cwd",
                    "/repo",
                    "--workspace",
                    "w2",
                    "--split",
                    "down",
                    "--",
                    *agent.ai_argv(
                        "codex",
                        agent.worker_prompt(agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")),
                        agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2"),
                    ),
                ],
                [
                    "herdr",
                    "notification",
                    "show",
                    "team2-agent",
                    "--body",
                    "Focused existing team2 herdr workspace",
                    "--sound",
                    "done",
                ],
                ["herdr", "session", "attach", "default"],
            ],
        )

    def test_run_herdr_open_no_attach_focuses_without_attaching(self) -> None:
        seen: list[list[str]] = []
        workspace_stdout = '{"result":{"workspaces":[{"workspace_id":"w2","label":"team2-orchestration","focused":true,"pane_count":3}]}}'
        panes_stdout = '{"result":{"panes":[{"pane_id":"p1","label":"global-orchestrator","agent":"codex"},{"pane_id":"p2","label":"orch-worker-1","agent":"codex"},{"pane_id":"p3","label":"orch-worker-2","agent":"codex"}]}}'

        def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            seen.append(list(command))
            if command == ["herdr", "workspace", "list"]:
                return completed(stdout=workspace_stdout)
            if command == ["herdr", "pane", "list", "--workspace", "w2"]:
                return completed(stdout=panes_stdout)
            return completed()

        code = agent.run(["herdr", "open", "--no-attach"], config=agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2"), runner=runner)

        self.assertEqual(code, 0)
        self.assertNotIn(["herdr", "session", "attach", "default"], seen)

    def test_run_herdr_open_adds_missing_workers_without_board_pane(self) -> None:
        seen: list[list[str]] = []
        workspace_stdout = '{"result":{"workspaces":[{"workspace_id":"w2","label":"team2-orchestration","focused":true,"pane_count":2}]}}'
        panes_stdout = (
            '{"result":{"panes":['
            '{"pane_id":"p1","label":"orchestrator","agent":"codex"},'
            '{"pane_id":"p2"}'
            ']}}'
        )

        def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            seen.append(list(command))
            if command == ["herdr", "workspace", "list"]:
                return completed(stdout=workspace_stdout)
            if command == ["herdr", "pane", "list", "--workspace", "w2"]:
                return completed(stdout=panes_stdout)
            return completed()

        with patch.dict(agent.os.environ, {}, clear=True):
            code = agent.run(["herdr", "open", "--no-attach"], config=agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2"), runner=runner)

        self.assertEqual(code, 0)
        self.assertIn(
            [
                "herdr",
                "pane",
                "rename",
                "p2",
                "orch-worker-1",
            ],
            seen,
        )
        self.assertIn(
            [
                "herdr",
                "agent",
                "start",
                "orch-worker-2",
                "--cwd",
                "/repo",
                "--workspace",
                "w2",
                "--split",
                "down",
                "--",
                *agent.ai_argv(
                    "codex",
                    agent.worker_prompt(agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")),
                    agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2"),
                ),
            ],
            seen,
        )
        self.assertFalse(any(command[:4] == ["herdr", "agent", "start", "board"] for command in seen))

    def test_run_herdr_open_reuses_shell_pane_for_second_worker_when_available(self) -> None:
        seen: list[list[str]] = []
        workspace_stdout = '{"result":{"workspaces":[{"workspace_id":"w2","label":"team2-orchestration","focused":true,"pane_count":3}]}}'
        panes_stdout = (
            '{"result":{"panes":['
            '{"pane_id":"p1","label":"orchestrator","agent":"codex"},'
            '{"pane_id":"p2"},'
            '{"pane_id":"p3","label":"worker-1","agent":"codex"}'
            ']}}'
        )

        def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            seen.append(list(command))
            if command == ["herdr", "workspace", "list"]:
                return completed(stdout=workspace_stdout)
            if command == ["herdr", "pane", "list", "--workspace", "w2"]:
                return completed(stdout=panes_stdout)
            return completed()

        with patch.dict(agent.os.environ, {}, clear=True):
            code = agent.run(["herdr", "open", "--no-attach"], config=agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2"), runner=runner)

        self.assertEqual(code, 0)
        self.assertIn(["herdr", "agent", "rename", "p1", "global-orchestrator"], seen)
        self.assertIn(["herdr", "agent", "rename", "p3", "orch-worker-1"], seen)
        self.assertIn(["herdr", "pane", "rename", "p2", "orch-worker-2"], seen)
        self.assertIn(
            [
                "herdr",
                "pane",
                "run",
                "p2",
                agent.ai_shell_command("codex", agent.worker_prompt(agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")), agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")),
            ],
            seen,
        )

    def test_run_herdr_open_bootstraps_new_workspace_as_three_pane_cockpit(self) -> None:
        seen: list[list[str]] = []
        workspace_stdout = '{"result":{"workspaces":[]}}'
        create_stdout = (
            '{"result":{'
            '"workspace":{"workspace_id":"w-new"},'
            '"root_pane":{"pane_id":"p-root"}'
            '}}'
        )
        config = agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")

        def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            seen.append(list(command))
            if command == ["herdr", "workspace", "list"]:
                return completed(stdout=workspace_stdout)
            if command == ["herdr", "workspace", "create", "--cwd", "/repo", "--label", "team2-orchestration", "--focus"]:
                return completed(stdout=create_stdout)
            return completed()

        with patch.dict(agent.os.environ, {}, clear=True):
            code = agent.run(["herdr", "open", "--no-attach"], config=config, runner=runner)

        self.assertEqual(code, 0)
        self.assertEqual(
            seen,
            [
                ["herdr", "workspace", "list"],
                ["herdr", "workspace", "create", "--cwd", "/repo", "--label", "team2-orchestration", "--focus"],
                ["herdr", "pane", "rename", "p-root", "orch-worker-1"],
                ["herdr", "pane", "run", "p-root", agent.ai_shell_command("codex", agent.worker_prompt(config), config)],
                [
                    "herdr",
                    "agent",
                    "start",
                    "global-orchestrator",
                    "--cwd",
                    "/repo",
                    "--workspace",
                    "w-new",
                    "--split",
                    "right",
                    "--",
                    *agent.ai_argv("codex", agent.orchestrator_prompt(config), config),
                ],
                [
                    "herdr",
                    "agent",
                    "start",
                    "orch-worker-2",
                    "--cwd",
                    "/repo",
                    "--workspace",
                    "w-new",
                    "--split",
                    "down",
                    "--",
                    *agent.ai_argv("codex", agent.worker_prompt(config), config),
                ],
                ["herdr", "notification", "show", "team2-agent", "--body", "Opened team2 orchestrator workspace", "--sound", "done"],
            ],
        )

    def test_run_herdr_worker_starts_named_worker_in_orchestration_workspace(self) -> None:
        seen: list[list[str]] = []
        workspace_stdout = '{"result":{"workspaces":[{"workspace_id":"w2","label":"team2-orchestration","focused":true,"pane_count":3}]}}'
        config = agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")

        def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            seen.append(list(command))
            if command == ["herdr", "workspace", "list"]:
                return completed(stdout=workspace_stdout)
            return completed()

        code = agent.run(["herdr", "worker", "orch-worker-3", "DEV2-6509", "브리프"], config=config, runner=runner)

        self.assertEqual(code, 0)
        self.assertEqual(
            seen,
            [
                ["herdr", "workspace", "list"],
                [
                    "herdr",
                    "agent",
                    "start",
                    "orch-worker-3",
                    "--cwd",
                    "/repo",
                    "--workspace",
                    "w2",
                    "--split",
                    "down",
                    "--",
                    *agent.ai_argv("codex", agent.worker_prompt(config, "DEV2-6509 브리프"), config),
                ],
            ],
        )

    def test_ticket_lead_prompt_can_spawn_role_agents(self) -> None:
        config = agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")

        prompt = agent.ticket_lead_prompt(config, "DEV2-6509", service="max")

        self.assertIn("ticket-lead", prompt)
        self.assertIn("DEV2-6509", prompt)
        self.assertIn("/ad:work-prep", prompt)
        self.assertIn("/repo/bin/team2-agent herdr role --service max DEV2-6509 analyst", prompt)
        self.assertIn("필요한 role agent만", prompt)
        self.assertIn("사용자 확인 없이", prompt)

    def test_run_herdr_tickets_starts_ticket_cells_up_to_concurrency(self) -> None:
        seen: list[list[str]] = []
        workspace_stdout = '{"result":{"workspaces":[{"workspace_id":"w-max","label":"max","focused":false,"pane_count":3}]}}'
        empty_tabs_stdout = '{"result":{"tabs":[]}}'
        config = agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")

        def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            seen.append(list(command))
            if command == ["herdr", "workspace", "list"]:
                return completed(stdout=workspace_stdout)
            if command == ["herdr", "tab", "list", "--workspace", "w-max"]:
                return completed(stdout=empty_tabs_stdout)
            if command == ["herdr", "tab", "create", "--workspace", "w-max", "--cwd", "/repo", "--label", "DEV2-6509", "--focus"]:
                return completed(stdout='{"result":{"tab":{"tab_id":"t-6509"}}}')
            if command == ["herdr", "tab", "create", "--workspace", "w-max", "--cwd", "/repo", "--label", "DEV2-6510", "--focus"]:
                return completed(stdout='{"result":{"tab":{"tab_id":"t-6510"}}}')
            return completed()

        code = agent.run(["herdr", "tickets", "--service", "max", "--concurrency", "2", "DEV2-6509", "DEV2-6510", "DEV2-6511"], config=config, runner=runner)

        self.assertEqual(code, 0)
        self.assertEqual(
            seen,
            [
                ["herdr", "workspace", "list"],
                [
                    "herdr",
                    "workspace",
                    "focus",
                    "w-max",
                ],
                ["herdr", "tab", "list", "--workspace", "w-max"],
                ["herdr", "tab", "create", "--workspace", "w-max", "--cwd", "/repo", "--label", "DEV2-6509", "--focus"],
                [
                    "herdr",
                    "agent",
                    "start",
                    "ticket-DEV2-6509",
                    "--cwd",
                    "/repo",
                    "--tab",
                    "t-6509",
                    "--split",
                    "down",
                    "--",
                    *agent.ai_argv("codex", agent.ticket_lead_prompt(config, "DEV2-6509", service="max"), config),
                ],
                ["herdr", "tab", "list", "--workspace", "w-max"],
                ["herdr", "tab", "create", "--workspace", "w-max", "--cwd", "/repo", "--label", "DEV2-6510", "--focus"],
                [
                    "herdr",
                    "agent",
                    "start",
                    "ticket-DEV2-6510",
                    "--cwd",
                    "/repo",
                    "--tab",
                    "t-6510",
                    "--split",
                    "down",
                    "--",
                    *agent.ai_argv("codex", agent.ticket_lead_prompt(config, "DEV2-6510", service="max"), config),
                ],
                [
                    "herdr",
                    "notification",
                    "show",
                    "team2-agent",
                    "--body",
                    "Started 2 ticket cells; queued 1",
                    "--sound",
                    "done",
                ],
            ],
        )

    def test_run_herdr_role_starts_ticket_role_agent(self) -> None:
        seen: list[list[str]] = []
        workspace_stdout = '{"result":{"workspaces":[{"workspace_id":"w-max","label":"max","focused":false,"pane_count":3}]}}'
        tabs_stdout = '{"result":{"tabs":[{"tab_id":"t-6509","label":"DEV2-6509","workspace_id":"w-max"}]}}'
        config = agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")

        def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            seen.append(list(command))
            if command == ["herdr", "workspace", "list"]:
                return completed(stdout=workspace_stdout)
            if command == ["herdr", "tab", "list", "--workspace", "w-max"]:
                return completed(stdout=tabs_stdout)
            return completed()

        code = agent.run(["herdr", "role", "--service", "max", "DEV2-6509", "analyst", "요구사항과 코드 진입점 분석"], config=config, runner=runner)

        self.assertEqual(code, 0)
        self.assertEqual(
            seen,
            [
                ["herdr", "workspace", "list"],
                [
                    "herdr",
                    "workspace",
                    "focus",
                    "w-max",
                ],
                ["herdr", "tab", "list", "--workspace", "w-max"],
                [
                    "herdr",
                    "agent",
                    "start",
                    "ticket-DEV2-6509-analyst",
                    "--cwd",
                    "/repo",
                    "--tab",
                    "t-6509",
                    "--split",
                    "down",
                    "--",
                    *agent.ai_argv("codex", agent.role_agent_prompt(config, "DEV2-6509", "analyst", "요구사항과 코드 진입점 분석", service="max"), config),
                ],
            ],
        )

    def test_run_herdr_open_adds_orchestrator_and_worker_pool_when_existing_workspace_has_one_pane(self) -> None:
        seen: list[list[str]] = []
        workspace_stdout = '{"result":{"workspaces":[{"workspace_id":"w2","label":"team2-orchestration","focused":true,"pane_count":1}]}}'
        panes_stdout = '{"result":{"panes":[{"pane_id":"p1"}]}}'

        def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            seen.append(list(command))
            if command == ["herdr", "workspace", "list"]:
                return completed(stdout=workspace_stdout)
            if command == ["herdr", "pane", "list", "--workspace", "w2"]:
                return completed(stdout=panes_stdout)
            return completed()

        with patch.dict(agent.os.environ, {}, clear=True):
            code = agent.run(["herdr", "open", "--no-attach"], config=agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2"), runner=runner)

        self.assertEqual(code, 0)
        self.assertIn(
            [
                "herdr",
                "agent",
                "start",
                "global-orchestrator",
                "--cwd",
                "/repo",
                "--workspace",
                "w2",
                "--split",
                "right",
                "--",
                *agent.ai_argv(
                    "codex",
                    agent.orchestrator_prompt(agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")),
                    agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2"),
                ),
            ],
            seen,
        )
        self.assertIn(
            [
                "herdr",
                "pane",
                "rename",
                "p1",
                "orch-worker-1",
            ],
            seen,
        )
        self.assertIn(
            [
                "herdr",
                "agent",
                "start",
                "orch-worker-2",
                "--cwd",
                "/repo",
                "--workspace",
                "w2",
                "--split",
                "down",
                "--",
                *agent.ai_argv(
                    "codex",
                    agent.worker_prompt(agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")),
                    agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2"),
                ),
            ],
            seen,
        )
        self.assertFalse(any(command[:4] == ["herdr", "agent", "start", "board"] for command in seen))

    def test_orchestration_workspace_id_prefers_orchestration_space(self) -> None:
        workspace_stdout = (
            '{"id":"cli:workspace:list","result":{"workspaces":['
            '{"workspace_id":"w1","label":"team2","focused":false},'
            '{"workspace_id":"w2","label":"team2-orchestration","focused":false}'
            ']}}'
        )

        self.assertEqual(agent.team2_workspace_id(workspace_stdout), "w2")


if __name__ == "__main__":
    unittest.main()
