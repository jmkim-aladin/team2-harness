#!/usr/bin/env python3
"""Small terminal control surface for DEV2 agent-board operations."""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple, Sequence


DEFAULT_HARNESS = "/Users/jm/Documents/workspace/team2"
DEFAULT_VAULT = "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
DEFAULT_HERMES_CLI = "/Users/jm/.hermes-team2/bin/cli"
DEFAULT_BOARD = "team2"
HERDR = "herdr"
ORCHESTRATION_WORKSPACE_LABEL = "team2-orchestration"
TRIAGE_WORKSPACE_LABEL = "team2-triage"
ORCHESTRATOR_AGENT_NAME = "global-orchestrator"
DEFAULT_ORCHESTRATION_WORKERS = ("orch-worker-1", "orch-worker-2")
DEFAULT_TICKET_CONCURRENCY = 4
GLOBAL_REFRESH_SAFE_STATUSES = {"done", "idle"}
DEFAULT_HERDR_ASK_TIMEOUT_MS = 600000
DEFAULT_HERDR_ASK_READ_LINES = 160
TICKET_CELL_ROLES = {
    "analyst",
    "architect",
    "data",
    "designer",
    "developer",
    "planner",
    "qa",
    "reviewer",
}

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


class ExecutionStep(NamedTuple):
    command: list[str]
    cwd: Path


class HerdrWorkspace(NamedTuple):
    workspace_id: str
    pane_count: int
    label: str = ""
    active_tab_id: str = ""
    root_pane_id: str = ""


class HerdrPane(NamedTuple):
    pane_id: str
    label: str
    agent: str


class HerdrTab(NamedTuple):
    tab_id: str
    label: str
    workspace_id: str
    root_pane_id: str = ""


class HerdrAgentInfo(NamedTuple):
    pane_id: str
    status: str
    workspace_id: str = ""


class HerdrCreatedWorkspace(NamedTuple):
    workspace_id: str
    root_pane_id: str
    active_tab_id: str = ""


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

    herdr = sub.add_parser("herdr", help="Operate the local herdr workspace")
    herdr_sub = herdr.add_subparsers(dest="herdr_command", required=True)
    herdr_sub.add_parser("doctor", help="Check herdr server, integrations, and workspace state")
    herdr_sub.add_parser("install-hooks", help="Install herdr hooks for Codex and Claude Code")
    refresh_global_parser = herdr_sub.add_parser("refresh-global", help="Restart global-orchestrator when it is idle/done")
    refresh_global_parser.add_argument("--force", action="store_true", help="Restart even when global-orchestrator is working")
    open_parser = herdr_sub.add_parser("open", help="Open and attach a team2 herdr workspace")
    open_parser.add_argument("--no-attach", action="store_true", help="Prepare/focus workspace without attaching the herdr UI")
    worker_parser = herdr_sub.add_parser("worker", help="Start an additional herdr worker in the orchestration workspace")
    worker_parser.add_argument("name")
    worker_parser.add_argument("instruction", nargs="*")
    ask_parser = herdr_sub.add_parser("ask", help="Send a structured work packet to an agent, wait, and read the result")
    ask_parser.add_argument("target")
    ask_parser.add_argument("--task-id", default="")
    ask_parser.add_argument("--expect", default="result")
    ask_parser.add_argument("--timeout-ms", type=int, default=DEFAULT_HERDR_ASK_TIMEOUT_MS)
    ask_parser.add_argument("--read-lines", type=int, default=DEFAULT_HERDR_ASK_READ_LINES)
    ask_parser.add_argument("instruction", nargs="+")
    tickets_parser = herdr_sub.add_parser("tickets", help="Start one ticket-lead cell per ticket")
    tickets_parser.add_argument("--service", default="triage")
    tickets_parser.add_argument("--concurrency", type=int, default=DEFAULT_TICKET_CONCURRENCY)
    tickets_parser.add_argument("ticket_ids", nargs="+")
    work_parser = herdr_sub.add_parser("work", help="Start a service-scoped work-lead cell for non-ticket work")
    work_parser.add_argument("--service", default="triage")
    work_parser.add_argument("work_id")
    work_parser.add_argument("instruction", nargs="*")
    role_parser = herdr_sub.add_parser("role", help="Start a role agent inside a ticket cell")
    role_parser.add_argument("--service", default="triage")
    role_parser.add_argument("ticket_id")
    role_parser.add_argument("role", choices=sorted(TICKET_CELL_ROLES))
    role_parser.add_argument("instruction", nargs="*")
    herdr_sub.add_parser("sync", help="Run the team2 cycle, refresh cockpit, and notify herdr")
    notify = herdr_sub.add_parser("notify", help="Show a herdr notification")
    notify.add_argument("body")

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


def herdr_notify_command(body: str, *, sound: str) -> list[str]:
    return [HERDR, "notification", "show", "team2-agent", "--body", body, "--sound", sound]


def board_shell_command(config: Config) -> str:
    team2_agent = config.harness / "bin" / "team2-agent"
    return f"{team2_agent} board; {team2_agent} cockpit; exec zsh"


def orchestrator_prompt(config: Config) -> str:
    team2_agent = config.harness / "bin" / "team2-agent"
    return (
        "너는 개발 2팀 로컬 orchestrator이며 inbox/router다. 사용자는 자연어로만 지시한다. "
        "너는 team2-agent, Hermes Board, desktop cockpit, wiki, GBrain을 사용해 짧게 상태를 확인하고 "
        "사용자에게는 결정이 필요한 사항만 묻는다. 오래 걸리는 작업은 직접 수행하지 않는다. "
        "board/cockpit은 상시 패널이 아니라 네가 필요할 때 조회하는 내부 상태 도구다. "
        "팀 서비스 기준의 강제 구조는 서비스 space -> ticket/work tab -> worker pane이다. "
        "티켓/서비스 작업은 직접 처리하지 않는다. DEV2 티켓을 받으면 "
        f"`{team2_agent} herdr tickets --service {{service|triage}} --concurrency N DEV2-1234 ...`를 실행해 "
        "서비스 space와 티켓별 ticket tab을 만들고 ticket-lead에게 넘긴다. DEV2 티켓이 아닌 서비스 작업은 "
        f"`{team2_agent} herdr work --service {{service|triage}} {{work-id}} \"작업 설명\"`으로 work tab을 만든다. "
        "서비스가 불명확하면 triage를 쓴다. 분석/개발/정리처럼 서비스 소속이 아닌 오래 걸리는 일은 "
        "worker를 필요할 때만 동적으로 띄운다. "
        f"새 worker가 필요하면 `{team2_agent} herdr worker orch-worker-1 \"작업 설명\"`로 생성해 결과를 받고 자동으로 닫는다. "
        f"이미 떠 있는 idle worker가 있으면 `{team2_agent} herdr ask orch-worker-N --expect result \"작업 설명\"`로 작업 패킷을 보낸다. "
        "동시에 여러 비서비스 작업이 필요하면 orch-worker-2, orch-worker-3처럼 이름을 늘려 추가 worker를 띄운다. "
        "사용자에게는 넘긴 내용과 다음 결정 질문만 짧게 말한 뒤 다시 대기한다. "
        f"하네스 경로는 {config.harness} 이고, 먼저 `{team2_agent} board`와 `{team2_agent} cockpit`으로 상태를 확인한다. "
        "Decision Needed를 최우선으로 A/B/보류/추가조사 선택지와 근거로 정리한다. "
        "사용자 확인 없이 YouTrack/KB/git commit/push/PR/DB/prod 변경을 하지 않는다."
    )


def worker_prompt(config: Config, instruction: str = "") -> str:
    team2_agent = config.harness / "bin" / "team2-agent"
    prompt = (
        f"너는 개발 2팀 worker다. global-orchestrator가 `{team2_agent} herdr ask orch-worker-N ...` 또는 "
        f"`{team2_agent} herdr worker orch-worker-N \"...\"`로 넘긴 단일 작업만 처리한다. "
        "팀 서비스 기준의 강제 구조는 서비스 space -> ticket/work tab -> worker pane이다. "
        "티켓/서비스 작업은 직접 처리하지 않는다. DEV2 티켓을 받으면 "
        f"`{team2_agent} herdr tickets --service {{service|triage}} --concurrency 1 DEV2-1234`로 서비스 space와 ticket tab을 만들고 넘긴다. "
        "DEV2 티켓이 아닌 서비스 작업은 "
        f"`{team2_agent} herdr work --service {{service|triage}} {{work-id}} \"작업 설명\"`으로 work tab을 만든다. "
        "서비스가 불명확하면 triage를 쓴다. "
        f"하네스 경로는 {config.harness} 이고, 작업 전 관련 vault note와 하네스 정책을 확인한다. "
        "사용자 또는 orchestrator의 명시 지시 전에는 YouTrack/KB/git commit/push/PR/DB/prod 변경을 하지 않는다. "
        "대기 상태로 시작하고, 작업을 받으면 완료/막힘/결정 필요 상태와 근거, 검증 결과를 짧게 남긴다."
    )
    if instruction:
        prompt += f" 초기 위임 작업: {instruction}"
    return prompt


def ticket_cell_name(ticket_id: str) -> str:
    return f"ticket-{ticket_id}"


def work_cell_name(work_id: str) -> str:
    return f"work-{work_id}"


def role_agent_name(ticket_id: str, role: str) -> str:
    return f"{ticket_cell_name(ticket_id)}-{role}"


def service_workspace_label(service: str) -> str:
    normalized = service.strip()
    if not normalized or normalized.lower() in {"auto", "triage", "unknown"}:
        return TRIAGE_WORKSPACE_LABEL
    return normalized


def service_workspace_cwd(service: str, config: Config) -> Path:
    label = service_workspace_label(service)
    if label == TRIAGE_WORKSPACE_LABEL:
        return config.harness
    candidate = config.harness.parent / label
    return candidate.resolve() if candidate.exists() else config.harness


def ticket_tab_label(ticket_id: str) -> str:
    return ticket_id


def herdr_ask_packet(config: Config, *, task_id: str = "", expect: str = "result", instruction: str = "") -> str:
    team2_agent = config.harness / "bin" / "team2-agent"
    return "\n".join(
        [
            "[TEAM2_WORK_PACKET]",
            f"task_id: {task_id or 'none'}",
            f"expect: {expect or 'result'}",
            f"instruction: {instruction}",
            "routing_contract:",
            "- 팀 서비스 기준 강제 구조는 서비스 space -> ticket/work tab -> worker pane이다.",
            f"- DEV2 티켓 작업이면 `{team2_agent} herdr tickets --service {{service|triage}} --concurrency 1 DEV2-1234`로 재라우팅한다.",
            f"- DEV2 티켓이 아닌 서비스 작업이면 `{team2_agent} herdr work --service {{service|triage}} {{work-id}} \"작업 설명\"`으로 재라우팅한다.",
            "- 서비스가 불명확하면 triage를 사용한다.",
            "- orchestration worker pane에서 서비스 작업을 장시간 직접 처리하지 않는다.",
            "response_contract:",
            "- RESULT_PACKET status=done|blocked|decision_needed",
            "- summary: 한두 문장",
            "- evidence: 파일/위키/명령 근거",
            "- next: 다음 액션 또는 사용자 결정 질문",
        ]
    )


def ticket_lead_prompt(config: Config, ticket_id: str, *, service: str = "triage") -> str:
    team2_agent = config.harness / "bin" / "team2-agent"
    service_label = service_workspace_label(service)
    return (
        f"너는 {ticket_id} ticket-lead다. Global orchestrator가 {service_label} space의 이 티켓 tab을 맡겼다. "
        "/ad:work-prep 기준으로 YouTrack을 읽기 전용 조회하고, 서비스 카탈로그/하네스 정책/관련 vault note를 확인한다. "
        "작업 유형을 판단해서 analyst, planner, architect, developer, reviewer, qa, designer, data 중 필요한 role agent만 생성한다. "
        f"role agent는 `{team2_agent} herdr role --service {service} {ticket_id} analyst \"요구사항과 코드 진입점 분석\"`처럼 띄운다. "
        "각 role agent의 결과를 티켓별 위키 note에 모으고, Decision Needed/Approval Needed/Blocked만 Global orchestrator에게 짧게 반환한다. "
        "사용자 확인 없이 YouTrack/KB/git commit/push/PR/DB/prod 변경을 하지 않는다."
    )


def work_lead_prompt(config: Config, work_id: str, *, service: str = "triage", instruction: str = "") -> str:
    team2_agent = config.harness / "bin" / "team2-agent"
    service_label = service_workspace_label(service)
    prompt = (
        f"너는 {work_id} work-lead다. Global orchestrator 또는 worker가 {service_label} space의 이 work tab을 맡겼다. "
        "팀 서비스 기준 강제 구조는 서비스 space -> ticket/work tab -> worker pane이다. "
        "서비스 카탈로그/하네스 정책/관련 vault note를 확인하고, 필요한 role agent만 생성한다. "
        f"role agent는 `{team2_agent} herdr role --service {service} {work_id} developer \"구현 후보와 검증 방법 정리\"`처럼 띄운다. "
        "각 role agent의 결과를 작업별 위키 note에 모으고, Decision Needed/Approval Needed/Blocked만 Global orchestrator에게 짧게 반환한다. "
        "사용자 확인 없이 YouTrack/KB/git commit/push/PR/DB/prod 변경을 하지 않는다."
    )
    if instruction:
        prompt += f" 초기 작업: {instruction}"
    return prompt


def role_agent_prompt(config: Config, ticket_id: str, role: str, instruction: str = "", *, service: str = "triage") -> str:
    role_hint = {
        "analyst": "요구사항, 도메인, 코드 진입점, 영향 범위를 분석한다.",
        "planner": "작업 분할, 순서, 리스크, 산출물 기준을 정리한다.",
        "architect": "구조 변경, 경계, 장기 유지보수 리스크를 검토한다.",
        "developer": "구현 후보, 수정 파일, 검증 방법을 정리하고 지시받은 개발을 수행한다.",
        "reviewer": "회귀, 보안, 테스트 누락, 코드 품질 리스크를 검토한다.",
        "qa": "재현 조건, 수용 기준, 테스트 케이스, 확인 절차를 정리한다.",
        "designer": "UI/UX 영향, 화면 흐름, 문구, 접근성 관점을 검토한다.",
        "data": "데이터 조회/추출/정합성 관점을 검토하되 DB 변경은 하지 않는다.",
    }.get(role, "맡은 역할 관점에서 티켓을 분석한다.")
    prompt = (
        f"너는 {service_workspace_label(service)} space, {ticket_id} tab의 {role} role agent다. {role_hint} "
        f"하네스 경로는 {config.harness} 이고, ticket-lead에게 보고할 근거 중심 결과만 만든다. "
        "다른 티켓 컨텍스트와 섞지 말고, 필요한 경우 관련 vault note와 하네스 정책을 확인한다. "
        "사용자 또는 ticket-lead의 명시 지시 전에는 YouTrack/KB/git commit/push/PR/DB/prod 변경을 하지 않는다."
    )
    if instruction:
        prompt += f" 위임 작업: {instruction}"
    return prompt


def ai_argv(engine: str, prompt: str, config: Config, *, cwd: Path | None = None) -> list[str]:
    return ["zsh", "-ic", ai_command_text(engine, prompt, config, cwd=cwd)]


def ai_command_text(engine: str, prompt: str, config: Config, *, cwd: Path | None = None) -> str:
    run_cwd = cwd or config.harness
    if engine == "codex":
        argv = [engine, "--sandbox", "danger-full-access", "--ask-for-approval", "never", prompt]
    elif engine == "claude":
        argv = [engine, "--dangerously-skip-permissions", prompt]
    else:
        argv = [engine, prompt]
    return f"cd {shlex.quote(str(run_cwd))}; {shlex.join(argv)}"


def ai_shell_command(engine: str, prompt: str, config: Config, *, cwd: Path | None = None) -> str:
    return shlex.join(ai_argv(engine, prompt, config, cwd=cwd))


def herdr_workspaces(output: str) -> list[HerdrWorkspace]:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return []
    workspaces = payload.get("result", {}).get("workspaces", [])
    parsed = []
    for workspace in workspaces:
        workspace_id = workspace.get("workspace_id")
        if not workspace_id:
            continue
        parsed.append(
            HerdrWorkspace(
                str(workspace_id),
                int(workspace.get("pane_count") or 0),
                str(workspace.get("label") or ""),
                str(workspace.get("active_tab_id") or ""),
            )
        )
    return parsed


def workspace_by_label(output: str, label: str, aliases: Sequence[str] = ()) -> HerdrWorkspace | None:
    labels = [label, *aliases]
    workspaces = herdr_workspaces(output)
    for candidate in labels:
        for workspace in workspaces:
            if workspace.label.lower() == candidate.lower():
                return workspace
    return None


def team2_workspace(output: str) -> HerdrWorkspace | None:
    return workspace_by_label(output, ORCHESTRATION_WORKSPACE_LABEL)


def team2_workspace_id(output: str) -> str | None:
    workspace = team2_workspace(output)
    return workspace.workspace_id if workspace else None


def herdr_panes(output: str) -> list[HerdrPane]:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return []
    panes = payload.get("result", {}).get("panes", [])
    parsed = []
    for pane in panes:
        pane_id = pane.get("pane_id")
        if not pane_id:
            continue
        parsed.append(HerdrPane(str(pane_id), str(pane.get("label") or ""), str(pane.get("agent") or "")))
    return parsed


def herdr_tabs(output: str) -> list[HerdrTab]:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return []
    tabs = payload.get("result", {}).get("tabs", [])
    parsed = []
    for tab in tabs:
        tab_id = tab.get("tab_id")
        if not tab_id:
            continue
        parsed.append(HerdrTab(str(tab_id), str(tab.get("label") or ""), str(tab.get("workspace_id") or "")))
    return parsed


def tab_by_label(output: str, label: str) -> HerdrTab | None:
    for tab in herdr_tabs(output):
        if tab.label == label:
            return tab
    return None


def herdr_created_tab(output: str) -> HerdrTab | None:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return None
    tab = payload.get("result", {}).get("tab", {})
    tab_id = tab.get("tab_id")
    if not tab_id:
        return None
    return HerdrTab(str(tab_id), str(tab.get("label") or ""), str(tab.get("workspace_id") or ""))


def herdr_created_workspace(output: str) -> HerdrCreatedWorkspace | None:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return None
    result = payload.get("result", {})
    workspace = result.get("workspace", {})
    root_pane = result.get("root_pane", {})
    workspace_id = workspace.get("workspace_id")
    root_pane_id = root_pane.get("pane_id")
    if not workspace_id or not root_pane_id:
        return None
    active_tab_id = workspace.get("active_tab_id") or root_pane.get("tab_id") or ""
    return HerdrCreatedWorkspace(str(workspace_id), str(root_pane_id), str(active_tab_id))


def herdr_agent_info(output: str) -> HerdrAgentInfo | None:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return None
    agent = payload.get("result", {}).get("agent", {})
    pane_id = agent.get("pane_id")
    if not pane_id:
        return None
    return HerdrAgentInfo(
        str(pane_id),
        str(agent.get("agent_status") or "").lower(),
        str(agent.get("workspace_id") or ""),
    )


def start_orchestrator_command(
    config: Config,
    *,
    workspace_id: str | None = None,
    engine: str = "codex",
    split: str = "right",
    focus: bool | None = None,
) -> list[str]:
    command = [
        HERDR,
        "agent",
        "start",
        ORCHESTRATOR_AGENT_NAME,
        "--cwd",
        str(config.harness),
    ]
    if workspace_id:
        command.extend(["--workspace", workspace_id])
    command.extend(["--split", split])
    if focus is not None:
        command.append("--focus" if focus else "--no-focus")
    command.extend(["--", *ai_argv(engine, orchestrator_prompt(config), config)])
    return command


def start_worker_command(
    config: Config,
    *,
    workspace_id: str | None = None,
    engine: str = "codex",
    name: str = DEFAULT_ORCHESTRATION_WORKERS[0],
    instruction: str = "",
    split: str = "down",
    focus: bool | None = None,
) -> list[str]:
    command = [
        HERDR,
        "agent",
        "start",
        name,
        "--cwd",
        str(config.harness),
    ]
    if workspace_id:
        command.extend(["--workspace", workspace_id])
    command.extend(["--split", split])
    if focus is not None:
        command.append("--focus" if focus else "--no-focus")
    command.extend(["--", *ai_argv(engine, worker_prompt(config, instruction), config)])
    return command


def start_ticket_lead_command(
    config: Config,
    *,
    workspace_id: str | None = None,
    tab_id: str | None = None,
    ticket_id: str,
    service: str = "triage",
    engine: str = "codex",
    cwd: Path | None = None,
) -> list[str]:
    agent_cwd = cwd or config.harness
    command = [
        HERDR,
        "agent",
        "start",
        ticket_cell_name(ticket_id),
        "--cwd",
        str(agent_cwd),
    ]
    if tab_id:
        command.extend(["--tab", tab_id])
    elif workspace_id:
        command.extend(["--workspace", workspace_id])
    command.extend(["--split", "down", "--", *ai_argv(engine, ticket_lead_prompt(config, ticket_id, service=service), config, cwd=agent_cwd)])
    return command


def start_work_lead_command(
    config: Config,
    *,
    workspace_id: str | None = None,
    tab_id: str | None = None,
    work_id: str,
    service: str = "triage",
    instruction: str = "",
    engine: str = "codex",
    cwd: Path | None = None,
) -> list[str]:
    agent_cwd = cwd or config.harness
    command = [
        HERDR,
        "agent",
        "start",
        work_cell_name(work_id),
        "--cwd",
        str(agent_cwd),
    ]
    if tab_id:
        command.extend(["--tab", tab_id])
    elif workspace_id:
        command.extend(["--workspace", workspace_id])
    command.extend(["--split", "down", "--", *ai_argv(engine, work_lead_prompt(config, work_id, service=service, instruction=instruction), config, cwd=agent_cwd)])
    return command


def start_role_agent_command(
    config: Config,
    *,
    workspace_id: str | None = None,
    tab_id: str | None = None,
    ticket_id: str,
    role: str,
    instruction: str = "",
    service: str = "triage",
    engine: str = "codex",
    cwd: Path | None = None,
) -> list[str]:
    agent_cwd = cwd or config.harness
    command = [
        HERDR,
        "agent",
        "start",
        role_agent_name(ticket_id, role),
        "--cwd",
        str(agent_cwd),
    ]
    if tab_id:
        command.extend(["--tab", tab_id])
    elif workspace_id:
        command.extend(["--workspace", workspace_id])
    command.extend(["--split", "down", "--", *ai_argv(engine, role_agent_prompt(config, ticket_id, role, instruction, service=service), config, cwd=agent_cwd)])
    return command


def start_ticket_lead_steps(config: Config, tab: HerdrTab, ticket_id: str, *, service: str, cwd: Path) -> list[ExecutionStep]:
    if tab.root_pane_id:
        return [
            ExecutionStep([HERDR, "pane", "rename", tab.root_pane_id, ticket_cell_name(ticket_id)], config.harness),
            ExecutionStep(
                [HERDR, "pane", "run", tab.root_pane_id, ai_shell_command("codex", ticket_lead_prompt(config, ticket_id, service=service), config, cwd=cwd)],
                config.harness,
            ),
        ]
    return [ExecutionStep(start_ticket_lead_command(config, tab_id=tab.tab_id, ticket_id=ticket_id, service=service, cwd=cwd), config.harness)]


def start_work_lead_steps(config: Config, tab: HerdrTab, work_id: str, *, service: str, instruction: str, cwd: Path) -> list[ExecutionStep]:
    if tab.root_pane_id:
        return [
            ExecutionStep([HERDR, "pane", "rename", tab.root_pane_id, work_cell_name(work_id)], config.harness),
            ExecutionStep(
                [HERDR, "pane", "run", tab.root_pane_id, ai_shell_command("codex", work_lead_prompt(config, work_id, service=service, instruction=instruction), config, cwd=cwd)],
                config.harness,
            ),
        ]
    return [ExecutionStep(start_work_lead_command(config, tab_id=tab.tab_id, work_id=work_id, service=service, instruction=instruction, cwd=cwd), config.harness)]


def start_role_agent_steps(config: Config, tab: HerdrTab, ticket_id: str, role: str, *, service: str, instruction: str, cwd: Path) -> list[ExecutionStep]:
    if tab.root_pane_id:
        return [
            ExecutionStep([HERDR, "pane", "rename", tab.root_pane_id, role_agent_name(ticket_id, role)], config.harness),
            ExecutionStep(
                [HERDR, "pane", "run", tab.root_pane_id, ai_shell_command("codex", role_agent_prompt(config, ticket_id, role, instruction, service=service), config, cwd=cwd)],
                config.harness,
            ),
        ]
    return [
        ExecutionStep(
            start_role_agent_command(
                config,
                tab_id=tab.tab_id,
                ticket_id=ticket_id,
                role=role,
                instruction=instruction,
                service=service,
                cwd=cwd,
            ),
            config.harness,
        )
    ]


def start_board_command(config: Config, *, workspace_id: str | None = None) -> list[str]:
    command = [
        HERDR,
        "agent",
        "start",
        "board",
        "--cwd",
        str(config.harness),
    ]
    if workspace_id:
        command.extend(["--workspace", workspace_id])
    command.extend(["--split", "down", "--", "zsh", "-lc", board_shell_command(config)])
    return command


def herdr_steps_for(args: argparse.Namespace, config: Config) -> list[ExecutionStep]:
    if args.herdr_command == "doctor":
        commands = [
            [HERDR, "status"],
            [HERDR, "integration", "status"],
            [HERDR, "workspace", "list"],
        ]
    elif args.herdr_command == "install-hooks":
        commands = [
            [HERDR, "integration", "install", "codex"],
            [HERDR, "integration", "install", "claude"],
            [HERDR, "integration", "status"],
        ]
    elif args.herdr_command == "open":
        commands = [
            [HERDR, "workspace", "create", "--cwd", str(config.harness), "--label", ORCHESTRATION_WORKSPACE_LABEL, "--focus"],
            start_orchestrator_command(config),
        ]
    elif args.herdr_command == "sync":
        commands = [
            command_for(parse_args(["cycle"]), config),
            command_for(parse_args(["cockpit"]), config),
            herdr_notify_command("Hermes board and desktop cockpit synced", sound="done"),
        ]
    elif args.herdr_command == "notify":
        commands = [herdr_notify_command(args.body, sound="request")]
    else:
        raise ValueError(f"unsupported herdr command: {args.herdr_command}")
    return [ExecutionStep(command=command, cwd=config.harness) for command in commands]


def steps_for(args: argparse.Namespace, config: Config) -> list[ExecutionStep]:
    if args.command == "herdr":
        return herdr_steps_for(args, config)
    return [ExecutionStep(command=command_for(args, config), cwd=config.harness)]


def run_steps(steps: Sequence[ExecutionStep], execute) -> int:
    for step in steps:
        proc = execute(step.command, step.cwd)
        if proc.returncode != 0:
            return int(proc.returncode)
    return 0


def herdr_attach_step(config: Config) -> ExecutionStep | None:
    if os.environ.get("HERDR_ENV") or os.environ.get("HERDR_PANE_ID"):
        return None
    return ExecutionStep([HERDR, "session", "attach", "default"], config.harness)


def existing_workspace_setup_steps(workspace: HerdrWorkspace, panes: list[HerdrPane], config: Config) -> list[ExecutionStep]:
    steps = [ExecutionStep([HERDR, "workspace", "focus", workspace.workspace_id], config.harness)]
    labels = {pane.label for pane in panes}

    if ORCHESTRATOR_AGENT_NAME not in labels:
        legacy_orchestrator = next((pane for pane in panes if pane.label == "orchestrator"), None)
        if legacy_orchestrator:
            rename_command = "agent" if legacy_orchestrator.agent in {"codex", "claude"} else "pane"
            steps.append(ExecutionStep([HERDR, rename_command, "rename", legacy_orchestrator.pane_id, ORCHESTRATOR_AGENT_NAME], config.harness))
        else:
            shell_pane = next((pane for pane in panes if not pane.agent and not pane.label), None)
            if shell_pane:
                steps.append(ExecutionStep(start_orchestrator_command(config, workspace_id=workspace.workspace_id, focus=True), config.harness))
                steps.append(ExecutionStep([HERDR, "pane", "close", shell_pane.pane_id], config.harness))
            else:
                steps.append(ExecutionStep(start_orchestrator_command(config, workspace_id=workspace.workspace_id), config.harness))

    steps.append(ExecutionStep(herdr_notify_command("Focused existing team2 herdr workspace", sound="done"), config.harness))
    return steps


def new_workspace_setup_steps(created: HerdrCreatedWorkspace, config: Config) -> list[ExecutionStep]:
    return [
        ExecutionStep(start_orchestrator_command(config, workspace_id=created.workspace_id, focus=True), config.harness),
        ExecutionStep([HERDR, "pane", "close", created.root_pane_id], config.harness),
        ExecutionStep(herdr_notify_command("Opened team2 orchestrator workspace", sound="done"), config.harness),
    ]


def ensure_workspace(label: str, config: Config, execute, *, cwd: Path | None = None, known_output: str | None = None) -> HerdrWorkspace | None:
    workspace_cwd = cwd or config.harness
    workspace = workspace_by_label(known_output or "", label) if known_output is not None else None
    if workspace:
        proc = execute([HERDR, "workspace", "focus", workspace.workspace_id], config.harness)
        if proc.returncode != 0:
            return None
        return workspace
    if known_output is None:
        list_proc = execute([HERDR, "workspace", "list"], config.harness)
        if list_proc.returncode != 0:
            return None
        workspace = workspace_by_label(list_proc.stdout or "", label)
        if workspace:
            proc = execute([HERDR, "workspace", "focus", workspace.workspace_id], config.harness)
            if proc.returncode != 0:
                return None
            return workspace
    create_proc = execute(
        [HERDR, "workspace", "create", "--cwd", str(workspace_cwd), "--label", label, "--focus"],
        config.harness,
    )
    if create_proc.returncode != 0:
        return None
    created = herdr_created_workspace(create_proc.stdout or "")
    if not created:
        return None
    return HerdrWorkspace(created.workspace_id, 0, label, created.active_tab_id, created.root_pane_id)


def ensure_ticket_tab(workspace: HerdrWorkspace, ticket_id: str, config: Config, execute, *, cwd: Path | None = None) -> HerdrTab | None:
    tab_cwd = cwd or config.harness
    label = ticket_tab_label(ticket_id)
    list_proc = execute([HERDR, "tab", "list", "--workspace", workspace.workspace_id], config.harness)
    if list_proc.returncode != 0:
        return None
    existing = tab_by_label(list_proc.stdout or "", label)
    if existing:
        return existing
    if workspace.root_pane_id and workspace.active_tab_id:
        rename_proc = execute([HERDR, "tab", "rename", workspace.active_tab_id, label], config.harness)
        if rename_proc.returncode != 0:
            return None
        return HerdrTab(workspace.active_tab_id, label, workspace.workspace_id, workspace.root_pane_id)
    create_proc = execute(
        [HERDR, "tab", "create", "--workspace", workspace.workspace_id, "--cwd", str(tab_cwd), "--label", label, "--focus"],
        config.harness,
    )
    if create_proc.returncode != 0:
        return None
    return herdr_created_tab(create_proc.stdout or "")


def run_herdr_worker(args: argparse.Namespace, config: Config, execute=None) -> int:
    should_emit = execute is None
    if execute is None:
        execute = lambda cmd, cwd: subprocess.run(list(cmd), cwd=cwd, text=True, check=False, capture_output=True)
    list_proc = execute([HERDR, "workspace", "list"], config.harness)
    if list_proc.returncode != 0:
        return int(list_proc.returncode)
    workspace = team2_workspace(list_proc.stdout or "")
    if not workspace:
        return 2
    instruction = instruction_text(args.instruction, "")
    start_proc = execute(start_worker_command(config, workspace_id=workspace.workspace_id, name=args.name, instruction=instruction), config.harness)
    if start_proc.returncode != 0 or not instruction:
        return int(start_proc.returncode)
    wait_proc = execute([HERDR, "agent", "wait", args.name, "--status", "idle", "--timeout", str(DEFAULT_HERDR_ASK_TIMEOUT_MS)], config.harness)
    if wait_proc.returncode != 0:
        return int(wait_proc.returncode)
    read_proc = execute(
        [HERDR, "agent", "read", args.name, "--source", "recent-unwrapped", "--lines", str(DEFAULT_HERDR_ASK_READ_LINES), "--format", "text"],
        config.harness,
    )
    if read_proc.returncode != 0:
        return int(read_proc.returncode)
    get_proc = execute([HERDR, "agent", "get", args.name], config.harness)
    if get_proc.returncode != 0:
        return int(get_proc.returncode)
    agent_info = herdr_agent_info(get_proc.stdout or "")
    if not agent_info:
        return 2
    close_proc = execute([HERDR, "pane", "close", agent_info.pane_id], config.harness)
    if close_proc.returncode != 0:
        return int(close_proc.returncode)
    if should_emit and read_proc.stdout:
        sys.stdout.write(read_proc.stdout)
    return 0


def run_herdr_ask(args: argparse.Namespace, config: Config, execute=None) -> int:
    should_emit = execute is None
    if execute is None:
        execute = lambda cmd, cwd: subprocess.run(list(cmd), cwd=cwd, text=True, check=False, capture_output=True)
    packet = herdr_ask_packet(
        config,
        task_id=args.task_id,
        expect=args.expect,
        instruction=instruction_text(args.instruction, ""),
    )
    send_proc = execute([HERDR, "agent", "send", args.target, packet], config.harness)
    if send_proc.returncode != 0:
        return int(send_proc.returncode)
    wait_proc = execute([HERDR, "agent", "wait", args.target, "--status", "idle", "--timeout", str(args.timeout_ms)], config.harness)
    if wait_proc.returncode != 0:
        return int(wait_proc.returncode)
    read_proc = execute(
        [HERDR, "agent", "read", args.target, "--source", "recent-unwrapped", "--lines", str(args.read_lines), "--format", "text"],
        config.harness,
    )
    if read_proc.returncode != 0:
        return int(read_proc.returncode)
    if args.target.startswith("orch-worker-"):
        get_proc = execute([HERDR, "agent", "get", args.target], config.harness)
        if get_proc.returncode != 0:
            return int(get_proc.returncode)
        agent_info = herdr_agent_info(get_proc.stdout or "")
        if not agent_info:
            return 2
        close_proc = execute([HERDR, "pane", "close", agent_info.pane_id], config.harness)
        if close_proc.returncode != 0:
            return int(close_proc.returncode)
    if should_emit and read_proc.stdout:
        sys.stdout.write(read_proc.stdout)
    return 0


def run_herdr_refresh_global(args: argparse.Namespace, config: Config, execute=None) -> int:
    if execute is None:
        execute = lambda cmd, cwd: subprocess.run(list(cmd), cwd=cwd, text=True, check=False, capture_output=True)
    list_proc = execute([HERDR, "workspace", "list"], config.harness)
    if list_proc.returncode != 0:
        return int(list_proc.returncode)
    workspace = team2_workspace(list_proc.stdout or "")
    if not workspace:
        return run_herdr_open(argparse.Namespace(no_attach=True), config, execute)

    get_proc = execute([HERDR, "agent", "get", ORCHESTRATOR_AGENT_NAME], config.harness)
    if get_proc.returncode != 0:
        return run_steps(
            [
                ExecutionStep(start_orchestrator_command(config, workspace_id=workspace.workspace_id), config.harness),
                ExecutionStep(herdr_notify_command("Refreshed global orchestrator", sound="done"), config.harness),
            ],
            execute,
        )
    agent_info = herdr_agent_info(get_proc.stdout or "")
    if not agent_info:
        return 2
    if agent_info.status not in GLOBAL_REFRESH_SAFE_STATUSES and not args.force:
        return run_steps(
            [
                ExecutionStep(
                    herdr_notify_command(f"{ORCHESTRATOR_AGENT_NAME} is {agent_info.status or 'unknown'}; refresh skipped", sound="request"),
                    config.harness,
                )
            ],
            execute,
        )
    return run_steps(
        [
            ExecutionStep([HERDR, "pane", "close", agent_info.pane_id], config.harness),
            ExecutionStep(start_orchestrator_command(config, workspace_id=workspace.workspace_id), config.harness),
            ExecutionStep(herdr_notify_command("Refreshed global orchestrator", sound="done"), config.harness),
        ],
        execute,
    )


def run_herdr_work(args: argparse.Namespace, config: Config, execute=None) -> int:
    if execute is None:
        execute = lambda cmd, cwd: subprocess.run(list(cmd), cwd=cwd, text=True, check=False, capture_output=True)
    list_proc = execute([HERDR, "workspace", "list"], config.harness)
    if list_proc.returncode != 0:
        return int(list_proc.returncode)
    service = args.service
    workspace_cwd = service_workspace_cwd(service, config)
    workspace = ensure_workspace(service_workspace_label(service), config, execute, cwd=workspace_cwd, known_output=list_proc.stdout or "")
    if not workspace:
        return 2
    tab = ensure_ticket_tab(workspace, args.work_id, config, execute, cwd=workspace_cwd)
    if not tab:
        return 2
    instruction = instruction_text(args.instruction, "")
    code = run_steps(start_work_lead_steps(config, tab, args.work_id, service=service, instruction=instruction, cwd=workspace_cwd), execute)
    if code != 0:
        return code
    return run_steps(
        [
            ExecutionStep(
                herdr_notify_command(f"Started work cell {args.work_id}", sound="done"),
                config.harness,
            )
        ],
        execute,
    )


def run_herdr_tickets(args: argparse.Namespace, config: Config, execute=None) -> int:
    if execute is None:
        execute = lambda cmd, cwd: subprocess.run(list(cmd), cwd=cwd, text=True, check=False, capture_output=True)
    if args.concurrency < 1:
        return 2
    list_proc = execute([HERDR, "workspace", "list"], config.harness)
    if list_proc.returncode != 0:
        return int(list_proc.returncode)
    service = args.service
    workspace_cwd = service_workspace_cwd(service, config)
    workspace = ensure_workspace(service_workspace_label(service), config, execute, cwd=workspace_cwd, known_output=list_proc.stdout or "")
    if not workspace:
        return 2
    ticket_ids = list(args.ticket_ids)
    active_ticket_ids = ticket_ids[: args.concurrency]
    queued_count = len(ticket_ids) - len(active_ticket_ids)
    for ticket_id in active_ticket_ids:
        tab = ensure_ticket_tab(workspace, ticket_id, config, execute, cwd=workspace_cwd)
        if not tab:
            return 2
        code = run_steps(start_ticket_lead_steps(config, tab, ticket_id, service=service, cwd=workspace_cwd), execute)
        if code != 0:
            return code
        if tab.root_pane_id:
            workspace = workspace._replace(active_tab_id="", root_pane_id="")
    return run_steps(
        [
            ExecutionStep(
                herdr_notify_command(f"Started {len(active_ticket_ids)} ticket cells; queued {queued_count}", sound="done"),
                config.harness,
            )
        ],
        execute,
    )


def run_herdr_role(args: argparse.Namespace, config: Config, execute=None) -> int:
    if execute is None:
        execute = lambda cmd, cwd: subprocess.run(list(cmd), cwd=cwd, text=True, check=False, capture_output=True)
    list_proc = execute([HERDR, "workspace", "list"], config.harness)
    if list_proc.returncode != 0:
        return int(list_proc.returncode)
    service = args.service
    workspace_cwd = service_workspace_cwd(service, config)
    workspace = ensure_workspace(service_workspace_label(service), config, execute, cwd=workspace_cwd, known_output=list_proc.stdout or "")
    if not workspace:
        return 2
    tab = ensure_ticket_tab(workspace, args.ticket_id, config, execute, cwd=workspace_cwd)
    if not tab:
        return 2
    instruction = instruction_text(args.instruction, "")
    return run_steps(
        start_role_agent_steps(config, tab, args.ticket_id, args.role, service=service, instruction=instruction, cwd=workspace_cwd),
        execute,
    )


def run_herdr_open(args: argparse.Namespace, config: Config, execute=None) -> int:
    if execute is None:
        list_proc = subprocess.run(
            [HERDR, "workspace", "list"],
            cwd=config.harness,
            text=True,
            check=False,
            capture_output=True,
        )
        execute_capture = lambda cmd, cwd: subprocess.run(list(cmd), cwd=cwd, text=True, check=False, capture_output=True)
        execute = lambda cmd, cwd: subprocess.run(list(cmd), cwd=cwd, text=True, check=False)
    else:
        list_proc = execute([HERDR, "workspace", "list"], config.harness)
        execute_capture = execute
    if list_proc.returncode != 0:
        return int(list_proc.returncode)
    workspace = team2_workspace(list_proc.stdout or "")
    if workspace:
        pane_proc = execute_capture([HERDR, "pane", "list", "--workspace", workspace.workspace_id], config.harness)
        if pane_proc.returncode != 0:
            return int(pane_proc.returncode)
        steps = existing_workspace_setup_steps(workspace, herdr_panes(pane_proc.stdout or ""), config)
    else:
        create_command = [HERDR, "workspace", "create", "--cwd", str(config.harness), "--label", ORCHESTRATION_WORKSPACE_LABEL, "--focus"]
        create_proc = execute_capture(create_command, config.harness)
        if create_proc.returncode != 0:
            return int(create_proc.returncode)
        created = herdr_created_workspace(create_proc.stdout or "")
        if not created:
            steps = [
                ExecutionStep(command, config.harness)
                for command in [
                    start_orchestrator_command(config),
                ]
            ]
        else:
            steps = new_workspace_setup_steps(created, config)
    attach_step = None if args.no_attach else herdr_attach_step(config)
    if attach_step:
        steps.append(attach_step)
    return run_steps(steps, execute)


def run(
    argv: Sequence[str],
    *,
    config: Config | None = None,
    runner=None,
) -> int:
    cfg = config or default_config()
    parsed = parse_args(argv)
    if parsed.command == "herdr" and parsed.herdr_command == "open":
        return run_herdr_open(parsed, cfg, runner)
    if parsed.command == "herdr" and parsed.herdr_command == "refresh-global":
        return run_herdr_refresh_global(parsed, cfg, runner)
    if parsed.command == "herdr" and parsed.herdr_command == "worker":
        return run_herdr_worker(parsed, cfg, runner)
    if parsed.command == "herdr" and parsed.herdr_command == "ask":
        return run_herdr_ask(parsed, cfg, runner)
    if parsed.command == "herdr" and parsed.herdr_command == "work":
        return run_herdr_work(parsed, cfg, runner)
    if parsed.command == "herdr" and parsed.herdr_command == "tickets":
        return run_herdr_tickets(parsed, cfg, runner)
    if parsed.command == "herdr" and parsed.herdr_command == "role":
        return run_herdr_role(parsed, cfg, runner)
    execute = runner or (lambda cmd, cwd: subprocess.run(list(cmd), cwd=cwd, text=True, check=False))
    return run_steps(steps_for(parsed, cfg), execute)


def main(argv: Sequence[str]) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
