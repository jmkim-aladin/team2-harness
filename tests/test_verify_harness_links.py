from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("verify_harness_links", ROOT / "tools/verify_harness_links.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class VerifyHarnessLinksTests(unittest.TestCase):
    def test_real_cli_exercises_sync_and_keeps_evidence_after_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "evidence"
            proc = subprocess.run([sys.executable, str(ROOT / "tools/verify_harness_links.py"),
                                   "--output", str(out)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            result = json.loads((out / "result.json").read_text())
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["cleanup"]["scratch_removed"])
            self.assertIn("- 이름: 검증 서비스", (out / "after.md").read_text())
            self.assertIn("예전 카탈로그 정보", (out / "before.md").read_text())
            self.assertIn("unchanged: 1", (out / "repeat.stderr.txt").read_text())
            self.assertIn("skipped: 1", (out / "unmanaged.stderr.txt").read_text())
            for name, sha in result["artifacts"].items():
                self.assertEqual(module.digest((out / name).read_bytes()), sha)

    def test_zero_exit_and_success_message_without_effect_is_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "fake.py"
            fake.write_text('print("PASS: everything worked")\n')
            out = Path(tmp) / "evidence"
            result = module.verify(out, fake)
            self.assertEqual(result["status"], "FAIL")
            self.assertFalse(result["checks"]["catalog_values_visible"])
            self.assertTrue(result["cleanup"]["scratch_removed"])
            self.assertTrue((out / "after.md").exists())

    def test_execution_failure_preserves_logs_and_cleans_scratch(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "fake.py"
            fake.write_text('import sys\nprint("cannot start", file=sys.stderr)\nsys.exit(3)\n')
            out = Path(tmp) / "evidence"
            result = module.verify(out, fake)
            self.assertEqual(result["status"], "INCONCLUSIVE")
            self.assertTrue(result["cleanup"]["scratch_removed"])
            self.assertIn("cannot start", (out / "dry-run.stderr.txt").read_text())

    def test_existing_evidence_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "evidence"
            out.mkdir()
            old = out / "result.json"
            old.write_text("previous result")
            with self.assertRaises(FileExistsError):
                module.verify(out)
            self.assertEqual(old.read_text(), "previous result")

    def test_successful_command_that_deletes_or_corrupts_note_is_failure(self):
        for mutation in ["note.unlink()", "note.write_bytes(b'\\xff')"]:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                fake = Path(tmp) / "fake.py"
                fake.write_text(
                    "import sys\nfrom pathlib import Path\n"
                    "if '--apply' in sys.argv:\n"
                    "    note = Path(sys.argv[sys.argv.index('--vault') + 1]) / 'wiki/services/sample/_index.md'\n"
                    f"    {mutation}\n")
                out = Path(tmp) / "evidence"
                result = module.verify(out, fake)
                self.assertEqual(result["status"], "FAIL")
                self.assertTrue(result["cleanup"]["scratch_removed"])
                self.assertEqual(result["commands"][-1]["exit_code"], 0)
                if "write_bytes" in mutation:
                    self.assertEqual((out / "after.md").read_bytes(), b'\xff')


if __name__ == "__main__":
    unittest.main()
