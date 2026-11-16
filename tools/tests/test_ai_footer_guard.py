"""AI 푸터 가드 회귀 — 임시 디렉터리 fixture 만 쓴다. git·gh 는 실행하지 않는다."""

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("ai_footer_guard", ROOT / "tools/ai_footer_guard.py")
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)
HOOK = ROOT / ".claude/hooks/ai-footer-guard.sh"

CLAUDE_COAUTHOR = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
GENERATED = "🤖 Generated with [Claude Code](https://claude.com/claude-code)"


def bash(command, cwd=None):
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd}


class FindFooterTests(unittest.TestCase):
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


class HookTests(unittest.TestCase):
    def run_hook(self, payload):
        return subprocess.run(["bash", str(HOOK)], input=json.dumps(payload), capture_output=True,
                              text=True, cwd="/", timeout=10)

    def test_hook_denies_with_reason(self):
        r = self.run_hook(bash(f'git commit -m "x\n\n{CLAUDE_COAUTHOR}"'))
        self.assertEqual(r.returncode, 0)
        out = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("Commit messages", out["permissionDecisionReason"])

    def test_hook_silent_for_clean_non_bash_and_garbage(self):
        for raw in [json.dumps(bash('git commit -m "ok"')),
                    json.dumps({"tool_name": "Edit", "tool_input": {"new_string": CLAUDE_COAUTHOR}}),
                    "not json"]:
            with self.subTest(raw=raw[:20]):
                r = subprocess.run(["bash", str(HOOK)], input=raw, capture_output=True, text=True, timeout=10)
                self.assertEqual((r.returncode, r.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
