from __future__ import annotations

import importlib.util
import subprocess
import tempfile
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


def seeds_orch_worker(command: Sequence[str]) -> bool:
    if command[:3] == ["herdr", "agent", "start"] and len(command) > 3:
        return command[3].startswith("orch-worker")
    if command[:3] in (["herdr", "agent", "rename"], ["herdr", "pane", "rename"]) and len(command) > 4:
        return command[4].startswith("orch-worker")
    return False


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

    def test_herdr_open_creates_team2_workspace_and_starts_only_orchestrator(self) -> None:
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
        self.assertIn("/repo/bin/team2-agent herdr worker orch-worker-1", prompt)
        self.assertIn("Decision Needed", prompt)
        self.assertIn("사용자 확인 없이", prompt)
        self.assertIn("inbox/router", prompt)
        self.assertIn("/repo/bin/team2-agent herdr ask orch-worker-N", prompt)
        self.assertIn("필요할 때만", prompt)
        self.assertIn("자동으로 닫", prompt)
        self.assertNotIn("기존 worker", prompt)
        self.assertIn("/repo/bin/team2-agent herdr tickets --service", prompt)
        self.assertIn("서비스 space", prompt)
        self.assertIn("ticket tab", prompt)
        self.assertIn("worker pane", prompt)
        self.assertIn("팀 서비스 기준", prompt)
        self.assertIn("티켓/서비스 작업은 직접 처리하지 않는다", prompt)
        self.assertIn("오래 걸리는 작업은 직접 수행하지 않는다", prompt)
        self.assertIn("서비스 판정에 필요한 최소 정보만", prompt)
        self.assertIn("티켓 상세 정리", prompt)
        self.assertIn("ticket-lead가 담당", prompt)

    def test_worker_prompt_accepts_delegated_work_from_orchestrator(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")

        prompt = agent.worker_prompt(config)

        self.assertIn("global-orchestrator가 `/repo/bin/team2-agent herdr ask", prompt)
        self.assertIn("완료/막힘/결정 필요", prompt)
        self.assertIn("/repo/bin/team2-agent herdr tickets --service", prompt)
        self.assertIn("서비스 space", prompt)
        self.assertIn("ticket tab", prompt)
        self.assertIn("worker pane", prompt)
        self.assertIn("팀 서비스 기준", prompt)
        self.assertIn("티켓/서비스 작업은 직접 처리하지 않는다", prompt)

    def test_worker_prompt_can_include_initial_instruction(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")

        prompt = agent.worker_prompt(config, "DEV2-6509 브리프")

        self.assertIn("초기 위임 작업: DEV2-6509 브리프", prompt)

    def test_service_workspace_cwd_uses_service_repo_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            harness = workspace / "team2"
            service_repo = workspace / "max"
            harness.mkdir()
            service_repo.mkdir()
            config = agent.Config(harness=harness, vault=Path("/vault"), hermes_cli="/hermes", board="team2")

            self.assertEqual(agent.service_workspace_cwd("max", config), service_repo.resolve())
            self.assertEqual(agent.service_workspace_cwd("triage", config), harness)

    def test_herdr_ask_packet_includes_routing_contract(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")

        packet = agent.herdr_ask_packet(config, task_id="DEV2-6509", expect="decision-brief", instruction="만권당 구독취소 자동결제 판별")

        self.assertIn("[TEAM2_WORK_PACKET]", packet)
        self.assertIn("task_id: DEV2-6509", packet)
        self.assertIn("expect: decision-brief", packet)
        self.assertIn("instruction: 만권당 구독취소 자동결제 판별", packet)
        self.assertIn("/repo/bin/team2-agent herdr tickets --service", packet)
        self.assertIn("/repo/bin/team2-agent herdr work --service", packet)
        self.assertIn("서비스 space", packet)
        self.assertIn("ticket/work tab", packet)
        self.assertIn("worker pane", packet)
        self.assertIn("RESULT_PACKET", packet)

    def test_run_herdr_ask_sends_packet_waits_and_reads_result(self) -> None:
        seen: list[list[str]] = []
        config = agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")
        expected_packet = agent.herdr_ask_packet(config, task_id="DEV2-6509", expect="decision-brief", instruction="만권당 분석")
        agent_stdout = '{"result":{"agent":{"name":"orch-worker-1","pane_id":"p-worker","agent_status":"idle","workspace_id":"w2"}}}'

        def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            seen.append(list(command))
            if command == ["herdr", "agent", "read", "orch-worker-1", "--source", "recent-unwrapped", "--lines", "160", "--format", "text"]:
                return completed(stdout="RESULT_PACKET status=done")
            if command == ["herdr", "agent", "get", "orch-worker-1"]:
                return completed(stdout=agent_stdout)
            return completed()

        code = agent.run(
            ["herdr", "ask", "orch-worker-1", "--task-id", "DEV2-6509", "--expect", "decision-brief", "만권당", "분석"],
            config=config,
            runner=runner,
        )

        self.assertEqual(code, 0)
        self.assertEqual(
            seen,
            [
                ["herdr", "agent", "send", "orch-worker-1", expected_packet],
                ["herdr", "agent", "wait", "orch-worker-1", "--status", "idle", "--timeout", "600000"],
                ["herdr", "agent", "read", "orch-worker-1", "--source", "recent-unwrapped", "--lines", "160", "--format", "text"],
                ["herdr", "agent", "get", "orch-worker-1"],
                ["herdr", "pane", "close", "p-worker"],
            ],
        )

    def test_ai_argv_starts_codex_with_local_workspace_permissions(self) -> None:
        config = agent.Config(harness=Path("/repo"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")

        argv = agent.ai_argv("codex", "hello", config)

        self.assertEqual(argv[:2], ["zsh", "-ic"])
        self.assertIn("codex --sandbox danger-full-access --ask-for-approval never hello", argv[2])

    def test_ai_argv_can_run_from_service_workspace(self) -> None:
        config = agent.Config(harness=Path("/workspace/team2"), vault=Path("/vault"), hermes_cli="/hermes", board="team2")

        argv = agent.ai_argv("codex", "hello", config, cwd=Path("/workspace/max"))

        self.assertEqual(argv[:2], ["zsh", "-ic"])
        self.assertIn("cd /workspace/max;", argv[2])
        self.assertNotIn("cd /workspace/team2;", argv[2])

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

    def test_run_herdr_open_does_not_seed_workers_without_board_pane(self) -> None:
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
        self.assertEqual(
            seen,
            [
                ["herdr", "workspace", "list"],
                ["herdr", "pane", "list", "--workspace", "w2"],
                ["herdr", "workspace", "focus", "w2"],
                ["herdr", "agent", "rename", "p1", "global-orchestrator"],
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
            ],
        )
        self.assertFalse(any(command[:4] == ["herdr", "agent", "start", "board"] for command in seen))
        self.assertFalse(any(seeds_orch_worker(command) for command in seen))

    def test_run_herdr_open_leaves_legacy_worker_panes_until_needed(self) -> None:
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
        self.assertFalse(any(seeds_orch_worker(command) for command in seen))

    def test_run_herdr_open_bootstraps_new_workspace_with_single_orchestrator_pane(self) -> None:
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
                    "--focus",
                    "--",
                    *agent.ai_argv("codex", agent.orchestrator_prompt(config), config),
                ],
                ["herdr", "pane", "close", "p-root"],
                ["herdr", "notification", "show", "team2-agent", "--body", "Opened team2 orchestrator workspace", "--sound", "done"],
            ],
        )

    def test_run_herdr_worker_closes_named_worker_after_instruction_result(self) -> None:
        seen: list[list[str]] = []
        workspace_stdout = '{"result":{"workspaces":[{"workspace_id":"w2","label":"team2-orchestration","focused":true,"pane_count":3}]}}'
        agent_stdout = '{"result":{"agent":{"name":"orch-worker-3","pane_id":"p-worker","agent_status":"idle","workspace_id":"w2"}}}'
        config = agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")

        def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            seen.append(list(command))
            if command == ["herdr", "workspace", "list"]:
                return completed(stdout=workspace_stdout)
            if command == ["herdr", "agent", "get", "orch-worker-3"]:
                return completed(stdout=agent_stdout)
            if command == ["herdr", "agent", "read", "orch-worker-3", "--source", "recent-unwrapped", "--lines", "160", "--format", "text"]:
                return completed(stdout="RESULT_PACKET status=done")
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
                ["herdr", "agent", "wait", "orch-worker-3", "--status", "idle", "--timeout", "600000"],
                ["herdr", "agent", "read", "orch-worker-3", "--source", "recent-unwrapped", "--lines", "160", "--format", "text"],
                ["herdr", "agent", "get", "orch-worker-3"],
                ["herdr", "pane", "close", "p-worker"],
            ],
        )

    def test_run_herdr_worker_without_instruction_keeps_manual_worker_open(self) -> None:
        seen: list[list[str]] = []
        workspace_stdout = '{"result":{"workspaces":[{"workspace_id":"w2","label":"team2-orchestration","focused":true,"pane_count":3}]}}'
        config = agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")

        def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            seen.append(list(command))
            if command == ["herdr", "workspace", "list"]:
                return completed(stdout=workspace_stdout)
            return completed()

        code = agent.run(["herdr", "worker", "orch-worker-3"], config=config, runner=runner)

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
                    *agent.ai_argv("codex", agent.worker_prompt(config), config),
                ],
            ],
        )

    def test_run_herdr_refresh_global_restarts_done_orchestrator(self) -> None:
        seen: list[list[str]] = []
        workspace_stdout = '{"result":{"workspaces":[{"workspace_id":"w2","label":"team2-orchestration","focused":true,"pane_count":3}]}}'
        agent_stdout = '{"result":{"agent":{"name":"global-orchestrator","pane_id":"p-global","agent_status":"done","workspace_id":"w2"}}}'
        config = agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")

        def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            seen.append(list(command))
            if command == ["herdr", "workspace", "list"]:
                return completed(stdout=workspace_stdout)
            if command == ["herdr", "agent", "get", "global-orchestrator"]:
                return completed(stdout=agent_stdout)
            return completed()

        code = agent.run(["herdr", "refresh-global"], config=config, runner=runner)

        self.assertEqual(code, 0)
        self.assertEqual(
            seen,
            [
                ["herdr", "workspace", "list"],
                ["herdr", "agent", "get", "global-orchestrator"],
                ["herdr", "pane", "close", "p-global"],
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
                    *agent.ai_argv("codex", agent.orchestrator_prompt(config), config),
                ],
                ["herdr", "notification", "show", "team2-agent", "--body", "Refreshed global orchestrator", "--sound", "done"],
            ],
        )

    def test_run_herdr_refresh_global_skips_working_orchestrator_without_force(self) -> None:
        seen: list[list[str]] = []
        workspace_stdout = '{"result":{"workspaces":[{"workspace_id":"w2","label":"team2-orchestration","focused":true,"pane_count":3}]}}'
        agent_stdout = '{"result":{"agent":{"name":"global-orchestrator","pane_id":"p-global","agent_status":"working","workspace_id":"w2"}}}'
        config = agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")

        def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            seen.append(list(command))
            if command == ["herdr", "workspace", "list"]:
                return completed(stdout=workspace_stdout)
            if command == ["herdr", "agent", "get", "global-orchestrator"]:
                return completed(stdout=agent_stdout)
            return completed()

        code = agent.run(["herdr", "refresh-global"], config=config, runner=runner)

        self.assertEqual(code, 0)
        self.assertEqual(
            seen,
            [
                ["herdr", "workspace", "list"],
                ["herdr", "agent", "get", "global-orchestrator"],
                [
                    "herdr",
                    "notification",
                    "show",
                    "team2-agent",
                    "--body",
                    "global-orchestrator is working; refresh skipped",
                    "--sound",
                    "request",
                ],
            ],
        )

    def test_run_herdr_refresh_global_force_restarts_working_orchestrator(self) -> None:
        seen: list[list[str]] = []
        workspace_stdout = '{"result":{"workspaces":[{"workspace_id":"w2","label":"team2-orchestration","focused":true,"pane_count":3}]}}'
        agent_stdout = '{"result":{"agent":{"name":"global-orchestrator","pane_id":"p-global","agent_status":"working","workspace_id":"w2"}}}'
        config = agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")

        def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            seen.append(list(command))
            if command == ["herdr", "workspace", "list"]:
                return completed(stdout=workspace_stdout)
            if command == ["herdr", "agent", "get", "global-orchestrator"]:
                return completed(stdout=agent_stdout)
            return completed()

        code = agent.run(["herdr", "refresh-global", "--force"], config=config, runner=runner)

        self.assertEqual(code, 0)
        self.assertIn(["herdr", "pane", "close", "p-global"], seen)
        self.assertIn(
            [
                "herdr",
                "notification",
                "show",
                "team2-agent",
                "--body",
                "Refreshed global orchestrator",
                "--sound",
                "done",
            ],
            seen,
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

    def test_work_lead_prompt_can_spawn_role_agents_for_non_ticket_work(self) -> None:
        config = agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")

        prompt = agent.work_lead_prompt(config, "aasm-resource-url-copy", service="aasm", instruction="경로복사에도 resource URL 템플릿 적용")

        self.assertIn("work-lead", prompt)
        self.assertIn("aasm-resource-url-copy", prompt)
        self.assertIn("aasm space", prompt)
        self.assertIn("/repo/bin/team2-agent herdr role --service aasm aasm-resource-url-copy developer", prompt)
        self.assertIn("경로복사에도 resource URL 템플릿 적용", prompt)

    def test_run_herdr_tickets_reuses_root_pane_when_service_workspace_is_created(self) -> None:
        seen: list[list[str]] = []
        workspace_stdout = '{"result":{"workspaces":[]}}'
        create_stdout = (
            '{"result":{'
            '"workspace":{"workspace_id":"w-max","active_tab_id":"t-root"},'
            '"root_pane":{"pane_id":"p-root","tab_id":"t-root"}'
            '}}'
        )
        tabs_stdout = '{"result":{"tabs":[{"tab_id":"t-root","label":"","workspace_id":"w-max"}]}}'
        config = agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")

        def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            seen.append(list(command))
            if command == ["herdr", "workspace", "list"]:
                return completed(stdout=workspace_stdout)
            if command == ["herdr", "workspace", "create", "--cwd", "/repo", "--label", "max", "--focus"]:
                return completed(stdout=create_stdout)
            if command == ["herdr", "tab", "list", "--workspace", "w-max"]:
                return completed(stdout=tabs_stdout)
            return completed()

        code = agent.run(["herdr", "tickets", "--service", "max", "--concurrency", "1", "DEV2-6509"], config=config, runner=runner)

        self.assertEqual(code, 0)
        self.assertEqual(
            seen,
            [
                ["herdr", "workspace", "list"],
                ["herdr", "workspace", "create", "--cwd", "/repo", "--label", "max", "--focus"],
                ["herdr", "tab", "list", "--workspace", "w-max"],
                ["herdr", "tab", "rename", "t-root", "DEV2-6509"],
                ["herdr", "pane", "rename", "p-root", "ticket-DEV2-6509"],
                [
                    "herdr",
                    "pane",
                    "run",
                    "p-root",
                    agent.ai_shell_command("codex", agent.ticket_lead_prompt(config, "DEV2-6509", service="max"), config),
                ],
                [
                    "herdr",
                    "notification",
                    "show",
                    "team2-agent",
                    "--body",
                    "Started 1 ticket cells; queued 0",
                    "--sound",
                    "done",
                ],
            ],
        )

    def test_run_herdr_work_reuses_root_pane_when_service_workspace_is_created(self) -> None:
        seen: list[list[str]] = []
        workspace_stdout = '{"result":{"workspaces":[]}}'
        create_stdout = (
            '{"result":{'
            '"workspace":{"workspace_id":"w-aasm","active_tab_id":"t-root"},'
            '"root_pane":{"pane_id":"p-root","tab_id":"t-root"}'
            '}}'
        )
        tabs_stdout = '{"result":{"tabs":[{"tab_id":"t-root","label":"","workspace_id":"w-aasm"}]}}'
        config = agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")

        def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            seen.append(list(command))
            if command == ["herdr", "workspace", "list"]:
                return completed(stdout=workspace_stdout)
            if command == ["herdr", "workspace", "create", "--cwd", "/repo", "--label", "aasm", "--focus"]:
                return completed(stdout=create_stdout)
            if command == ["herdr", "tab", "list", "--workspace", "w-aasm"]:
                return completed(stdout=tabs_stdout)
            return completed()

        code = agent.run(
            ["herdr", "work", "--service", "aasm", "aasm-resource-url-copy", "경로복사에도", "resource", "URL", "템플릿", "적용"],
            config=config,
            runner=runner,
        )

        self.assertEqual(code, 0)
        self.assertEqual(
            seen,
            [
                ["herdr", "workspace", "list"],
                ["herdr", "workspace", "create", "--cwd", "/repo", "--label", "aasm", "--focus"],
                ["herdr", "tab", "list", "--workspace", "w-aasm"],
                ["herdr", "tab", "rename", "t-root", "aasm-resource-url-copy"],
                ["herdr", "pane", "rename", "p-root", "work-aasm-resource-url-copy"],
                [
                    "herdr",
                    "pane",
                    "run",
                    "p-root",
                    agent.ai_shell_command(
                        "codex",
                        agent.work_lead_prompt(config, "aasm-resource-url-copy", service="aasm", instruction="경로복사에도 resource URL 템플릿 적용"),
                        config,
                    ),
                ],
                [
                    "herdr",
                    "notification",
                    "show",
                    "team2-agent",
                    "--body",
                    "Started work cell aasm-resource-url-copy",
                    "--sound",
                    "done",
                ],
            ],
        )

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

    def test_run_herdr_work_starts_work_cell_in_service_tab(self) -> None:
        seen: list[list[str]] = []
        workspace_stdout = '{"result":{"workspaces":[{"workspace_id":"w-aasm","label":"aasm","focused":false,"pane_count":1}]}}'
        empty_tabs_stdout = '{"result":{"tabs":[]}}'
        config = agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")

        def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
            seen.append(list(command))
            if command == ["herdr", "workspace", "list"]:
                return completed(stdout=workspace_stdout)
            if command == ["herdr", "tab", "list", "--workspace", "w-aasm"]:
                return completed(stdout=empty_tabs_stdout)
            if command == ["herdr", "tab", "create", "--workspace", "w-aasm", "--cwd", "/repo", "--label", "aasm-resource-url-copy", "--focus"]:
                return completed(stdout='{"result":{"tab":{"tab_id":"t-work","label":"aasm-resource-url-copy","workspace_id":"w-aasm"}}}')
            return completed()

        code = agent.run(
            ["herdr", "work", "--service", "aasm", "aasm-resource-url-copy", "경로복사에도", "resource", "URL", "템플릿", "적용"],
            config=config,
            runner=runner,
        )

        self.assertEqual(code, 0)
        self.assertEqual(
            seen,
            [
                ["herdr", "workspace", "list"],
                ["herdr", "workspace", "focus", "w-aasm"],
                ["herdr", "tab", "list", "--workspace", "w-aasm"],
                ["herdr", "tab", "create", "--workspace", "w-aasm", "--cwd", "/repo", "--label", "aasm-resource-url-copy", "--focus"],
                [
                    "herdr",
                    "agent",
                    "start",
                    "work-aasm-resource-url-copy",
                    "--cwd",
                    "/repo",
                    "--tab",
                    "t-work",
                    "--split",
                    "down",
                    "--",
                    *agent.ai_argv("codex", agent.work_lead_prompt(config, "aasm-resource-url-copy", service="aasm", instruction="경로복사에도 resource URL 템플릿 적용"), config),
                ],
                [
                    "herdr",
                    "notification",
                    "show",
                    "team2-agent",
                    "--body",
                    "Started work cell aasm-resource-url-copy",
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

    def test_run_herdr_open_adds_only_orchestrator_when_existing_workspace_has_one_pane(self) -> None:
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
                "--focus",
                "--",
                *agent.ai_argv(
                    "codex",
                    agent.orchestrator_prompt(agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2")),
                    agent.Config(Path("/repo"), Path("/vault"), "/hermes", "team2"),
                ),
            ],
            seen,
        )
        self.assertIn(["herdr", "pane", "close", "p1"], seen)
        self.assertFalse(any(command[:4] == ["herdr", "agent", "start", "board"] for command in seen))
        self.assertFalse(any(seeds_orch_worker(command) for command in seen))

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
