"""lint_harness_rules 스모크 — 실제 repo 상태에 의존하는 검사만 모은다.

읽기 전용으로만 돈다. 파일을 고치는 경로(--sync-generated·--update-baseline)는
tempdir fixture 를 쓰는 tests/test_lint_harness_rules.py 에서 검증한다.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/lint_harness_rules.py"
spec = importlib.util.spec_from_file_location("lint_harness_rules", TOOL)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def scan_repo(paths=()):
    md, yamls = module.collect_targets(str(ROOT), [str(p) for p in paths])
    return module.scan(str(ROOT), md, yamls, None)


class RealRepoSmokeTests(unittest.TestCase):
    def test_convention_section_is_not_flagged_as_overlap_or_emphasis(self):
        """§표기 규약 본문은 규약 설명문이라 R2·R3 대상이 아니다."""
        found = scan_repo([ROOT / "policies/instruction-precedence-policy.md"])
        self.assertEqual([f for f in found if f["rule"] in ("R2", "R3")], [])

    def test_generated_blocks_are_in_sync(self):
        found = scan_repo()
        self.assertEqual([f["excerpt"] for f in found if f["rule"] == "R7"], [])

    def test_summary_cli_runs_clean(self):
        proc = subprocess.run([sys.executable, str(TOOL), "--summary"],
                              capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("규칙별 요약", proc.stdout)
        self.assertTrue(proc.stdout.strip().splitlines()[-1].startswith("lint_harness_rules: OK"))


if __name__ == "__main__":
    unittest.main()
