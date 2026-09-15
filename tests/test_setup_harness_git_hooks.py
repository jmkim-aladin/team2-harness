"""setup_harness 의 git hooks 수렴 — Claude·Codex 공통 pre-commit 게이트가 실제로 붙는지."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("setup_harness", ROOT / "tools/setup_harness.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

MANIFEST = {"git_hooks": {"hooks_path": ".githooks", "scripts": ["pre-commit"]}}


class GitHooksConvergenceTests(unittest.TestCase):
    def setUp(self):
        for bucket in (module.ok_list, module.warn_list, module.fix_list):
            bucket.clear()

    def make_repo(self, tmp):
        repo = Path(tmp)
        subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
        script = repo / ".githooks/pre-commit"
        script.parent.mkdir()
        script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        os.chmod(script, 0o644)
        return repo, script

    def hooks_path(self, repo):
        r = subprocess.run(["git", "-C", str(repo), "config", "--get", "core.hooksPath"],
                           capture_output=True, text=True)
        return r.stdout.strip()

    def test_apply_sets_hooks_path_and_makes_script_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, script = self.make_repo(tmp)
            self.assertEqual(self.hooks_path(repo), "")
            with mock.patch.object(module, "REPO", str(repo)), \
                 mock.patch.object(module, "IS_WIN", False):
                module.converge_git_hooks(MANIFEST, apply=True)
            self.assertEqual(self.hooks_path(repo), ".githooks")
            self.assertTrue(os.access(script, os.X_OK))
            self.assertTrue(any("core.hooksPath" in m for m in module.fix_list))

    def test_dry_run_only_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, script = self.make_repo(tmp)
            with mock.patch.object(module, "REPO", str(repo)), \
                 mock.patch.object(module, "IS_WIN", False):
                module.converge_git_hooks(MANIFEST, apply=False)
            self.assertEqual(self.hooks_path(repo), "")
            self.assertFalse(os.access(script, os.X_OK))
            self.assertTrue(any("수렴 필요" in m for m in module.warn_list))

    def test_windows_converges_without_chmod(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, _script = self.make_repo(tmp)
            with mock.patch.object(module, "REPO", str(repo)), \
                 mock.patch.object(module, "IS_WIN", True), \
                 mock.patch("os.chmod") as chmod:
                module.converge_git_hooks(MANIFEST, apply=True)
            chmod.assert_not_called()
            self.assertEqual(self.hooks_path(repo), ".githooks")

    def test_missing_script_warns_and_skips(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, script = self.make_repo(tmp)
            script.unlink()
            with mock.patch.object(module, "REPO", str(repo)), \
                 mock.patch.object(module, "IS_WIN", False):
                module.converge_git_hooks(MANIFEST, apply=True)
            self.assertEqual(self.hooks_path(repo), "")
            self.assertTrue(any("없음" in m for m in module.warn_list))


if __name__ == "__main__":
    unittest.main()
