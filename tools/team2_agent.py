#!/usr/bin/env python3
"""Small terminal control surface for DEV2 agent-board operations."""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Callable, NamedTuple, Sequence


DEFAULT_HARNESS = "/Users/jm/Documents/workspace/team2"
DEFAULT_VAULT = "/Users/jm/Library/Mobile Documents/iCloud~md~obsidian/Documents/team2"
DEFAULT_HERMES_CLI = "/Users/jm/.hermes-team2/bin/cli"
CONTAINER_HARNESS = "/workspace/team2"
CONTAINER_VAULT = "/workspace/team2-vault"
CONTAINER_HERMES_CLI = "/opt/hermes/.venv/bin/hermes"
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
DEFAULT_AGENT_ENGINE = "codex"
AGENT_ENGINES = ("codex", "claude")
TASK_KINDS = ("auto", "ticket", "work")
DEFAULT_HERDR_PANE_SPLIT = "right"
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
    agent_engine: str = DEFAULT_AGENT_ENGINE


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
        harness=default_path("TEAM2_HARNESS_PATH", DEFAULT_HARNESS, CONTAINER_HARNESS),
        vault=default_path("LOCAL_WIKI_PATH", DEFAULT_VAULT, CONTAINER_VAULT),
        hermes_cli=default_cli("HERMES_CLI", DEFAULT_HERMES_CLI, CONTAINER_HERMES_CLI),
        board=os.environ.get("HERMES_KANBAN_BOARD", DEFAULT_BOARD),
        agent_engine=normalise_agent_engine(os.environ.get("TEAM2_HERDR_ENGINE")),
    )


def default_path(env_name: str, host_default: str, container_default: str) -> Path:
    configured = os.environ.get(env_name)
    if configured:
        return Path(configured).resolve()
    container_path = Path(container_default)
    if container_path.exists():
        return container_path.resolve()
    return Path(host_default).resolve()


def default_cli(env_name: str, host_default: str, container_default: str) -> str:
    configured = os.environ.get(env_name)
    if configured:
        return configured
    return container_default if Path(container_default).exists() else host_default


def normalise_agent_engine(engine: str | None) -> str:
    return engine if engine in AGENT_ENGINES else DEFAULT_AGENT_ENGINE


def add_engine_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--engine", choices=AGENT_ENGINES, default=None, help="AI engine for newly started herdr agents")


def config_with_engine(config: Config, args: argparse.Namespace) -> Config:
    engine = getattr(args, "engine", None)
    return config._replace(agent_engine=engine) if engine else config


def prompt_for_open_engine(config: Config, input_fn: Callable[[str], str]) -> str:
    default_engine = config.agent_engine if config.agent_engine in AGENT_ENGINES else DEFAULT_AGENT_ENGINE
    default_label = "Codex" if default_engine == "codex" else "Claude Code"
    prompt = f"herdr open engine 선택 [1] Codex / [2] Claude Code (Enter={default_label}): "
    choices = {
        "1": "codex",
        "c": "codex",
        "codex": "codex",
        "2": "claude",
        "claude": "claude",
        "claude code": "claude",
        "claude-code": "claude",
    }
    while True:
        answer = input_fn(prompt).strip().lower()
        if not answer:
            return default_engine
        engine = choices.get(answer)
        if engine:
            return engine
        sys.stderr.write("1(Codex) 또는 2(Claude Code)를 입력하세요.\n")


def config_with_open_engine_prompt(
    config: Config,
    args: argparse.Namespace,
    *,
    input_fn: Callable[[str], str] | None = None,
    interactive: bool | None = None,
) -> Config:
    if getattr(args, "engine", None):
        return config
    is_interactive = sys.stdin.isatty() if interactive is None else interactive
    if not is_interactive:
        return config
    try:
        engine = prompt_for_open_engine(config, input_fn or input)
    except EOFError:
        return config
    return config._replace(agent_engine=engine)


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
    add_engine_option(refresh_global_parser)
    open_parser = herdr_sub.add_parser("open", help="Open and attach a team2 herdr workspace")
    open_parser.add_argument("--no-attach", action="store_true", help="Prepare/focus workspace without attaching the herdr UI")
    add_engine_option(open_parser)
    worker_parser = herdr_sub.add_parser("worker", help="Start an additional herdr worker in the orchestration workspace")
    add_engine_option(worker_parser)
    worker_parser.add_argument("name")
    worker_parser.add_argument("instruction", nargs="*")
    ask_parser = herdr_sub.add_parser("ask", help="Send a structured work packet to an agent, wait, and read the result")
    ask_parser.add_argument("target")
    ask_parser.add_argument("--task-id", default="")
    ask_parser.add_argument("--expect", default="result")
    ask_parser.add_argument("--timeout-ms", type=int, default=DEFAULT_HERDR_ASK_TIMEOUT_MS)
    ask_parser.add_argument("--read-lines", type=int, default=DEFAULT_HERDR_ASK_READ_LINES)
    ask_parser.add_argument("instruction", nargs="+")
    route_parser = herdr_sub.add_parser("route", help="Route a follow-up instruction to a ticket/work lead")
    add_engine_option(route_parser)
    route_parser.add_argument("--service", default="triage")
    route_parser.add_argument("--kind", choices=TASK_KINDS, default="auto")
    route_parser.add_argument("--expect", default="result")
    route_parser.add_argument("work_ref")
    route_parser.add_argument("instruction", nargs="+")
    collect_parser = herdr_sub.add_parser("collect", help="Read recent output from a ticket/work lead without closing it")
    collect_parser.add_argument("--kind", choices=TASK_KINDS, default="auto")
    collect_parser.add_argument("--lines", type=int, default=DEFAULT_HERDR_ASK_READ_LINES)
    collect_parser.add_argument("target")
    tickets_parser = herdr_sub.add_parser("tickets", help="Start one ticket-lead cell per ticket")
    add_engine_option(tickets_parser)
    tickets_parser.add_argument("--service", default="triage")
    tickets_parser.add_argument("--concurrency", type=int, default=DEFAULT_TICKET_CONCURRENCY)
    tickets_parser.add_argument("ticket_ids", nargs="+")
    work_parser = herdr_sub.add_parser("work", help="Start a service-scoped work-lead cell for non-ticket work")
    add_engine_option(work_parser)
    work_parser.add_argument("--service", default="triage")
    work_parser.add_argument("work_id")
    work_parser.add_argument("instruction", nargs="*")
    role_parser = herdr_sub.add_parser("role", help="Start a role agent inside a ticket cell")
    add_engine_option(role_parser)
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


STRUCTURE_RULE = "팀 서비스 기준: 서비스 space -> ticket/work tab -> worker pane."
APPROVAL_BAN = "YouTrack/KB/git commit/push/PR/DB/prod 변경 금지"


def orchestrator_prompt(config: Config) -> str:
    team2_agent = config.harness / "bin" / "team2-agent"
    return (
        "너는 개발 2팀 global-orchestrator이자 inbox/router다. 사용자는 자연어로만 지시한다. "
        "team2-agent, Hermes Board, cockpit, wiki, GBrain으로 상태만 짧게 보고 Decision Needed만 묻는다. "
        "오래 걸리는 작업은 직접 수행하지 않는다. "
        f"{STRUCTURE_RULE} 티켓/서비스 작업은 직접 처리하지 않는다. "
        "DEV2 티켓은 서비스 판정에 필요한 최소 정보만 보고, 티켓 상세 정리/분석/상태 판단은 ticket-lead가 담당한다. "
        f"`{team2_agent} herdr tickets --engine {config.agent_engine} --service {{service|triage}} --concurrency N DEV2-1234 ...`를 실행해 "
        "서비스 space와 티켓별 ticket tab을 만든다. 비티켓 서비스 작업은 "
        f"`{team2_agent} herdr work --engine {config.agent_engine} --service {{service|triage}} {{work-id}} \"작업 설명\"`로 work tab을 만든다. "
        "서비스 불명확하면 triage. 비서비스/단기 병렬 작업은 필요할 때만 "
        f"`{team2_agent} herdr worker --engine {config.agent_engine} orch-worker-1 \"작업 설명\"`로 띄우고 결과 후 자동으로 닫는다. "
        f"idle worker는 `{team2_agent} herdr ask orch-worker-N --expect result \"작업 설명\"`로 쓴다. "
        f"후속 지시는 `{team2_agent} herdr route --engine {config.agent_engine} --service {{service|triage}} {{DEV2-1234|work-id}} \"후속 지시\"`, "
        f"결과 확인은 `{team2_agent} herdr collect {{DEV2-1234|work-id}}`. "
        f"먼저 `{team2_agent} board`와 `{team2_agent} cockpit` 확인. 사용자 확인 없이 {APPROVAL_BAN}."
    )


def worker_prompt(config: Config, instruction: str = "") -> str:
    team2_agent = config.harness / "bin" / "team2-agent"
    prompt = (
        f"너는 worker다. global-orchestrator가 `{team2_agent} herdr ask orch-worker-N ...` 또는 "
        f"`{team2_agent} herdr worker --engine {config.agent_engine} orch-worker-N \"...\"`로 준 단일 작업만 처리. "
        f"{STRUCTURE_RULE} 티켓/서비스 작업은 직접 처리하지 않는다. "
        f"DEV2 티켓은 `{team2_agent} herdr tickets --engine {config.agent_engine} --service {{service|triage}} --concurrency 1 DEV2-1234`로 서비스 space/ticket tab 생성. "
        f"비티켓은 `{team2_agent} herdr work --engine {config.agent_engine} --service {{service|triage}} {{work-id}} \"작업 설명\"`로 work tab 생성. "
        "서비스 불명확: triage. note/정책 확인. "
        f"명시 지시 전 {APPROVAL_BAN}. 결과: 완료/막힘/결정 필요, 근거, 검증."
    )
    if instruction:
        prompt += f" 초기 위임 작업: {instruction}"
    return prompt


def ticket_cell_name(ticket_id: str) -> str:
    return f"ticket-{ticket_id}"


def work_cell_name(work_id: str) -> str:
    return f"work-{work_id}"


def is_ticket_ref(work_ref: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][A-Z0-9]+-\d+", work_ref.strip()))


def resolve_task_kind(kind: str, work_ref: str) -> str:
    if kind in {"ticket", "work"}:
        return kind
    return "ticket" if is_ticket_ref(work_ref) else "work"


def task_lead_name(work_ref: str, *, kind: str = "auto") -> str:
    resolved = resolve_task_kind(kind, work_ref)
    if resolved == "ticket":
        if work_ref.startswith("ticket-"):
            return work_ref
        return ticket_cell_name(work_ref)
    if work_ref.startswith("work-"):
        return work_ref
    return work_cell_name(work_ref)


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
            "routing:",
            f"- {STRUCTURE_RULE}",
            f"- DEV2 티켓: `{team2_agent} herdr tickets --engine {config.agent_engine} --service {{service|triage}} --concurrency 1 DEV2-1234`.",
            f"- 비티켓 서비스: `{team2_agent} herdr work --engine {config.agent_engine} --service {{service|triage}} {{work-id}} \"작업 설명\"`.",
            "- 서비스 불명확: triage. orchestration worker pane 장시간 처리 금지.",
            "response:",
            "- RESULT_PACKET status=done|blocked|decision_needed",
            "- summary/evidence/next: 짧게",
        ]
    )


def herdr_route_packet(config: Config, *, work_ref: str, expect: str = "result", instruction: str = "") -> str:
    team2_agent = config.harness / "bin" / "team2-agent"
    return "\n".join(
        [
            "[TEAM2_ROUTE_PACKET]",
            f"work_ref: {work_ref}",
            f"expect: {expect or 'result'}",
            f"instruction: {instruction}",
            "routing:",
            "- 이미 생성된 ticket/work lead 후속 지시다.",
            "- lead는 필요한 role agent만 열고 결과를 wiki/Hermes/GBrain 근거로 모은다.",
            f"- role agent: `{team2_agent} herdr role --engine {config.agent_engine} --service {{service}} {work_ref} {{role}} \"작업\"`.",
            "response:",
            "- GLOBAL_RESULT_PACKET status=done|blocked|decision_needed|approval_needed",
            "- summary/evidence/next: global이 물어볼 결정만",
        ]
    )


def ticket_lead_prompt(config: Config, ticket_id: str, *, service: str = "triage", instruction: str = "") -> str:
    team2_agent = config.harness / "bin" / "team2-agent"
    service_label = service_workspace_label(service)
    prompt = (
        f"너는 {ticket_id} ticket-lead다. Global이 {service_label} space 티켓 tab 맡김. "
        "/ad:work-prep 기준: YouTrack 읽기전용, 카탈로그/정책/vault note 확인. "
        "필요한 role agent만 생성(analyst, planner, architect, developer, reviewer, qa, designer, data). "
        f"role agent는 `{team2_agent} herdr role --engine {config.agent_engine} --service {service} {ticket_id} analyst \"요구사항과 코드 진입점 분석\"`처럼 띄운다. "
        "TEAM2_ROUTE_PACKET은 후속 지시다. "
        "role 결과는 위키 note에 모아 GLOBAL_RESULT_PACKET으로 Decision Needed/Approval Needed/Blocked만 반환한다. "
        f"사용자 확인 없이 {APPROVAL_BAN}."
    )
    if instruction:
        prompt += f" 초기 라우팅 메시지: {instruction}"
    return prompt


def work_lead_prompt(config: Config, work_id: str, *, service: str = "triage", instruction: str = "") -> str:
    team2_agent = config.harness / "bin" / "team2-agent"
    service_label = service_workspace_label(service)
    prompt = (
        f"너는 {work_id} work-lead다. Global/worker가 {service_label} space work tab 맡김. "
        f"{STRUCTURE_RULE} 카탈로그/정책/vault note 확인 후 필요한 role agent만 생성. "
        f"role agent는 `{team2_agent} herdr role --engine {config.agent_engine} --service {service} {work_id} developer \"구현 후보와 검증 방법 정리\"`처럼 띄운다. "
        "TEAM2_ROUTE_PACKET은 후속 지시다. "
        "role 결과는 위키 note에 모아 GLOBAL_RESULT_PACKET으로 Decision Needed/Approval Needed/Blocked만 반환한다. "
        f"사용자 확인 없이 {APPROVAL_BAN}."
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
        f"하네스: {config.harness}. ticket/work lead에게 근거 중심 결과만 보고한다. "
        f"다른 컨텍스트와 섞지 말고 필요 시 vault note/정책 확인. 명시 지시 전 {APPROVAL_BAN}."
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
    engine: str | None = None,
    split: str = DEFAULT_HERDR_PANE_SPLIT,
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
    selected_engine = engine or config.agent_engine
    command.extend(["--", *ai_argv(selected_engine, orchestrator_prompt(config), config)])
    return command


def start_worker_command(
    config: Config,
    *,
    workspace_id: str | None = None,
    engine: str | None = None,
    name: str = DEFAULT_ORCHESTRATION_WORKERS[0],
    instruction: str = "",
    split: str = DEFAULT_HERDR_PANE_SPLIT,
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
    selected_engine = engine or config.agent_engine
    command.extend(["--", *ai_argv(selected_engine, worker_prompt(config, instruction), config)])
    return command


def start_ticket_lead_command(
    config: Config,
    *,
    workspace_id: str | None = None,
    tab_id: str | None = None,
    ticket_id: str,
    service: str = "triage",
    engine: str | None = None,
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
    selected_engine = engine or config.agent_engine
    command.extend(["--split", DEFAULT_HERDR_PANE_SPLIT, "--", *ai_argv(selected_engine, ticket_lead_prompt(config, ticket_id, service=service), config, cwd=agent_cwd)])
    return command


def start_work_lead_command(
    config: Config,
    *,
    workspace_id: str | None = None,
    tab_id: str | None = None,
    work_id: str,
    service: str = "triage",
    instruction: str = "",
    engine: str | None = None,
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
    selected_engine = engine or config.agent_engine
    command.extend(["--split", DEFAULT_HERDR_PANE_SPLIT, "--", *ai_argv(selected_engine, work_lead_prompt(config, work_id, service=service, instruction=instruction), config, cwd=agent_cwd)])
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
    engine: str | None = None,
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
    selected_engine = engine or config.agent_engine
    command.extend(["--split", DEFAULT_HERDR_PANE_SPLIT, "--", *ai_argv(selected_engine, role_agent_prompt(config, ticket_id, role, instruction, service=service), config, cwd=agent_cwd)])
    return command


def start_ticket_lead_steps(config: Config, tab: HerdrTab, ticket_id: str, *, service: str, cwd: Path, instruction: str = "") -> list[ExecutionStep]:
    if tab.root_pane_id:
        return [
            ExecutionStep([HERDR, "pane", "rename", tab.root_pane_id, ticket_cell_name(ticket_id)], config.harness),
            ExecutionStep(
                [
                    HERDR,
                    "pane",
                    "run",
                    tab.root_pane_id,
                    ai_shell_command(config.agent_engine, ticket_lead_prompt(config, ticket_id, service=service, instruction=instruction), config, cwd=cwd),
                ],
                config.harness,
            ),
        ]
    if instruction:
        command = [
            HERDR,
            "agent",
            "start",
            ticket_cell_name(ticket_id),
            "--cwd",
            str(cwd),
            "--tab",
            tab.tab_id,
            "--split",
            DEFAULT_HERDR_PANE_SPLIT,
            "--",
            *ai_argv(config.agent_engine, ticket_lead_prompt(config, ticket_id, service=service, instruction=instruction), config, cwd=cwd),
        ]
        return [ExecutionStep(command, config.harness)]
    return [ExecutionStep(start_ticket_lead_command(config, tab_id=tab.tab_id, ticket_id=ticket_id, service=service, cwd=cwd), config.harness)]


def start_work_lead_steps(config: Config, tab: HerdrTab, work_id: str, *, service: str, instruction: str, cwd: Path) -> list[ExecutionStep]:
    if tab.root_pane_id:
        return [
            ExecutionStep([HERDR, "pane", "rename", tab.root_pane_id, work_cell_name(work_id)], config.harness),
            ExecutionStep(
                [HERDR, "pane", "run", tab.root_pane_id, ai_shell_command(config.agent_engine, work_lead_prompt(config, work_id, service=service, instruction=instruction), config, cwd=cwd)],
                config.harness,
            ),
        ]
    return [ExecutionStep(start_work_lead_command(config, tab_id=tab.tab_id, work_id=work_id, service=service, instruction=instruction, cwd=cwd), config.harness)]


def start_role_agent_steps(config: Config, tab: HerdrTab, ticket_id: str, role: str, *, service: str, instruction: str, cwd: Path) -> list[ExecutionStep]:
    if tab.root_pane_id:
        return [
            ExecutionStep([HERDR, "pane", "rename", tab.root_pane_id, role_agent_name(ticket_id, role)], config.harness),
            ExecutionStep(
                [HERDR, "pane", "run", tab.root_pane_id, ai_shell_command(config.agent_engine, role_agent_prompt(config, ticket_id, role, instruction, service=service), config, cwd=cwd)],
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
    command.extend(["--split", DEFAULT_HERDR_PANE_SPLIT, "--", "zsh", "-lc", board_shell_command(config)])
    return command


def herdr_steps_for(args: argparse.Namespace, config: Config) -> list[ExecutionStep]:
    config = config_with_engine(config, args)
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


def run_herdr_route(args: argparse.Namespace, config: Config, execute=None) -> int:
    if execute is None:
        execute = lambda cmd, cwd: subprocess.run(list(cmd), cwd=cwd, text=True, check=False, capture_output=True)
    list_proc = execute([HERDR, "workspace", "list"], config.harness)
    if list_proc.returncode != 0:
        return int(list_proc.returncode)

    service = args.service
    work_ref = args.work_ref
    instruction = instruction_text(args.instruction, "")
    kind = resolve_task_kind(args.kind, work_ref)
    lead_name = task_lead_name(work_ref, kind=kind)
    workspace_cwd = service_workspace_cwd(service, config)
    workspace = ensure_workspace(service_workspace_label(service), config, execute, cwd=workspace_cwd, known_output=list_proc.stdout or "")
    if not workspace:
        return 2
    tab = ensure_ticket_tab(workspace, work_ref, config, execute, cwd=workspace_cwd)
    if not tab:
        return 2

    get_proc = execute([HERDR, "agent", "get", lead_name], config.harness)
    if get_proc.returncode == 0:
        packet = herdr_route_packet(config, work_ref=work_ref, expect=args.expect, instruction=instruction)
        send_proc = execute([HERDR, "agent", "send", lead_name, packet], config.harness)
        if send_proc.returncode != 0:
            return int(send_proc.returncode)
    else:
        if kind == "ticket":
            steps = start_ticket_lead_steps(config, tab, work_ref, service=service, cwd=workspace_cwd, instruction=instruction)
        else:
            steps = start_work_lead_steps(config, tab, work_ref, service=service, instruction=instruction, cwd=workspace_cwd)
        code = run_steps(steps, execute)
        if code != 0:
            return code

    return run_steps(
        [
            ExecutionStep(
                herdr_notify_command(f"Routed {work_ref} to {lead_name}", sound="done"),
                config.harness,
            )
        ],
        execute,
    )


def run_herdr_collect(args: argparse.Namespace, config: Config, execute=None) -> int:
    should_emit = execute is None
    if execute is None:
        execute = lambda cmd, cwd: subprocess.run(list(cmd), cwd=cwd, text=True, check=False, capture_output=True)
    target = args.target if args.target.startswith(("ticket-", "work-", "orch-worker-", ORCHESTRATOR_AGENT_NAME)) else task_lead_name(args.target, kind=args.kind)
    read_proc = execute(
        [HERDR, "agent", "read", target, "--source", "recent-unwrapped", "--lines", str(args.lines), "--format", "text"],
        config.harness,
    )
    if read_proc.returncode != 0:
        return int(read_proc.returncode)
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
    input_fn: Callable[[str], str] | None = None,
    interactive: bool | None = None,
) -> int:
    cfg = config or default_config()
    parsed = parse_args(argv)
    if parsed.command == "herdr":
        cfg = config_with_engine(cfg, parsed)
        if parsed.herdr_command == "open":
            cfg = config_with_open_engine_prompt(cfg, parsed, input_fn=input_fn, interactive=interactive)
    if parsed.command == "herdr" and parsed.herdr_command == "open":
        return run_herdr_open(parsed, cfg, runner)
    if parsed.command == "herdr" and parsed.herdr_command == "refresh-global":
        return run_herdr_refresh_global(parsed, cfg, runner)
    if parsed.command == "herdr" and parsed.herdr_command == "worker":
        return run_herdr_worker(parsed, cfg, runner)
    if parsed.command == "herdr" and parsed.herdr_command == "ask":
        return run_herdr_ask(parsed, cfg, runner)
    if parsed.command == "herdr" and parsed.herdr_command == "route":
        return run_herdr_route(parsed, cfg, runner)
    if parsed.command == "herdr" and parsed.herdr_command == "collect":
        return run_herdr_collect(parsed, cfg, runner)
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
