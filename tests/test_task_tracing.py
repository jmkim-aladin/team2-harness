from __future__ import annotations

import concurrent.futures
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import task_tracing as tracing


class TaskTracingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = self.root / "state"

    def test_same_task_is_shared_across_agents_but_sessions_stay_distinct(self):
        a = tracing.ensure_task(self.store, agent="codex", session_id="a", ticket="DEV2-123", title="조사")
        b = tracing.ensure_task(self.store, agent="claude-code", session_id="b", task_id=a["task_id"])
        self.assertEqual(a["task_id"], b["task_id"])
        self.assertEqual(b["title"], "조사")
        self.assertEqual(tracing.ensure_task(self.store, agent="codex", session_id="a")["task_id"], a["task_id"])

    def test_ticketless_parallel_sessions_in_same_repo_get_distinct_ids(self):
        def resolve(n):
            return tracing.ensure_task(self.store, agent="codex", session_id=str(n))["task_id"]
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            ids = list(pool.map(resolve, range(16)))
        self.assertEqual(len(set(ids)), 16)
        self.assertTrue(all(x.startswith("TASK-") for x in ids))

    def test_named_work_reference_shares_generated_id_across_roles_and_isolates_services(self):
        a = tracing.ensure_task(self.store, work_key="herdr:lamp:review", title="LAMP review")
        b = tracing.ensure_task(self.store, work_key="herdr:lamp:review")
        c = tracing.ensure_task(self.store, work_key="herdr:other:review")
        self.assertTrue(a["task_id"].startswith("TASK-"))
        self.assertEqual(a["task_id"], b["task_id"])
        self.assertNotEqual(a["task_id"], c["task_id"])

    def test_subagent_start_inherits_parent_id_and_injects_context_for_both_engines(self):
        script = str(Path(tracing.__file__).resolve())
        env = {k: v for k, v in os.environ.items() if k not in ("TEAM2_TASK_ID", "TEAM2_TASK_TITLE")}
        env["TEAM2_TASK_STATE_DIR"] = str(self.store)
        for engine in ("codex", "claude-code"):
            parent = tracing.ensure_task(self.store, agent=engine, session_id="parent-" + engine, title="Shared parent")
            payload = {"session_id": "parent-" + engine, "agent_id": "child-" + engine,
                       "agent_type": "reviewer", "hook_event_name": "SubagentStart"}
            proc = subprocess.run([sys.executable, script, "hook", engine], input=json.dumps(payload),
                                  env=env, capture_output=True, text=True)
            output = json.loads(proc.stdout)["hookSpecificOutput"]
            self.assertEqual(output["hookEventName"], "SubagentStart")
            self.assertIn(parent["task_id"], output["additionalContext"])
            child = tracing.ensure_task(self.store, agent=engine, session_id="child-" + engine)
            self.assertEqual(parent["task_id"], child["task_id"])

    def test_concurrent_same_session_allocates_only_once(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            ids = list(pool.map(lambda _: tracing.ensure_task(
                self.store, agent="codex", session_id="same")["task_id"], range(16)))
        self.assertEqual(len(set(ids)), 1)

    def test_session_cannot_be_silently_reassigned_and_title_can_be_refined(self):
        a = tracing.ensure_task(self.store, agent="codex", session_id="a", title="초기 제목")
        b = tracing.ensure_task(self.store, agent="codex", session_id="a", title="정리한 제목")
        self.assertEqual(a["task_id"], b["task_id"])
        self.assertEqual(b["title"], "정리한 제목")
        with self.assertRaises(ValueError):
            tracing.ensure_task(self.store, agent="codex", session_id="a", task_id="DEV2-456")

    def test_ticket_added_later_preserves_id_and_is_reused_by_another_session(self):
        a = tracing.ensure_task(self.store, agent="codex", session_id="a")
        b = tracing.ensure_task(self.store, agent="codex", session_id="a", ticket="DEV2-88")
        c = tracing.ensure_task(self.store, agent="claude-code", session_id="b", ticket="DEV2-88")
        self.assertEqual(a["task_id"], b["task_id"])
        self.assertEqual(b["task_id"], c["task_id"])
        with self.assertRaises(ValueError):
            tracing.ensure_task(self.store, agent="codex", session_id="a", ticket="DEV2-89")

    def test_followup_prompt_does_not_rename_task_or_bind_incidental_ticket(self):
        with patch.object(tracing, "repository", return_value={"repo": "same", "branch": "main", "cwd": "/repo"}):
            a = tracing.context(self.store, "codex", {"session_id": "a", "prompt": "설정 조사"}, {})
            b = tracing.context(self.store, "codex", {"session_id": "a", "prompt": "DEV2-98은 참고만"}, {})
            c = tracing.context(self.store, "codex", {"session_id": "b", "prompt": "$ad-work-prep DEV2-99"}, {})
        self.assertEqual(a["task_id"], b["task_id"])
        self.assertEqual(b["title"], "설정 조사")
        self.assertEqual(c["task_id"], "DEV2-99")

    def test_shared_identity_tags_reach_both_engines_and_preserve_existing_tags(self):
        common = {"task_id": "TASK-shared", "title": "두 도구 비교", "repo": "max-api", "branch": "feature/DEV2-9",
                  "cwd": "/repo", "ticket_id": "DEV2-9", "session_id": "a"}
        for agent, key in (("codex", "LANGFUSE_CODEX_TAGS"), ("claude-code", "CC_LANGFUSE_TRACE_TAGS")):
            env = tracing.tracing_environment(dict(common, agent=agent), {key: '["custom"]'})
            tags = json.loads(env[key])
            self.assertIn("task_id:TASK-shared", tags)
            self.assertIn("repo:max-api", tags)
            self.assertIn("agent:" + agent, tags)
            self.assertIn("custom", tags)
            if agent == "codex":
                self.assertEqual(json.loads(env["LANGFUSE_CODEX_METADATA"])["task_id"], "TASK-shared")

    def test_explicit_handoff_id_is_reused_and_multiple_ids_are_not_guessed(self):
        a = tracing.ensure_task(self.store, title="공통 작업")
        with patch.object(tracing, "repository", return_value={"repo": "same", "branch": "main", "cwd": "/repo"}):
            b = tracing.context(self.store, "claude-code", {
                "session_id": "b", "prompt": f"task_id: {a['task_id']}\n검토해줘"}, {})
            c = tracing.context(self.store, "claude-code", {
                "session_id": "c", "prompt": "task_id: TASK-one\ntask_id: TASK-two"}, {})
        self.assertEqual(a["task_id"], b["task_id"])
        self.assertEqual(b["title"], "공통 작업")
        self.assertNotIn(c["task_id"], ("TASK-one", "TASK-two"))

    def test_repository_name_is_stable_across_worktrees(self):
        repo = self.root / "repo"
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                        "commit", "--allow-empty", "-qm", "initial"], check=True)
        worktree = self.root / "other-worktree"
        subprocess.run(["git", "-C", str(repo), "worktree", "add", "-qb", "other", str(worktree)], check=True)
        self.assertEqual(tracing.repository(repo)["repo"], tracing.repository(worktree)["repo"])

    def test_cli_run_passes_shared_id_without_shell_interpretation(self):
        env = dict(os.environ, TEAM2_TASK_STATE_DIR=str(self.store))
        script = str(Path(tracing.__file__).resolve())
        out = subprocess.check_output([sys.executable, script, "run", "DEV2-55", "--", sys.executable,
                                       "-c", "import os;print(os.environ['TEAM2_TASK_ID'])"], env=env, text=True)
        self.assertEqual(out.strip(), "DEV2-55")
        with self.assertRaises(ValueError):
            tracing.ensure_task(self.store, task_id="x;touch malicious")

    def test_broken_observability_is_fail_open_and_does_not_log_prompt(self):
        script = str(Path(tracing.__file__).resolve())
        env = dict(os.environ, TEAM2_TASK_STATE_DIR=str(self.store))
        payload = {"session_id": "a", "hook_event_name": "Stop", "prompt": "SECRET-PROMPT"}
        proc = subprocess.run([sys.executable, script, "hook", "codex", "--config", str(self.root / "missing.json")],
                              input=json.dumps(payload), env=env, text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")
        self.assertNotIn("SECRET-PROMPT", (self.store / "hook-errors.log").read_text())

    def test_claude_env_file_uses_quoted_session_id_and_adapter_is_idempotent(self):
        script = str(Path(tracing.__file__).resolve())
        envfile = self.root / "env"
        env = dict(os.environ, TEAM2_TASK_STATE_DIR=str(self.store), CLAUDE_ENV_FILE=str(envfile))
        payload = {"session_id": "a'; echo unsafe", "hook_event_name": "SessionStart"}
        proc = subprocess.run([sys.executable, script, "hook", "claude-code"], input=json.dumps(payload),
                              env=env, text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0)
        exported = subprocess.check_output(["bash", "-c", 'source "$1"; printf "%s" "$TEAM2_TRACE_SESSION_ID"',
                                            "--", str(envfile)], text=True)
        self.assertEqual(exported, payload["session_id"])


if __name__ == "__main__":
    unittest.main()
