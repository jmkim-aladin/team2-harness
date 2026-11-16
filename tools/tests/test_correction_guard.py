"""교정 가드 회귀 — 임시 디렉터리 fixture 만 쓴다. git·gh·subagent 는 실행하지 않는다."""

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("correction_guard", ROOT / "tools/correction_guard.py")
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)
HOOK = ROOT / ".claude/hooks/correction-guard.sh"
LEDGER = ROOT / "docs/correction-ledger.md"

CLAUDE_COAUTHOR = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
GENERATED = "🤖 Generated with [Claude Code](https://claude.com/claude-code)"


def bash(command, cwd=None):
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd}


def agent(subagent_type, model=None, tool="Agent"):
    tool_input = {"description": "d", "prompt": "p", "subagent_type": subagent_type}
    if model is not None:
        tool_input["model"] = model
    return {"tool_name": tool, "tool_input": tool_input}


class FooterTests(unittest.TestCase):
    def test_blocks_heredoc_commit_with_coauthor(self):
        cmd = f'git commit -m "$(cat <<\'EOF\'\n[TEAM2] 작업\n\n{CLAUDE_COAUTHOR}\nEOF\n)"'
        self.assertIn("Co-Authored-By: Claude", guard.find_footer(cmd))

    def test_blocks_pr_body_inline_and_rtk_prefixed(self):
        for cmd in [f'gh pr create --title t --body "요약\n\n{GENERATED}"',
                    f'rtk gh pr edit 3 --body "x {GENERATED}"',
                    f'git -C /repo commit -m "x" -m "{CLAUDE_COAUTHOR}"']:
            with self.subTest(cmd=cmd[:30]):
                self.assertIsNotNone(guard.find_footer(cmd))

    def test_reads_message_files_relative_to_cwd(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "msg.txt").write_text(f"[TEAM2] x\n\n{CLAUDE_COAUTHOR}\n", encoding="utf-8")
            Path(d, "body.md").write_text(f"본문\n\n{GENERATED}\n", encoding="utf-8")
            self.assertIsNotNone(guard.find_footer("git commit -F msg.txt", d))
            self.assertIsNotNone(guard.find_footer("git commit --file=msg.txt", d))
            self.assertIsNotNone(guard.find_footer(f"gh pr create --body-file {d}/body.md"))

    def test_allows_clean_messages_and_human_coauthors(self):
        for cmd in ['git commit -m "[TEAM2] 게이트 추가"',
                    'git commit -m "x" -m "Co-Authored-By: 김정민 <a@b.c>"',
                    'gh pr create --title t --body "변경 요약"',
                    "git commit -F missing-file.txt"]:
            with self.subTest(cmd=cmd):
                self.assertIsNone(guard.find_footer(cmd))

    def test_ignores_commands_without_commit_or_pr_write(self):
        for cmd in ['git log --grep "Co-Authored-By: Claude"',
                    f'rg "{GENERATED}" docs',
                    f'gh pr view 3 --json body | grep "{CLAUDE_COAUTHOR}"']:
            with self.subTest(cmd=cmd[:25]):
                self.assertIsNone(guard.find_footer(cmd))


class DelegateModelTests(unittest.TestCase):
    def test_cheap_task_agents_without_model_are_denied(self):
        for t in ["Explore", "web-fetch", "caveman:cavecrew-investigator", "caveman:cavecrew-reviewer"]:
            for tool in guard.AGENT_TOOLS:
                with self.subTest(agent=t, tool=tool):
                    self.assertEqual(guard.violation(agent(t, tool=tool)), ("delegate-model", {"agent": t}))

    def test_model_given_or_judgment_agents_pass(self):
        for payload in [agent("Explore", "haiku"), agent("web-fetch", "sonnet"),
                        agent("general-purpose"), agent("Plan"), agent("fork"), agent(""),
                        {"tool_name": "Agent", "tool_input": {"prompt": "p"}}]:
            with self.subTest(payload=payload["tool_input"].get("subagent_type")):
                self.assertIsNone(guard.violation(payload))


class HookTests(unittest.TestCase):
    def run_hook(self, raw):
        return subprocess.run(["bash", str(HOOK)], input=raw, capture_output=True, text=True, cwd="/", timeout=10)

    def test_hook_denies_each_rule_with_its_sot(self):
        for payload, sot in [(bash(f'git commit -m "x\n\n{CLAUDE_COAUTHOR}"'), "ai-usage-policy.md"),
                             (agent("Explore"), "claude-base.md")]:
            with self.subTest(sot=sot):
                r = self.run_hook(json.dumps(payload))
                self.assertEqual(r.returncode, 0)
                out = json.loads(r.stdout)["hookSpecificOutput"]
                self.assertEqual(out["permissionDecision"], "deny")
                self.assertIn(sot, out["permissionDecisionReason"])

    def test_hook_silent_for_clean_other_tools_and_garbage(self):
        for raw in [json.dumps(bash('git commit -m "ok"')), json.dumps(agent("Explore", "haiku")),
                    json.dumps({"tool_name": "Edit", "tool_input": {"new_string": CLAUDE_COAUTHOR}}), "not json"]:
            with self.subTest(raw=raw[:20]):
                self.assertEqual((lambda r: (r.returncode, r.stdout))(self.run_hook(raw)), (0, ""))


class LedgerTests(unittest.TestCase):
    def test_every_guard_rule_is_in_the_ledger(self):
        ledger = LEDGER.read_text(encoding="utf-8")
        for rule in guard.REASONS:
            with self.subTest(rule=rule):
                self.assertIn(f"`correction-guard:{rule}`", ledger)


if __name__ == "__main__":
    unittest.main()
