"""사용자 레벨 게이트 설치 회귀 — 임시 settings.json fixture 만 쓴다. 실제 ~/.claude 는 건드리지 않는다."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gates = load("install_claude_gates", "tools/install_claude_gates.py")
HARNESS = "/opt/team 2/harness"
CAVEMAN = "if [ -z \"${HOME-}\" ]; then printf '{}\\n'; fi; caveman-hook"


def user_settings():
    """실제 사용자 settings 의 모양 — 여러 이벤트 훅, matcher 없는 그룹, env, allow 규칙."""
    return {
        "env": {"LOCAL_WIKI_PATH": "~/wiki", "TEAM2_HARNESS_PATH": "/x/team2"},
        "hooks": {
            "PreToolUse": [
                {"matcher": "Bash", "hooks": [{"type": "command", "command": "rtk hook claude"}]},
                {"matcher": "*", "hooks": [{"type": "command", "command": CAVEMAN, "timeout": 10}]},
            ],
            "PostToolUse": [{"matcher": "*", "hooks": [{"type": "command", "command": CAVEMAN, "timeout": 10}]}],
            "SessionStart": [{"matcher": "^(startup|resume)$", "hooks": [
                {"type": "command", "command": "bash '/u/.claude/hooks/herdr-agent-state.sh' session"}]},
                {"hooks": [{"type": "command", "command": CAVEMAN}]}],
        },
        "permissions": {"allow": ["Bash(gh pr view:*)"]},
        "statusLine": {"type": "command", "command": "hud"},
    }


def managed_commands(settings):
    return [h["command"] for g in settings["hooks"]["PreToolUse"] for h in g["hooks"]
            if "/.claude/hooks/" in h["command"]]


class MergeTests(unittest.TestCase):
    def test_installs_three_hooks_and_ask_rules(self):
        merged, changes = gates.merge_settings(user_settings(), HARNESS)
        groups = {g["matcher"]: g["hooks"][0]["command"] for g in merged["hooks"]["PreToolUse"][2:]}
        self.assertEqual(set(groups), {m for _, m in gates.HOOKS})
        for name, matcher in gates.HOOKS:
            self.assertEqual(shlex.split(groups[matcher]), ["bash", f"{HARNESS}/.claude/hooks/{name}.sh"])
        self.assertEqual(merged["permissions"]["ask"], ["Bash(gh pr merge:*)", "Bash(rtk gh pr merge:*)"])
        self.assertTrue(shlex.split(groups["Bash|mcp__.*"])[-1].endswith("/agent-run-guard.sh"))
        self.assertEqual(len(changes), len(gates.HOOKS) + len(gates.ASK_RULES))

    def test_converges_previous_install(self):
        """1차 설치본(파일 도구 matcher, push·PR 정적 ask)을 새 선언으로 수렴시킨다."""
        s = user_settings()
        s["hooks"]["PreToolUse"].append({"matcher": "Bash|Write|Edit|MultiEdit|NotebookEdit|mcp__.*", "hooks": [
            {"type": "command", "command": gates.hook_command(HARNESS, "agent-run-guard")}]})
        s["permissions"]["ask"] = ["Bash(npm publish:*)", "Bash(git push:*)", "Bash(gh pr create:*)",
                                   "Bash(gh pr merge:*)", "Bash(rtk git push:*)", "Bash(rtk gh pr create:*)",
                                   "Bash(rtk gh pr merge:*)"]
        merged, changes = gates.merge_settings(s, HARNESS)
        matchers = [g["matcher"] for g in merged["hooks"]["PreToolUse"] if "agent-run-guard" in str(g)]
        self.assertEqual(matchers, ["Bash|mcp__.*"])
        self.assertEqual(merged["permissions"]["ask"],
                         ["Bash(npm publish:*)", "Bash(gh pr merge:*)", "Bash(rtk gh pr merge:*)"])
        self.assertIn("PreToolUse 훅 갱신 — agent-run-guard [Bash|mcp__.*]", changes)
        self.assertEqual(sum("permissions.ask 제거" in c for c in changes), 4)
        self.assertEqual(gates.merge_settings(merged, HARNESS)[1], [])

    def test_preserves_existing_hooks_env_and_permissions(self):
        before = user_settings()
        merged, _ = gates.merge_settings(before, HARNESS)
        self.assertEqual(before, user_settings())  # 입력 불변
        self.assertEqual(merged["hooks"]["PreToolUse"][:2], before["hooks"]["PreToolUse"])
        for event in ["PostToolUse", "SessionStart"]:
            self.assertEqual(merged["hooks"][event], before["hooks"][event])
        self.assertEqual(merged["env"], before["env"])
        self.assertEqual(merged["permissions"]["allow"], before["permissions"]["allow"])
        self.assertEqual(merged["statusLine"], before["statusLine"])

    def test_idempotent(self):
        once, _ = gates.merge_settings(user_settings(), HARNESS)
        twice, changes = gates.merge_settings(once, HARNESS)
        self.assertEqual(changes, [])
        self.assertEqual(twice, once)

    def test_moved_harness_and_project_style_entries_replaced(self):
        s = user_settings()
        s["hooks"]["PreToolUse"][0]["hooks"].append(
            {"type": "command", "command": "bash /old/team2/.claude/hooks/agent-run-guard.sh"})
        s["hooks"]["PreToolUse"].append({"matcher": "Bash", "hooks": [
            {"type": "command", "command": '"$CLAUDE_PROJECT_DIR/.claude/hooks/sqlcmd-readonly.sh"'}]})
        merged, changes = gates.merge_settings(s, HARNESS)
        self.assertEqual(merged["hooks"]["PreToolUse"][0]["hooks"], [{"type": "command", "command": "rtk hook claude"}])
        self.assertEqual(len(managed_commands(merged)), 3)
        self.assertTrue(all(HARNESS in c for c in managed_commands(merged)))
        self.assertTrue(any("갱신 — agent-run-guard" in c for c in changes))
        self.assertTrue(any("갱신 — sqlcmd-readonly" in c for c in changes))

    def test_duplicates_collapsed_and_existing_ask_kept(self):
        s, _ = gates.merge_settings(user_settings(), HARNESS)
        s["hooks"]["PreToolUse"].append(copy.deepcopy(s["hooks"]["PreToolUse"][-1]))
        s["permissions"]["ask"].insert(0, "Bash(npm publish:*)")
        merged, changes = gates.merge_settings(s, HARNESS)
        self.assertEqual(len(managed_commands(merged)), 3)
        self.assertEqual(changes, ["PreToolUse 훅 중복 제거 — agent-run-guard (1건)"])
        self.assertEqual(merged["permissions"]["ask"][0], "Bash(npm publish:*)")

    def test_uninstall_restores_pre_install_settings(self):
        installed, _ = gates.merge_settings(user_settings(), HARNESS)
        installed["permissions"]["ask"].insert(0, "Bash(npm publish:*)")
        removed, changes = gates.remove_settings(installed)
        expected = user_settings()
        expected["permissions"]["ask"] = ["Bash(npm publish:*)"]
        self.assertEqual(removed, expected)
        self.assertEqual(len(changes), len(gates.HOOKS) + len(gates.ASK_RULES))
        self.assertEqual(gates.remove_settings(user_settings()), (user_settings(), []))

    def test_uninstall_drops_containers_it_emptied(self):
        installed, _ = gates.merge_settings({}, HARNESS)
        self.assertEqual(gates.remove_settings(installed)[0], {"hooks": {}, "permissions": {}})

    def test_empty_and_malformed_settings(self):
        merged, _ = gates.merge_settings({}, HARNESS)
        self.assertEqual(len(merged["hooks"]["PreToolUse"]), 3)
        for bad in [[], {"hooks": []}, {"hooks": {"PreToolUse": {}}}, {"permissions": {"ask": "x"}}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                gates.merge_settings(bad, HARNESS)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.path = self.tmp / "settings.json"

    def run_cli(self, *extra):
        return subprocess.run(["python3", str(ROOT / "tools/install_claude_gates.py"), "--settings", str(self.path),
                               "--harness", str(ROOT), *extra], text=True, capture_output=True)

    def backups(self):
        return sorted(p.name for p in self.tmp.glob("settings.json.bak-*"))

    def test_install_then_rerun_is_noop(self):
        self.path.write_text(json.dumps(user_settings()), encoding="utf-8")
        self.assertEqual(self.run_cli("--check").returncode, 1)
        self.assertEqual(self.backups(), [])  # --check 는 쓰지 않는다
        first = self.run_cli()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(len(self.backups()), 1)
        installed = self.path.read_text(encoding="utf-8")
        second = self.run_cli()
        self.assertIn("이미 설치됨", second.stdout)
        self.assertEqual(self.path.read_text(encoding="utf-8"), installed)
        self.assertEqual(len(self.backups()), 1)
        self.assertEqual(self.run_cli("--check").returncode, 0)

    def test_uninstall_cli_check_then_remove(self):
        self.path.write_text(json.dumps(user_settings()), encoding="utf-8")
        self.assertEqual(self.run_cli().returncode, 0)
        preview = self.run_cli("--uninstall", "--check")
        self.assertEqual(preview.returncode, 1)
        self.assertIn("[변경 예정]", preview.stdout)
        self.assertEqual(len(managed_commands(json.loads(self.path.read_text(encoding="utf-8")))), 3)
        result = self.run_cli("--uninstall")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8")), user_settings())
        self.assertIn("제거할 게이트 없음", self.run_cli("--uninstall").stdout)

    def test_missing_file_created_and_invalid_json_untouched(self):
        self.assertEqual(self.run_cli().returncode, 0)
        self.assertEqual(len(managed_commands(json.loads(self.path.read_text(encoding="utf-8")))), 3)
        self.path.write_text("{not json", encoding="utf-8")
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "{not json")

    def test_symlinked_settings_keeps_link(self):
        real = self.tmp / "dotfiles/settings.json"
        real.parent.mkdir()
        real.write_text("{}", encoding="utf-8")
        self.path.symlink_to(real)
        self.assertEqual(self.run_cli().returncode, 0)
        self.assertTrue(self.path.is_symlink())
        self.assertEqual(len(managed_commands(json.loads(real.read_text(encoding="utf-8")))), 3)

    def test_installed_commands_run_from_unrelated_cwd(self):
        merged, _ = gates.merge_settings({}, str(ROOT))
        commands = {g["matcher"]: g["hooks"][0]["command"] for g in merged["hooks"]["PreToolUse"]}
        sqlcmd = {"tool_name": "Bash", "tool_input": {"command": "sqlcmd -S prod.example -d WebCatalog -Q 'SELECT 1'"}}
        mcp = {"tool_name": "mcp__postgres__query", "tool_input": {}}
        merge = {"tool_name": "Bash", "tool_input": {"command": "gh pr merge 1"}, "cwd": str(self.tmp)}
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR" and not k.startswith("PAPERCLIP_")}
        for matcher, event, extra in [("Bash", sqlcmd, {}), ("mcp__.*", mcp, {}),
                                      (gates.HOOKS[2][1], merge, {"PAPERCLIP_RUN_ID": "run-1"})]:
            with self.subTest(matcher=matcher):
                result = subprocess.run(commands[matcher], shell=True, cwd=self.tmp, input=json.dumps(event),
                                        text=True, capture_output=True, env={**env, **extra}, check=True)
                self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")


class SetupHarnessIntegrationTests(unittest.TestCase):
    """setup_harness 가 같은 선언으로 수렴하고, --reset 의 미등록 훅 정리가 게이트를 지우지 않는다."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.sh = load("setup_harness_under_test", "tools/setup_harness.py")
        patcher = mock.patch.object(self.sh, "CLAUDE", str(self.tmp))
        patcher.start()
        self.addCleanup(patcher.stop)
        (self.tmp / "settings.json").write_text(json.dumps(user_settings()), encoding="utf-8")

    def settings(self):
        return json.loads((self.tmp / "settings.json").read_text(encoding="utf-8"))

    def test_check_reports_then_converge_installs_and_reset_keeps_gates(self):
        self.sh.converge_claude_gates(apply=False)
        self.assertTrue(self.sh.warn_list)
        self.assertEqual(self.settings(), user_settings())
        self.sh.converge_claude_gates(apply=True)
        self.assertEqual(len(managed_commands(self.settings())), 3)
        self.sh.audit_hooks(self.sh.load_manifest(), "reset")
        after = self.settings()
        self.assertEqual(len(managed_commands(after)), 3)
        self.assertEqual(after["hooks"]["PostToolUse"], user_settings()["hooks"]["PostToolUse"])


if __name__ == "__main__":
    unittest.main()
