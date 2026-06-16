#!/usr/bin/env python3
"""Small terminal control surface for DEV2 agent-board operations."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple, Sequence


DEFAULT_HARNESS = "/Users/jm/Documents/workspace/team2"
DEFAULT_VAULT = "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
DEFAULT_HERMES_CLI = "/Users/jm/.hermes-team2/bin/cli"
DEFAULT_BOARD = "team2"

DEFAULT_INSTRUCTIONS = {
    "brief": "결정 브리프 만들어줘",
    "ask": "추가 근거와 답변을 정리해줘",
    "decide": "결정을 원본 위키에 기록하고 상태 해소 후보로 정리해줘",
    "approve": "승인 처리하고 다음 단계로 진행해줘",
    "revise": "이 방향으로 다시 검토해줘",
    "split": "작업을 더 작은 단위로 분할해줘",
    "snooze": "지금은 보류로 기록해줘",
    "done": "확인 완료로 정리하고 원본 위키 상태 해소 후보로 반영해줘",
}


class Config(NamedTuple):
    harness: Path
    vault: Path
    hermes_cli: str
    board: str


def default_config() -> Config:
    return Config(
        harness=Path(os.environ.get("TEAM2_HARNESS_PATH", DEFAULT_HARNESS)).resolve(),
        vault=Path(os.environ.get("LOCAL_WIKI_PATH", DEFAULT_VAULT)).resolve(),
        hermes_cli=os.environ.get("HERMES_CLI", DEFAULT_HERMES_CLI),
        board=os.environ.get("HERMES_KANBAN_BOARD", DEFAULT_BOARD),
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="team2-agent", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("board", help="Show Hermes team2 board stats")
    sub.add_parser("cockpit", help="Refresh desktop decision cockpit")
    sub.add_parser("cycle", help="Run the full team2 knowledge cycle")

    for action in ("brief", "ask", "decide", "approve", "revise", "split", "snooze", "done"):
        action_parser = sub.add_parser(action, help=f"Queue {action} action for a Hermes task")
        action_parser.add_argument("task_id")
        action_parser.add_argument("instruction", nargs="*")

    delegate = sub.add_parser("delegate", help="Delegate a Hermes task to a role")
    delegate.add_argument("task_id")
    delegate.add_argument("role")
    delegate.add_argument("instruction", nargs="*")

    return parser.parse_args(list(argv))


def python_command(config: Config, script: str, *args: str) -> list[str]:
    return [sys.executable, str(config.harness / "tools" / script), *args]


def queue_command(config: Config, task_id: str, action: str, instruction: str) -> list[str]:
    return python_command(
        config,
        "queue_agent_board_action.py",
        "--vault",
        str(config.vault),
        "--task-id",
        task_id,
        "--action",
        action,
        "--instruction",
        instruction,
        "--apply",
        "--comment-hermes",
        "--hermes-cli",
        config.hermes_cli,
        "--kanban-board",
        config.board,
    )


def instruction_text(parts: Sequence[str], default: str) -> str:
    text = " ".join(parts).strip()
    return text or default


def command_for(args: argparse.Namespace, config: Config) -> list[str]:
    if args.command == "board":
        return [config.hermes_cli, "kanban", "--board", config.board, "stats"]
    if args.command == "cockpit":
        return python_command(config, "generate_decision_cockpit.py", "--vault", str(config.vault), "--apply")
    if args.command == "cycle":
        return python_command(
            config,
            "run_team2_knowledge_cycle.py",
            "--harness",
            str(config.harness),
            "--vault",
            str(config.vault),
            "--apply",
        )
    if args.command == "delegate":
        instruction = instruction_text(args.instruction, "진행 가능한 다음 액션까지 정리해줘")
        return queue_command(config, args.task_id, "delegate", f"{args.role}에게 위임: {instruction}")
    if args.command in DEFAULT_INSTRUCTIONS:
        return queue_command(
            config,
            args.task_id,
            args.command,
            instruction_text(args.instruction, DEFAULT_INSTRUCTIONS[args.command]),
        )
    raise ValueError(f"unsupported command: {args.command}")


def run(
    argv: Sequence[str],
    *,
    config: Config | None = None,
    runner=None,
) -> int:
    cfg = config or default_config()
    parsed = parse_args(argv)
    command = command_for(parsed, cfg)
    execute = runner or (lambda cmd, cwd: subprocess.run(list(cmd), cwd=cwd, text=True, check=False))
    proc = execute(command, cfg.harness)
    return int(proc.returncode)


def main(argv: Sequence[str]) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
