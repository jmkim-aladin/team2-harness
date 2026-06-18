import importlib.util
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "run_granola_sync_cycle.py"
spec = importlib.util.spec_from_file_location("run_granola_sync_cycle", MODULE_PATH)
granola_cycle = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(granola_cycle)


def completed(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class GranolaSyncCycleTests(unittest.TestCase):
    def test_compute_updated_after_uses_success_watermark_with_overlap(self) -> None:
        state = {
            "status": "ok",
            "finished_at": "2026-06-18T09:30:00+00:00",
        }

        updated_after = granola_cycle.compute_updated_after(
            state,
            now=datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
            overlap_minutes=30,
            initial_lookback_days=7,
        )

        self.assertEqual(updated_after, "2026-06-18T09:00:00Z")

    def test_sync_command_uses_safe_defaults(self) -> None:
        command = granola_cycle.build_sync_command(
            Path("/workspace/team2"),
            Path("/workspace/team2-vault"),
            updated_after="2026-06-18T09:00:00Z",
            apply=True,
            include_transcript=False,
            create_daily=False,
        )
        command_text = " ".join(command)

        self.assertIn("sync_granola_meetings.py", command_text)
        self.assertIn("--updated-after 2026-06-18T09:00:00Z", command_text)
        self.assertIn("--apply", command)
        self.assertNotIn("--include-transcript", command)
        self.assertNotIn("--create-daily", command)

    def test_enrichment_block_is_idempotent_and_preserves_manual_sections(self) -> None:
        original = """---
type: meeting
date: 2026-06-18
source: granola
granola_id: not_test
---

# 2026-06-18 AASM 공유 링크 회의

<!-- generated:granola note_id=not_test updated=old -->
## 요약

- DEV2-1234에서 AASM 배포 링크 복사를 확인.
<!-- /generated -->

## 결정

- 수동 결정은 보존한다.
"""

        once = granola_cycle.upsert_enrichment_block(
            original,
            updated_at="2026-06-18T10:00:00+00:00",
        )
        twice = granola_cycle.upsert_enrichment_block(
            once,
            updated_at="2026-06-18T10:10:00+00:00",
        )

        self.assertIn("<!-- generated:granola-ai-enrichment", once)
        self.assertEqual(twice.count("<!-- generated:granola-ai-enrichment"), 1)
        self.assertIn("[[dev2-1234]]", twice)
        self.assertIn("[[aasm]]", twice)
        self.assertIn("- 수동 결정은 보존한다.", twice)
        self.assertNotIn("confirmed", twice.lower())
        self.assertNotIn("canonical", twice.lower())

    def test_run_cycle_enriches_changed_meeting_and_runs_followups(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            harness = root / "harness"
            vault = root / "vault"
            (harness / "tools").mkdir(parents=True)
            meeting = vault / "wiki/processes/meetings/2026-06-18-aasm-release.md"
            meeting.parent.mkdir(parents=True)
            meeting.write_text(
                """---
type: meeting
date: 2026-06-18
source: granola
granola_id: not_test
---

# 2026-06-18 AASM release

<!-- generated:granola note_id=not_test updated=old -->
## 요약

- DEV2-1234 AASM release 링크 복사 논의.
<!-- /generated -->

## 후속 액션

- [ ] 수동 액션
""",
                encoding="utf-8",
            )
            seen: list[str] = []

            def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
                script = Path(command[1]).name
                seen.append(script)
                if script == "sync_granola_meetings.py":
                    return completed(stdout="wrote wiki/processes/meetings/2026-06-18-aasm-release.md\n")
                return completed(stdout="ok\n")

            result = granola_cycle.run_cycle(
                harness,
                vault,
                apply=True,
                command_runner=runner,
                now_fn=lambda: datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(
                seen,
                [
                    "sync_granola_meetings.py",
                    "generate_vault_indexes.py",
                    "lint_vault.py",
                    "run_team2_knowledge_cycle.py",
                ],
            )
            text = meeting.read_text(encoding="utf-8")
            self.assertIn("generated:granola-ai-enrichment", text)
            self.assertIn("[[dev2-1234]]", text)
            self.assertIn("[[aasm]]", text)
            self.assertIn("- [ ] 수동 액션", text)
            self.assertTrue((vault / granola_cycle.DEFAULT_STATUS_JSON).exists())
            self.assertTrue((vault / granola_cycle.DEFAULT_STATUS_MD).exists())

    def test_run_cycle_skips_followups_when_sync_has_no_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            harness = root / "harness"
            vault = root / "vault"
            (harness / "tools").mkdir(parents=True)
            vault.mkdir()
            seen: list[str] = []

            def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
                seen.append(Path(command[1]).name)
                return completed(stdout="dry-run only. 실제 저장은 --apply를 붙이세요.\n")

            result = granola_cycle.run_cycle(
                harness,
                vault,
                apply=True,
                command_runner=runner,
                now_fn=lambda: datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc),
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(seen, ["sync_granola_meetings.py"])
            self.assertEqual(result["changed_meetings"], [])


if __name__ == "__main__":
    unittest.main()
