import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Sequence


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "run_team2_knowledge_cycle.py"
spec = importlib.util.spec_from_file_location("run_team2_knowledge_cycle", MODULE_PATH)
cycle = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(cycle)


def completed(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class Team2KnowledgeCycleTests(unittest.TestCase):
    def test_build_steps_uses_existing_team2_tools_without_youtrack_mutations(self) -> None:
        harness = Path("/harness")
        vault = Path("/vault")
        steps = cycle.build_steps(harness, vault, apply=True)

        names = [step["name"] for step in steps]
        self.assertEqual(
            names,
            [
                "sync_harness_links",
                "enrich_vault_relations",
                "generate_vault_indexes",
                "run_hermes_dispatch_cycle",
            ],
        )
        commands = "\n".join(" ".join(step["command"]) for step in steps)
        self.assertIn("--apply", commands)
        self.assertNotIn("youtrack", commands.lower())
        self.assertNotIn("curl", commands.lower())

    def test_run_cycle_writes_status_and_summarizes_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = Path(tmp) / "harness"
            vault = Path(tmp) / "vault"
            (harness / "tools").mkdir(parents=True)
            vault.mkdir()
            seen: list[str] = []

            def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
                seen.append(Path(command[1]).name)
                if Path(command[1]).name == "run_hermes_dispatch_cycle.py":
                    return completed(
                        stdout=(
                            '{"schema":"team2.hermes_dispatch_cycle.v1",'
                            '"board":{"cards":2},'
                            '"dispatch_request":{"request_id":"hdr-test"},'
                            '"batch":{"payload_count":1,"dispatch_required":true}}'
                        )
                    )
                return completed(stderr="ok")

            result = cycle.run_cycle(
                harness,
                vault,
                apply=True,
                gbrain_health_url="http://gbrain.test/health",
                command_runner=runner,
                health_checker=lambda url: {"status": "ok", "url": url, "version": "test"},
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(seen[-1], "run_hermes_dispatch_cycle.py")
            self.assertEqual(cycle.dispatch_summary(result)["pending_payloads"], 1)
            self.assertTrue((vault / cycle.DEFAULT_STATUS_JSON).exists())
            self.assertTrue((vault / cycle.DEFAULT_STATUS_MD).exists())
            status_text = (vault / cycle.DEFAULT_STATUS_MD).read_text(encoding="utf-8")
            self.assertIn("DEV2 지식 사이클 상태", status_text)
            self.assertIn("youtrack_mutation", status_text)

    def test_run_cycle_stops_on_failed_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = Path(tmp) / "harness"
            vault = Path(tmp) / "vault"
            (harness / "tools").mkdir(parents=True)
            vault.mkdir()
            calls = 0

            def runner(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
                nonlocal calls
                calls += 1
                return completed(stderr="boom", returncode=7)

            result = cycle.run_cycle(
                harness,
                vault,
                apply=False,
                gbrain_health_url="http://gbrain.test/health",
                command_runner=runner,
                health_checker=lambda url: {"status": "ok", "url": url},
            )

            self.assertEqual(result["status"], "failed")
            self.assertEqual(calls, 1)
            self.assertEqual(result["steps"][0]["returncode"], 7)
            self.assertFalse((vault / cycle.DEFAULT_STATUS_JSON).exists())


if __name__ == "__main__":
    unittest.main()
