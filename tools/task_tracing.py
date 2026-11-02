#!/usr/bin/env python3
"""Shared task identities and a context adapter for official Langfuse hooks.

Only task/session bindings live here. Vendor plugins still convert transcripts;
both engines receive the same searchable identity tags, without merging sessions.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shlex
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path


ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z")
LEADING_TICKET = re.compile(r"^\s*(?:[/$]ad[:\-][\w-]+\s+)?\[?(DEV2-\d+)\b", re.I)
HANDOFF_ID = re.compile(r"^\s*task_id:\s*[\"']?([A-Za-z0-9][A-Za-z0-9_.-]{0,95})[\"']?\s*$", re.M)


def state_dir():
    return Path(os.environ.get("TEAM2_TASK_STATE_DIR", "~/.local/state/team2/task-tracing")).expanduser()


def session_identity(env):
    agent = env.get("TEAM2_TRACE_AGENT")
    if agent == "claude-code":
        return agent, env.get("TEAM2_TRACE_SESSION_ID") or env.get("CLAUDE_SESSION_ID", "")
    if env.get("CODEX_THREAD_ID"):
        return "codex", env["CODEX_THREAD_ID"]
    return agent or "manual", env.get("TEAM2_TRACE_SESSION_ID", "")


def _clean(value, limit=160):
    return " ".join(str(value or "").split())[:limit]


def connect(root):
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = root / "tasks.sqlite3"
    conn = sqlite3.connect(db, timeout=10)
    os.chmod(db, 0o600)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY, title TEXT NOT NULL, ticket_id TEXT,
            created_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS tasks_ticket ON tasks(ticket_id)
            WHERE ticket_id IS NOT NULL;
        CREATE TABLE IF NOT EXISTS sessions (
            agent TEXT NOT NULL, session_id TEXT NOT NULL, task_id TEXT NOT NULL,
            PRIMARY KEY(agent, session_id)
        );
        CREATE TABLE IF NOT EXISTS work_refs (
            work_key TEXT PRIMARY KEY, task_id TEXT NOT NULL
        );
    """)
    return conn


def ensure_task(root, *, agent="manual", session_id="", task_id="", ticket="", title="", work_key=""):
    """Atomically reuse a session/explicit task, or allocate an isolated identity."""
    if task_id and not ID.fullmatch(task_id):
        raise ValueError("task_id: use 1–96 letters, digits, dot, underscore or hyphen")
    if ticket and not re.fullmatch(r"DEV2-\d+", ticket):
        raise ValueError("ticket: expected DEV2-<number>")
    conn = connect(root)
    try:
        conn.execute("BEGIN IMMEDIATE")
        bound = conn.execute("SELECT task_id FROM sessions WHERE agent=? AND session_id=?",
                             (agent, session_id)).fetchone() if session_id else None
        if bound and task_id and bound["task_id"] != task_id:
            raise ValueError("This session already belongs to another task; use a new session")
        chosen = bound["task_id"] if bound else task_id
        if work_key:
            linked = conn.execute("SELECT task_id FROM work_refs WHERE work_key=?", (work_key,)).fetchone()
            if linked:
                if chosen and chosen != linked["task_id"]:
                    raise ValueError("Work reference already belongs to another task")
                chosen = linked["task_id"]
        if not chosen and ticket:
            existing = conn.execute("SELECT task_id FROM tasks WHERE ticket_id=?", (ticket,)).fetchone()
            chosen = existing["task_id"] if existing else ticket
        if not chosen:
            chosen = "TASK-" + dt.datetime.now().strftime("%Y%m%d-") + uuid.uuid4().hex[:12]
        row = conn.execute("SELECT * FROM tasks WHERE task_id=?", (chosen,)).fetchone()
        if row is None:
            conn.execute("INSERT INTO tasks VALUES(?,?,?,?)", (
                chosen, _clean(title) or chosen, ticket or (chosen if re.fullmatch(r"DEV2-\d+", chosen) else None),
                dt.datetime.now(dt.timezone.utc).isoformat()))
        else:
            if ticket and row["ticket_id"] and row["ticket_id"] != ticket:
                raise ValueError("Task already has a different ticket; use a new session")
            if title:
                conn.execute("UPDATE tasks SET title=? WHERE task_id=?", (_clean(title), chosen))
            if ticket and not row["ticket_id"]:
                conn.execute("UPDATE tasks SET ticket_id=? WHERE task_id=?", (ticket, chosen))
        if session_id:
            conn.execute("INSERT OR IGNORE INTO sessions VALUES(?,?,?)", (agent, session_id, chosen))
        if work_key:
            conn.execute("INSERT OR IGNORE INTO work_refs VALUES(?,?)", (work_key, chosen))
        result = dict(conn.execute("SELECT * FROM tasks WHERE task_id=?", (chosen,)).fetchone())
        conn.commit()
        return result
    finally:
        conn.close()


def repository(cwd):
    """Use the common git directory so linked worktrees share a repository name."""
    cwd = Path(cwd).expanduser().resolve()
    def git(*args):
        return subprocess.check_output(["git", "-C", str(cwd), *args], stderr=subprocess.DEVNULL,
                                       timeout=2, text=True).strip()
    try:
        common = Path(git("rev-parse", "--git-common-dir"))
        if not common.is_absolute():
            common = cwd / common
        common = common.resolve()
        repo = common.parent.name if common.name == ".git" else Path(git("rev-parse", "--show-toplevel")).name
        return {"repo": repo, "branch": git("branch", "--show-current"), "cwd": str(cwd)}
    except (OSError, subprocess.SubprocessError):
        return {"repo": cwd.name or "unknown", "branch": "", "cwd": str(cwd)}


def context(root, agent, payload, env):
    prompt = payload.get("prompt", "")
    match = LEADING_TICKET.match(prompt) if isinstance(prompt, str) else None
    handoff_ids = set(HANDOFF_ID.findall(prompt)) if isinstance(prompt, str) else set()
    session = payload.get("session_id") or session_identity(env)[1]
    if not session:
        raise ValueError("Hook requires session_id")
    # Only the first prompt names an automatically allocated task. Later prompts
    # belong to that session; a harness ensure command can explicitly refine title.
    conn = connect(root)
    try:
        bound = conn.execute("SELECT 1 FROM sessions WHERE agent=? AND session_id=?", (agent, session)).fetchone()
        candidate = env.get("TEAM2_TASK_ID", "") or (next(iter(handoff_ids)) if len(handoff_ids) == 1 else "")
        if not candidate and match:
            existing_ticket = conn.execute("SELECT task_id FROM tasks WHERE ticket_id=?", (match[1].upper(),)).fetchone()
            candidate = existing_ticket["task_id"] if existing_ticket else match[1].upper()
        existing_task = conn.execute("SELECT title FROM tasks WHERE task_id=?", (candidate,)).fetchone() if candidate else None
    finally:
        conn.close()
    task = ensure_task(root, agent=agent, session_id=session,
                       task_id=env.get("TEAM2_TASK_ID", "") or (next(iter(handoff_ids)) if len(handoff_ids) == 1 and not bound else ""),
                       ticket=match[1].upper() if match and not bound else "",
                       title=(env.get("TEAM2_TASK_TITLE") or _clean(prompt)) if not bound and not existing_task else "")
    return {**task, **repository(payload.get("cwd") or os.getcwd()), "agent": agent, "session_id": session}


def _tags(raw):
    if not raw:
        return []
    try:
        parsed = json.loads(raw) if raw.startswith("[") else raw.split(",")
        return [str(x) for x in parsed if isinstance(x, (str, int))] if isinstance(parsed, list) else []
    except ValueError:
        return []


def tracing_environment(ctx, env):
    result = dict(env)
    identity = [f"task_id:{ctx['task_id']}", f"task_name:{ctx['title']}",
                f"repo:{ctx['repo']}", f"agent:{ctx['agent']}"]
    if ctx.get("ticket_id"):
        identity.append(f"ticket_id:{ctx['ticket_id']}")
    if ctx.get("branch"):
        identity.append(f"branch:{_clean(ctx['branch'], 120)}")
    key = "LANGFUSE_CODEX_TAGS" if ctx["agent"] == "codex" else "CC_LANGFUSE_TRACE_TAGS"
    # Reserve room under the Claude plugin's 20-tag limit for identity and skills.
    tags = list(dict.fromkeys(identity + _tags(result.get(key, ""))))[:15]
    result[key] = json.dumps(tags, ensure_ascii=False)
    if ctx["agent"] == "codex":
        try:
            metadata = json.loads(result.get("LANGFUSE_CODEX_METADATA", "{}"))
        except ValueError:
            metadata = {}
        if not isinstance(metadata, dict):
            metadata = {}
        metadata.update({k: str(ctx[k]) for k in ("task_id", "title", "repo", "branch", "cwd", "agent", "session_id")})
        if ctx.get("ticket_id"):
            metadata["ticket_id"] = ctx["ticket_id"]
        result["LANGFUSE_CODEX_METADATA"] = json.dumps(metadata, ensure_ascii=False)
    return result


def export_hook(ctx, payload, env, config):
    """Execute installed, pinned vendor hooks; their package files stay intact."""
    env = tracing_environment(ctx, env)
    if ctx["agent"] == "codex":
        command = [config.get("node", "node"), config["codex_hook"]]
    else:
        # The vendor plugin normally gets these via Claude's userConfig injection.
        # Our adapter invokes its installed script, using the existing private file.
        for line in Path(config["client_env"]).read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and key in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"):
                env["CLAUDE_PLUGIN_OPTION_" + key] = value
        env["CLAUDE_PLUGIN_OPTION_LANGFUSE_USER_ID"] = "jmkim"
        command = [config.get("uv", "uv"), "run", "--quiet", "--script", config["claude_hook"]]
    # Keep a slow or unavailable tracing backend outside the agent control path.
    completed = subprocess.run(command, input=json.dumps(payload), text=True, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=25)
    return completed.returncode


def hook(agent, config_path):
    """Fail open: identity/observability must not block the user's actual work."""
    try:
        payload = json.loads(sys.stdin.buffer.read(8 * 1024 * 1024))
        event = payload.get("hook_event_name")
        if event == "SessionStart":
            # Claude's env file lets its own shell tools address the same binding.
            if agent == "claude-code" and os.environ.get("CLAUDE_ENV_FILE"):
                with open(os.environ["CLAUDE_ENV_FILE"], "a") as f:
                    f.write("\nexport TEAM2_TRACE_AGENT=claude-code\nexport TEAM2_TRACE_SESSION_ID="
                            + shlex.quote(payload["session_id"]) + "\n")
            return 0
        ctx = context(state_dir(), agent, payload, os.environ)
        if event == "SubagentStart":
            child = payload.get("agent_id")
            if not isinstance(child, str) or not child:
                raise ValueError("SubagentStart requires agent_id")
            ensure_task(state_dir(), agent=agent, session_id=child, task_id=ctx["task_id"])
        if event in ("UserPromptSubmit", "SubagentStart"):
            message = (f"Shared task_id={ctx['task_id']}; task_name={ctx['title']}; repo={ctx['repo']}. "
                       "Reuse this task_id in delegation/handoff. Refine with team2-task ensure --title; "
                       "start a new session for a different task. Policy: "
                       "/Users/jm/Documents/workspace/team2/policies/task-tracing-policy.md")
            print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": message}}, ensure_ascii=False))
        elif event in ("Stop", "SessionEnd"):
            config = json.loads(config_path.read_text())
            code = export_hook(ctx, payload, os.environ, config)
            if code:
                raise RuntimeError(f"vendor hook exit {code}")
    except Exception as exc:
        # Deliberately log only the error class, never prompt, arguments or keys.
        try:
            root = state_dir()
            root.mkdir(parents=True, exist_ok=True, mode=0o700)
            with (root / "hook-errors.log").open("a") as f:
                f.write(f"{dt.datetime.now(dt.timezone.utc).isoformat()} {agent} {type(exc).__name__}\n")
        except OSError:
            pass
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    ensure = sub.add_parser("ensure", help="Allocate/reuse task_id; automatically bind the current agent session")
    ensure.add_argument("--task-id", default="")
    ensure.add_argument("--ticket", default="")
    ensure.add_argument("--title", default="")
    ensure.add_argument("--agent", default="")
    ensure.add_argument("--session", default="")
    run = sub.add_parser("run", help="Launch an agent with a shared task_id")
    run.add_argument("task_id")
    run.add_argument("args", nargs=argparse.REMAINDER)
    show = sub.add_parser("show", help="Read task details without creating a task")
    show.add_argument("task_id")
    adapter = sub.add_parser("hook", help="Internal lifecycle adapter (JSON on stdin)")
    adapter.add_argument("agent", choices=("codex", "claude-code"))
    adapter.add_argument("--config", type=Path, default=Path.home() / ".langfuse-team2/task-tracing.json")
    args = parser.parse_args(argv)
    if args.command == "hook":
        return hook(args.agent, args.config)
    try:
        if args.command == "ensure":
            agent, session = session_identity(os.environ)
            row = ensure_task(state_dir(), agent=args.agent or agent, session_id=args.session or session,
                              task_id=args.task_id or os.environ.get("TEAM2_TASK_ID", ""),
                              ticket=args.ticket.upper(), title=args.title)
            print(json.dumps(row, ensure_ascii=False, indent=2))
        elif args.command == "show":
            conn = connect(state_dir())
            try:
                row = conn.execute("SELECT * FROM tasks WHERE task_id=?", (args.task_id,)).fetchone()
                if not row:
                    raise ValueError("Unknown task_id")
                print(json.dumps(dict(row), ensure_ascii=False, indent=2))
            finally:
                conn.close()
        elif args.command == "run":
            command = args.args[1:] if args.args[:1] == ["--"] else args.args
            if not command:
                raise ValueError("Expected command after task_id --")
            row = ensure_task(state_dir(), task_id=args.task_id)
            env = dict(os.environ, TEAM2_TASK_ID=row["task_id"], TEAM2_TASK_TITLE=row["title"])
            # This variable identifies the launched engine; SessionStart supplies
            # its fresh session id. Do not inherit the parent's session binding.
            env.pop("TEAM2_TRACE_SESSION_ID", None)
            engine = Path(command[0]).name
            if engine in ("codex", "claude"):
                env["TEAM2_TRACE_AGENT"] = "codex" if engine == "codex" else "claude-code"
            os.execvpe(command[0], command, env)
        return 0
    except (ValueError, sqlite3.IntegrityError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
